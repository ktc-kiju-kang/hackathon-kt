#!/usr/bin/env python3
"""제출 문서 8개 검사 — 빠진 문서, 남은 {{자리표시}}, 끊긴 SRC→REQ→AC→TC 사슬, SEC 누락.

prd.md는 인덱스(원문 SRC·요구사항 표·상태)이고, REQ별 확인 조건(AC)은 요구사항 표의 ID 칸이
링크한 하위 정의서 docs/prd/REQ-01-<설명>.md에 둔다 (하위 파일 없이 prd.md 한 파일에 AC를 둬도 된다).

사용: python3 scripts/check-docs.py [--draft] [저장소 루트]
  --draft  작성 중: 자리표시·미실행·빈 표는 경고로만 본다 (제출 직전에는 빼고 실행)
종료 코드: 오류가 있으면 1
"""

import re
import sys
from pathlib import Path

DOCS = [
    "README.md",
    "docs/project-brief.md",
    "docs/prd.md",
    "docs/arch.md",
    "docs/experience.md",
    "docs/development.md",
    "docs/security-compliance.md",
    "docs/e2e-test.md",
]
TC_STATUS = ("PASS", "FAIL", "SKIP", "미실행")
PLACEHOLDER = re.compile(r"\{\{[^}]*\}\}")
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
# 한글 조사("REQ-01을")가 붙어도 잡히도록 \b 대신 영문·숫자만 막는 경계를 쓴다
ID_RE = re.compile(r"(?<![A-Za-z0-9-])((?:REQ|AC|TC|SEC)-S?\d+(?:-\d+)?)(?![0-9])")
PRD_LINK = re.compile(r"\]\((prd/[^)\s#]+)\)")  # 요구사항 표 ID 칸: [REQ-01](prd/REQ-01-login.md)
CHILD_NAME = re.compile(r"REQ-(\d+)(?:-[a-z0-9-]+)?\.md")
SRC_RE = re.compile(r"SRC-\d+")
ID_PAT = {
    "REQ": r"REQ-\d+",
    "AC": r"AC-\d+-\d+",
    "TC": r"TC-S?\d+-\d+",
    "SEC": r"SEC-\d+",
}


def norm(raw: str) -> str:
    """ID 정규화: 마크다운 장식을 벗기고 숫자 자리수를 맞춘다 (첫 번호만: REQ-1 → REQ-01, AC-1-2 → AC-01-2)."""
    s = re.sub(r"\(.*?\)$", "", re.sub(r"[*`\[\]]", "", raw)).strip()
    return re.sub(r"^([A-Z]+-)(S?)(\d+)", lambda m: f"{m[1]}{m[2]}{int(m[3]):02d}", s)


def tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    """마크다운 표를 (헤더, 행 목록)으로 나눈다. 셀 안의 \\|는 구분자로 보지 않는다."""
    out: list[tuple[list[str], list[list[str]]]] = []
    header: list[str] | None = None
    body: list[list[str]] = []
    for line in [*text.splitlines(), ""]:
        if line.lstrip().startswith("|"):
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
            if header is None:
                header = cells
            elif not all(re.fullmatch(r":?-+:?", c) for c in cells):
                body.append(cells)
        elif header is not None:
            out.append((header, body))
            header, body = None, []
    return out


def id_rows(
    text: str, kind: str, errors: list[str], rel: str
) -> dict[str, dict[str, str]]:
    """첫 칸이 kind ID인 표 행을 {ID: {헤더: 값}}으로 모은다. 중복·칸 부족은 오류."""
    found: dict[str, dict[str, str]] = {}
    for header, body in tables(text):
        for cells in body:
            key = norm(cells[0]) if cells else ""
            if not re.fullmatch(ID_PAT[kind], key):
                continue
            if len(cells) < len(header):
                errors.append(f"{rel}: {key} 행의 칸 수가 헤더보다 적음")
            if key in found:
                errors.append(f"{rel}: {key}가 두 번 정의됨")
            found[key] = dict(zip(header, cells))
    return found


def refs(cell: str) -> list[str]:
    return [norm(m) for m in ID_RE.findall(cell)]


def req_of(ac: str) -> str:
    return "REQ-" + ac.split("-")[1]


