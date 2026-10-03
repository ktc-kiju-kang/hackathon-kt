"""OpenAI Signals 트렌드 지표. 계약: docs/contracts/trends.md

공개된 읽기 전용 데이터라 DB 대신 backend/data/signals/의 CSV를
처음 호출 때 메모리에 읽는다 (~2MB).
"""

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException

from app.schemas.trends import (
    Evidence,
    EvidenceRef,
    IntentChange,
    MonthRange,
    Source,
    TopicChange,
    TrendSeries,
    TrendsMeta,
    TrendSummary,
    UsageRank,
    WorkShare,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "signals"
SOURCE_URL = "https://openai.com/signals/data-download/"
EVIDENCE_MONTHS = 23  # Evidence는 항상 전체 기간 비교 (계약)
INTENT_LABEL = {
    "asking": "질문(asking)",
    "doing": "작업 요청(doing)",
    "expressing": "표현(expressing)",
}

Country = str | None  # None = 전 세계


def _tree():
    return defaultdict(dict)


@dataclass
class _Data:
    # [country][month][key] = share. country None = 전 세계
    topic: dict = field(default_factory=lambda: defaultdict(_tree))
    # [(country, work_related)][month][key] = share
    work_topic: dict = field(default_factory=lambda: defaultdict(_tree))
    intent: dict = field(default_factory=lambda: defaultdict(_tree))
    # [country][month]["0" | "1"] = share
    work: dict = field(default_factory=lambda: defaultdict(_tree))
    # [country][quarter] = rank
    rank: dict = field(default_factory=lambda: defaultdict(dict))
    months: list[str] = field(default_factory=list)
    countries: list[str] = field(default_factory=list)


def _rows(name: str):
    # keep_default_na 문제(나미비아 "NA")가 없게 csv 모듈로 문자열 그대로 읽는다
    with open(DATA_DIR / f"{name}.csv", newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)


def _month(value: str) -> str:
    return value[:7]  # "2024-07-01" → "2024-07"


@lru_cache
def _data() -> _Data:
    d = _Data()
    prefix = "share_of_messages_by_"
    for country in (False, True):
        suffix = "_country_month" if country else "_month"

        def c(r, country=country):
            return r["country"] if country else None

        for r in _rows(f"{prefix}topic{suffix}"):
            d.topic[c(r)][_month(r["month"])][r["topic"]] = float(r["share_of_messages"])
        for r in _rows(f"{prefix}topic_work_related{suffix}"):
            key = (c(r), int(r["work_related"]))
            d.work_topic[key][_month(r["month"])][r["topic"]] = float(r["share_of_messages"])
        for r in _rows(f"{prefix}work_related_ask_do_express{suffix}"):
            key = (c(r), int(r["work_related"]))
            d.intent[key][_month(r["month"])][r["ask_do_express"]] = float(r["share_of_messages"])
        for r in _rows(f"{prefix}work_related{suffix}"):
            d.work[c(r)][_month(r["month"])][r["work_related"]] = float(r["share_of_messages"])
    for r in _rows("share_of_messages_by_country_quarter_rank"):
        d.rank[r["country"]][_month(r["quarter"])] = int(r["rank"])

    d.months = sorted(d.topic[None])
    full = len(d.months)
    codes = {k for k in d.topic if k is not None}
    d.countries = sorted(
        code
        for code in codes
        if len(d.topic[code]) == full
        and len(d.work[code]) == full
        and len(d.work_topic[(code, 1)]) == full
        and len(d.intent[(code, 1)]) == full
    )
    return d


def _check_country(country: Country) -> None:
    if country is not None and country not in _data().countries:
        raise HTTPException(status_code=404, detail="해당 국가 데이터가 없습니다")


def get_meta() -> TrendsMeta:
    d = _data()
    topics = sorted({t for m in d.topic[None].values() for t in m})
    return TrendsMeta(
        months=MonthRange(from_=d.months[0], to=d.months[-1]),
        countries=d.countries,
        topics=topics,
        source=Source(url=SOURCE_URL),
    )


def get_series(
    dimension: str,
    country: Country,
    work_related: int | None,
    from_: str | None,
    to: str | None,
) -> TrendSeries:
    d = _data()
    if dimension == "ask_do_express" and work_related is None:
        raise HTTPException(422, "ask_do_express는 work_related(0 또는 1)가 필요합니다")
    if dimension == "work_related" and work_related is not None:
        raise HTTPException(422, "work_related 차원에는 work_related 필터를 쓸 수 없습니다")
    start, end = from_ or d.months[0], to or d.months[-1]
    if start > end or start not in d.months or end not in d.months:
        raise HTTPException(422, f"기간은 {d.months[0]} ~ {d.months[-1]} 안에서 from ≤ to")
    _check_country(country)

    if dimension == "topic":
        table = d.topic[country] if work_related is None else d.work_topic[(country, work_related)]
    elif dimension == "ask_do_express":
        table = d.intent[(country, work_related)]
    else:
        table = d.work[country]
    points = [
        {"month": m, "key": k, "share": table[m][k]}
        for m in d.months
        if start <= m <= end and m in table
        for k in sorted(table[m])
    ]
    return TrendSeries(
        dimension=dimension, country=country, work_related=work_related, points=points
    )


def _pp(a: float, b: float) -> float:
    return round((b - a) * 100, 1)


def _changes(table: dict, start: str, end: str) -> list[tuple[str, float, float, float]]:
    """(key, from, to, change_pp) — change_pp 내림차순."""
    before = table[start]
    rows = [(k, before[k], v, _pp(before[k], v)) for k, v in table[end].items() if k in before]
    return sorted(rows, key=lambda r: (-r[3], r[0]))


def _topic_changes(table: dict, start: str, end: str) -> list[TopicChange]:
    return [
        TopicChange(topic=k, from_share=a, to_share=b, change_pp=pp)
        for k, a, b, pp in _changes(table, start, end)
    ]


def _usage_rank(country: Country, start: str) -> UsageRank | None:
    ranks = _data().rank.get(country) if country else None
    if not ranks:
        return None
    quarters = sorted(ranks)
    latest = quarters[-1]
    prev = next((q for q in quarters if q >= start), None)
    if prev == latest:
        prev = None
    return UsageRank(
        quarter=latest,
        rank=ranks[latest],
        previous_quarter=prev,
        previous_rank=ranks[prev] if prev else None,
    )


@lru_cache(maxsize=512)
def get_summary(country: Country, months: int = 12) -> TrendSummary:
    d = _data()
    if not 1 <= months < len(d.months):
        raise HTTPException(422, f"months는 1~{len(d.months) - 1}")
    _check_country(country)
    end = d.months[-1]
    start = d.months[-1 - months]
    work_from, work_to = d.work[country][start]["1"], d.work[country][end]["1"]
    return TrendSummary(
        country=country,
        period=MonthRange(from_=start, to=end),
        topics=_topic_changes(d.topic[country], start, end),
        work_topics=_topic_changes(d.work_topic[(country, 1)], start, end),
        work_share=WorkShare(from_=work_from, to=work_to, change_pp=_pp(work_from, work_to)),
        work_intent=[
            IntentChange(intent=k, from_share=a, to_share=b, change_pp=pp)
            for k, a, b, pp in _changes(d.intent[(country, 1)], start, end)
        ],
        usage_rank=_usage_rank(country, start),
    )


def _pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def _resolve(ref: EvidenceRef) -> Evidence | None:
    s = get_summary(ref.country, EVIDENCE_MONTHS)
    where = ref.country or "전 세계"
    period = f"({s.period.from_} → {s.period.to})"
    base = {"metric": ref.metric, "key": ref.key, "country": ref.country}

    def share(subject: str, a: float, b: float) -> Evidence:
        return Evidence(
            **base,
            from_=s.period.from_,
            to=s.period.to,
            from_value=a,
            to_value=b,
            change_pp=_pp(a, b),
            label=f"{where} {subject} {_pct(a)} → {_pct(b)} {period}",
        )

    if ref.metric in ("topic_share", "work_topic_share"):
        rows = s.topics if ref.metric == "topic_share" else s.work_topics
        row = next((r for r in rows if r.topic == ref.key), None)
        if row is None:
            return None
        scope = "메시지" if ref.metric == "topic_share" else "업무 메시지"
        return share(f"{scope} 중 {row.topic}", row.from_share, row.to_share)
    if ref.metric == "work_intent":
        row = next((r for r in s.work_intent if r.intent == ref.key), None)
        if row is None:
            return None
        return share(f"업무 메시지 중 {INTENT_LABEL[row.intent]}", row.from_share, row.to_share)
    if ref.metric == "work_share" and ref.key is None:
        return share("업무 관련 메시지 비중", s.work_share.from_, s.work_share.to)
    if ref.metric == "usage_rank" and ref.key is None and s.usage_rank:
        r = s.usage_rank
        ranks = f"{r.previous_rank}위 → {r.rank}위" if r.previous_rank else f"{r.rank}위"
        quarters = f"({r.previous_quarter} → {r.quarter})" if r.previous_quarter else ""
        quarters = quarters or f"({r.quarter})"
        return Evidence(
            **base,
            from_=r.previous_quarter or r.quarter,
            to=r.quarter,
            from_value=r.previous_rank,
            to_value=r.rank,
            change_pp=None,
            label=f"{where} 인구 대비 ChatGPT 사용량 순위 {ranks} {quarters}",
        )
    return None


def resolve_evidence(refs: list[EvidenceRef], allowed_countries: set[Country]) -> list[Evidence]:
    """LLM이 고른 근거 지표에 실제 값을 채운다. 허용되지 않거나 해석할 수 없는 ref는 버린다."""
    out: list[Evidence] = []
    seen: set[tuple] = set()
    for ref in refs:
        key = (ref.metric, ref.key, ref.country)
        if key in seen or ref.country not in allowed_countries:
            continue
        if ref.country is not None and ref.country not in _data().countries:
            continue
        seen.add(key)
        if (ev := _resolve(ref)) is not None:
            out.append(ev)
    return out