def prd_children(
    root: Path, parent: str, errors: list[str]
) -> list[tuple[str, str]]:
    """부모 prd.md가 링크한 REQ별 하위 정의서 [(경로, 내용)]. 링크되지 않은 docs/prd/*.md는 오류."""
    linked = list(dict.fromkeys(PRD_LINK.findall(parent)))
    out = []
    for rel in linked:
        p = root / "docs" / rel
        if not CHILD_NAME.fullmatch(p.name):
            errors.append(f"prd.md: 하위 정의서 이름은 prd/REQ-01-<설명>.md 형식이어야 함 ({rel})")
        elif not p.is_file():
            errors.append(f"prd.md: 링크한 docs/{rel} 없음")
        else:
            out.append((f"docs/{rel}", COMMENT.sub("", p.read_text(encoding="utf-8"))))
    folder = root / "docs" / "prd"
    if folder.is_dir():
        for p in sorted(folder.glob("*.md")):
            if f"prd/{p.name}" not in linked and not p.name.startswith("_"):
                errors.append(f"docs/prd/{p.name}: prd.md 요구사항 표에서 링크되지 않음")
    return out


def main() -> int:
    flags = {a for a in sys.argv[1:] if a.startswith("-")}
    if flags - {"--draft"}:
        print(__doc__)
        return 2
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    draft = "--draft" in flags
    root = Path(args[0] if args else ".")
    errors: list[str] = []
    warns: list[str] = []
    soft = warns if draft else errors  # draft면 경고, 아니면 오류
    texts: dict[str, str] = {}

    for rel in DOCS:
        p = root / rel
        if not p.exists():
            errors.append(f"{rel}: 파일 없음")
            continue
        texts[rel] = COMMENT.sub("", p.read_text(encoding="utf-8"))
        if not texts[rel].strip():
            errors.append(f"{rel}: 내용 없음")
        n = len(PLACEHOLDER.findall(texts[rel]))
        if n:
            soft.append(f"{rel}: 채우지 않은 {{{{자리표시}}}} {n}개")

    prd = texts.get("docs/prd.md", "")
    reqs = id_rows(prd, "REQ", errors, "prd.md")
    acs = id_rows(prd, "AC", errors, "prd.md")
    for rel, text in prd_children(root, prd, errors):
        texts[rel] = text  # 자리표시·정의 안 된 ID 검사에도 넣는다
        n = len(PLACEHOLDER.findall(text))
        if n:
            soft.append(f"{rel}: 채우지 않은 {{{{자리표시}}}} {n}개")
        if id_rows(text, "REQ", [], rel):
            errors.append(f"{rel}: REQ 표는 부모 prd.md에만 둔다 (상태가 두 곳이 됨)")
        m = CHILD_NAME.fullmatch(Path(rel).name)  # prd_children가 이름 형식을 확인했다
        own = f"REQ-{int(m[1]):02d}" if m else ""
        if own not in reqs:
            errors.append(f"{rel}: {own}가 prd.md 요구사항 표에 없음")
        for ac, row in id_rows(text, "AC", errors, rel).items():
            if req_of(ac) != own:
                errors.append(f"{rel}: {ac}는 {own}의 확인 조건이 아님")
            if ac in acs:
                errors.append(f"{rel}: {ac}가 두 번 정의됨")
            acs[ac] = row
    # 하위 정의서 링크가 그 REQ의 파일을 가리키는가, 요약 칸 '확인 조건'이 실제 AC와 같은가
    for req, r in reqs.items():
        link = PRD_LINK.search(r.get("ID", ""))
        name = CHILD_NAME.fullmatch(Path(link[1]).name) if link else None
        if link and name and f"REQ-{int(name[1]):02d}" != req:
            errors.append(f"prd.md: {req}의 링크가 다른 REQ 파일을 가리킴 ({link[1]})")
        if "확인 조건" in r:
            want = sorted(ac for ac in acs if req_of(ac) == req)
            got = sorted(x for x in refs(r["확인 조건"]) if x.startswith("AC-"))
            if got != want:
                errors.append(
                    f"prd.md: {req}의 '확인 조건' 칸({', '.join(got) or '없음'})이"
                    f" 정의된 AC({', '.join(want) or '없음'})와 다름"
                )
    # 원문(SRC)은 REQ의 '출처' 칸이나 '범위 밖' 표로 이어져야 한다 (질문·메모에만 나오면 안 이어진 것)
    defined: set[str] = set()
    used = {s for r in reqs.values() for s in SRC_RE.findall(r.get("출처", ""))}
    for header, body in tables(prd):
        if header[:1] == ["SRC"]:
            (defined if "원문" in header else used).update(
                s for cells in body for s in SRC_RE.findall(cells[0])
            )
    for src in sorted(defined - used, key=lambda s: int(s[4:])):
        soft.append(f"prd.md: {src}가 어느 REQ의 출처나 '범위 밖'에도 없음")
    tcs = id_rows(texts.get("docs/e2e-test.md", ""), "TC", errors, "e2e-test.md")
    secs = id_rows(
        texts.get("docs/security-compliance.md", ""),
        "SEC",
        errors,
        "security-compliance.md",
    )
    for name, got in (("REQ", reqs), ("AC", acs), ("TC", tcs)):
        if not got:
            soft.append(f"{name} 표가 비었거나 못 읽음 (첫 칸이 {name}-번호인 표)")

    # TC가 확인하는 AC·SEC — 한 칸에 여러 개("AC-01-1, AC-01-2")도 허용
    tc_refs = {tc: refs(r.get("확인 조건", "")) for tc, r in tcs.items()}
    for req in reqs:
        if not any(req_of(ac) == req for ac in acs):
            errors.append(f"prd.md: {req}에 확인 조건(AC)이 없음")
    covered = {x for xs in tc_refs.values() for x in xs}
    for ac in acs:
        if req_of(ac) not in reqs:
            errors.append(f"prd.md: {ac}의 {req_of(ac)}가 요구사항 표에 없음")
        if ac not in covered:
            errors.append(f"e2e-test.md: {ac}을 확인하는 TC가 없음")
    for tc, r in tcs.items():
        if not tc_refs[tc]:
            errors.append(f"e2e-test.md: {tc}의 '확인 조건' 칸에 AC·SEC ID가 없음")
        for ref in tc_refs[tc]:
            if ref.startswith("AC-") and ref not in acs:
                errors.append(f"e2e-test.md: {tc}가 없는 {ref}를 참조")
            if ref.startswith("SEC-") and ref not in secs:
                errors.append(f"e2e-test.md: {tc}가 compliance 표에 없는 {ref}를 참조")
        status = r.get("상태", "")
        if not status.startswith(TC_STATUS):
            errors.append(
                f"e2e-test.md: {tc} 상태 '{status}' — {'/'.join(TC_STATUS)} 중 하나"
            )
        elif status.startswith("미실행"):
            soft.append(f"e2e-test.md: {tc} 미실행")
        elif status.startswith("SKIP") and "(" not in status:
            errors.append(f"e2e-test.md: {tc} SKIP에 이유가 없음 — SKIP(이유)")
    # 검증됨 REQ는 연결된 TC가 모두 PASS여야 한다
    for req, r in reqs.items():
        if not r.get("상태", "").startswith("검증됨"):
            continue
        linked = [
            t
            for t, xs in tc_refs.items()
            if any(x.startswith("AC-") and req_of(x) == req for x in xs)
        ]
        if not linked or any(
            not tcs[t].get("상태", "").startswith("PASS") for t in linked
        ):
            errors.append(f"prd.md: {req}이 '검증됨'인데 연결된 TC가 모두 PASS는 아님")
    # 정의되지 않은 ID를 참조하는 문서 ({{…}} 안의 ID는 예시라서 제외)
    known = set(reqs) | set(acs) | set(tcs) | set(secs)
    for rel, text in texts.items():
        found = {norm(m) for m in ID_RE.findall(PLACEHOLDER.sub("", text))}
        for ref in sorted(found - known):
            if not ref.startswith("SEC-"):
                warns.append(f"{rel}: {ref}가 prd.md/e2e-test.md에 정의되지 않음")
    # SEC: 주최 정책의 모든 항목이 compliance 표에 있는가
    policy = root / "docs/security-policy.md"
    if not policy.exists():
        warns.append("docs/security-policy.md(주최 제공) 없음 — SEC 대조 생략")
    else:
        text = policy.read_text(encoding="utf-8")
        need = {norm(m) for m in re.findall(r"SEC-\d+", text)}
        if not need:
            warns.append("security-policy.md에서 SEC-번호를 못 찾음 — 직접 대조할 것")
        for sec in sorted(need - set(secs)):
            errors.append(f"security-compliance.md: {sec} 행 없음")

    for w in warns:
        print(f"경고  {w}")
    for e in errors:
        print(f"오류  {e}")
    counts = f"REQ {len(reqs)} · AC {len(acs)} · TC {len(tcs)} · SEC {len(secs)}"
    print(f"\n{counts} — 오류 {len(errors)}, 경고 {len(warns)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
