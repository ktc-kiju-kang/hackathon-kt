#!/usr/bin/env python3
"""시험 결과(JUnit XML) → docs/e2e-test.md 상태·근거 갱신 + docs/evidence/<실행>/ 근거 저장.

테스트 이름에 TC ID를 넣으면 자동으로 연결된다:
  pytest  def test_tc_01_3_other_users_item_is_hidden(): ...
  vitest  it('TC-02-1 빈 입력이면 저장 버튼이 꺼진다', ...)
같은 TC에 테스트가 여럿이면 하나라도 실패 → FAIL, 전부 skip → SKIP(이유), 그 밖 → PASS.
테스트가 없는 TC(수동 시험)는 건드리지 않는다.

사용: scripts/e2e.sh 가 부른다.
직접: python3 scripts/e2e-report.py --version <sha> --results .run/e2e
"""

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "e2e-test.md"
KST = timezone(timedelta(hours=9))
TC_IN_NAME = re.compile(r"(?i)(?<![a-z0-9])tc[-_]?(s?)(\d+)[-_](\d+)")
SUITES = {"backend.xml": "backend pytest", "frontend.xml": "frontend vitest", "e2e.xml": "E2E"}


def tc_id(text: str) -> str | None:
    m = TC_IN_NAME.search(text)
    return f"TC-{m[1].upper()}{int(m[2]):02d}-{int(m[3])}" if m else None


def norm(cell: str) -> str:
    """문서 표의 TC 칸 정규화 (TC-1-1 → TC-01-1)."""
    s = re.sub(r"[*`\[\]]|\(.*?\)$", "", cell).strip()
    return re.sub(r"^TC-(S?)(\d+)", lambda m: f"TC-{m[1]}{int(m[2]):02d}", s)


def read_junit(path: Path) -> list[dict]:
    cases = []
    for tc in ET.parse(path).getroot().iter("testcase"):
        name = tc.get("name", "")
        cls = tc.get("classname", "")
        if tc.find("failure") is not None or tc.find("error") is not None:
            status, why = "FAIL", ""
        elif (sk := tc.find("skipped")) is not None:
            msg = (sk.get("message") or "").strip().splitlines()
            why = (msg[0] if msg else "skip")[:60].replace("|", "/")  # 표 칸을 깨지 않게
            status = "SKIP"
        else:
            status, why = "PASS", ""
        cases.append({"name": name, "cls": cls, "status": status, "why": why, "suite": path.name})
    return cases


def aggregate(cases: list[dict]) -> dict[str, dict]:
    by_tc: dict[str, list[dict]] = {}
    for c in cases:
        if tid := tc_id(c["name"]) or tc_id(c["cls"]):
            by_tc.setdefault(tid, []).append(c)
    out = {}
    for tid, cs in by_tc.items():
        if any(c["status"] == "FAIL" for c in cs):
            status = "FAIL"
        elif all(c["status"] == "SKIP" for c in cs):
            status = f"SKIP({cs[0]['why']})"
        else:
            status = "PASS"
        out[tid] = {"status": status, "tests": cs}
    return out


def split_row(line: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def join_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def is_tc_list(header: list[str]) -> bool:
    """e2e-test.md "시험 목록" 표 (TC·확인 조건·상태). SKIP 사유 표 등은 제외."""
    return header[:1] == ["TC"] and "확인 조건" in header and "상태" in header


def update_doc(text: str, results: dict[str, dict], env: dict[str, str], evidence: str) -> str:
    lines = text.splitlines()
    i = 0
    tc_rows: list[tuple[int, list[str], list[str]]] = []
    while i < len(lines):
        if lines[i].lstrip().startswith("|") and i + 1 < len(lines) and "---" in lines[i + 1]:
            header = split_row(lines[i])
            j = i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                cells = split_row(lines[j])
                key = cells[0] if cells else ""
                if is_tc_list(header):
                    tid = norm(key)
                    st_i = header.index("상태")
                    ev_i = header.index("근거") if "근거" in header else None
                    if tid not in results and ev_i is not None and "evidence/" in cells[ev_i]:
                        # 전에 자동 기록됐는데 이번 실행에 없음 → 예전 PASS를 남기지 않는다
                        cells[st_i], cells[ev_i] = "미실행", "-"
                        lines[j] = join_row(cells)
                    if tid in results:
                        cells[header.index("상태")] = results[tid]["status"]
                        if "근거" in header:
                            cells[header.index("근거")] = (
                                f"[{Path(evidence).parent.name}]({evidence})"
                            )
                        lines[j] = join_row(cells)
                    tc_rows.append((j, header, cells))
                elif header[:1] == ["항목"] and key in env and len(cells) > 1:
                    cells[1] = env[key]
                    lines[j] = join_row(cells)
                j += 1
            i = j
        else:
            i += 1
    # 결과 요약 표: 시험 목록의 상태를 다시 센다
    counts = {"PASS": 0, "FAIL": 0, "SKIP": 0, "미실행": 0}
    for _, header, cells in tc_rows:
        st = cells[header.index("상태")]
        for k in counts:
            if st.startswith(k):
                counts[k] += 1
    for n, line in enumerate(lines):
        cells = split_row(line) if line.lstrip().startswith("|") else []
        # "결과 요약" 표의 2칸 행 (| PASS | {{n}} |)만 바꾼다
        if len(cells) == 2 and cells[0] in counts and re.fullmatch(r"\{\{n\}\}|\d+", cells[1]):
            lines[n] = join_row([cells[0], str(counts[cells[0]])])
    return "\n".join(lines) + "\n"


def doc_tc_status(text: str) -> dict[str, str]:
    """e2e-test.md 시험 목록의 TC → 상태."""
    out = {}
    for header, rows in tables(text):
        if is_tc_list(header):
            for cells in rows:
                out[norm(cells[0])] = cells[header.index("상태")]
    return out


def tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    out, lines, i = [], text.splitlines(), 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|") and i + 1 < len(lines) and "---" in lines[i + 1]:
            header, rows, j = split_row(lines[i]), [], i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                rows.append(split_row(lines[j]))
                j += 1
            out.append((header, rows))
            i = j
        else:
            i += 1
    return out


def update_prd(text: str, tc_status: dict[str, str]) -> tuple[str, list[str]]:
    """REQ 상태 = 그 REQ의 AC가 가리키는 TC 결과.

    전부 PASS → 검증됨, 일부만 실행·실패 → 구현됨-미검증, 실행 안 함 → 그대로.
    """
    req_tcs: dict[str, list[str]] = {}
    for header, rows in tables(text):
        if header[:1] == ["AC"] and "시험" in header:
            for cells in rows:
                m = re.match(r"AC-(\d+)-", cells[0].strip("*` "))
                if m:
                    req = f"REQ-{int(m[1]):02d}"
                    tcs = [
                        norm(t) for t in re.findall(r"TC-S?\d+-\d+", cells[header.index("시험")])
                    ]
                    req_tcs.setdefault(req, []).extend(tcs)
    changed, lines = [], text.splitlines()
    for n, line in enumerate(lines):
        cells = split_row(line) if line.lstrip().startswith("|") else []
        req = re.sub(r"[*`\[\]]", "", cells[0]).strip() if cells else ""
        if not re.fullmatch(r"REQ-\d+", req) or req not in req_tcs or cells[-1].startswith("제외"):
            continue
        sts = [tc_status.get(t, "미실행") for t in req_tcs[req]]
        if not sts:
            continue
        if all(s.startswith("PASS") for s in sts):
            new = "검증됨"
        elif any(s.startswith(("PASS", "FAIL", "SKIP")) for s in sts):
            new = "구현됨-미검증"
        else:
            continue
        if cells[-1] != new:
            changed.append(f"{req} {cells[-1]} → {new}")
            cells[-1] = new
            lines[n] = join_row(cells)
    return "\n".join(lines) + "\n", changed


def tool_version(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "?"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--results", required=True, type=Path)
    ap.add_argument("--exit-codes", nargs="*", default=[], help="묶음=종료코드 (e2e.sh가 넘김)")
    args = ap.parse_args()

    cases: list[dict] = []
    ran: dict[str, str] = {}
    for fname, label in SUITES.items():
        p = args.results / fname
        if p.exists():
            got = read_junit(p)
            cases += got
            ran[label] = f"{len(got)}개 중 실패 {sum(c['status'] == 'FAIL' for c in got)}"
        else:
            ran[label] = "결과 없음 (실행 실패)"
    results = aggregate(cases)

    # 전체 판정: 종료코드 실패·결과 없는 묶음·실패 테스트(TC ID 무관) 중 하나라도 있으면 FAIL
    codes = dict(x.split("=", 1) for x in args.exit_codes)
    failed_suites = [k for k, v in codes.items() if v != "0"]
    missing_suites = [label for label, r in ran.items() if r.startswith("결과 없음")]
    failed_cases = [c for c in cases if c["status"] == "FAIL"]
    overall = "FAIL" if failed_suites or missing_suites or failed_cases else "PASS"

    now = datetime.now(UTC)
    sha = args.version
    dirty = "-dirty" if sha.endswith("-dirty") else ""
    run_id = f"{now.astimezone(KST):%Y%m%d-%H%M%S}-{sha[:7]}{dirty}"
    # 제출 문서가 없는 레포(키트 원본)에서는 근거를 커밋 대상이 아닌 .run/에 둔다
    ev_base = ROOT / "docs" / "evidence" if DOC.exists() else ROOT / ".run" / "evidence"
    ev_dir = ev_base / run_id
    if ev_dir.exists():
        shutil.rmtree(ev_dir)
    ev_dir.mkdir(parents=True)
    home = str(Path.home())
    for f in args.results.iterdir():
        if f.suffix in (".xml", ".log"):
            # 홈 경로(/Users/<이름>)는 ~로 — 배정 레포가 공개여도 개인 경로가 남지 않게
            text = f.read_text(encoding="utf-8", errors="replace").replace(home, "~")
            (ev_dir / f.name).write_text(text, encoding="utf-8")
    rel = f"evidence/{run_id}/summary.md"  # docs/e2e-test.md 기준 상대 경로

    env = {
        "소스 SHA": sha,
        "실행 시각": f"{now.astimezone(KST):%Y-%m-%d %H:%M} KST",
        "OS·런타임": f"{platform.system()} {platform.release()}"
        f" / Node {tool_version(['node', '-v'])} / Python {platform.python_version()}",
    }
    in_doc: set[str] = set()
    if DOC.exists():
        text = DOC.read_text(encoding="utf-8")
        in_doc = {norm(m) for m in re.findall(r"TC-S?\d+-\d+", text)}
        text = update_doc(text, results, env, rel)
        DOC.write_text(text, encoding="utf-8")
        prd = ROOT / "docs" / "prd.md"
        if prd.exists():
            new_prd, changed = update_prd(prd.read_text(encoding="utf-8"), doc_tc_status(text))
            prd.write_text(new_prd, encoding="utf-8")
            for c in changed:
                print(f"  prd.md: {c}")

    unmapped = [c for c in cases if not (tc_id(c["name"]) or tc_id(c["cls"]))]
    missing = sorted(set(results) - in_doc)
    manual = sorted(in_doc - set(results))
    llm = os.environ.get("E2E_LLM_PROVIDER", "mock")
    lines = [
        f"# 시험 실행 {run_id}",
        "",
        f"- 소스 SHA: `{sha}`"
        + (" — ⚠️ 커밋하지 않은 코드 변경 포함 (제출 근거 아님)" if dirty else ""),
        f"- 전체: {overall}"
        + (f" (실패 묶음: {', '.join(failed_suites)})" if failed_suites else "")
        + (f" (결과 없음: {', '.join(missing_suites)})" if missing_suites else ""),
        f"- 실행 시각: {env['실행 시각']}",
        f"- 환경: {env['OS·런타임']}",
        f"- 명령: `make e2e` (scripts/e2e.sh) — E2E는 격리 로컬 배포(새 DB·LLM `{llm}`)에 실행",
        "",
        "| 묶음 | 결과 | 원본 |",
        "|---|---|---|",
    ]
    for fname, label in SUITES.items():
        lines.append(f"| {label} | {ran[label]} | `{fname}` |")
    lines += ["", "## TC별 결과", "", "| TC | 결과 | 테스트 |", "|---|---|---|"]
    for tid in sorted(results):
        tests = "<br>".join(
            f"{c['suite']}: `{c['name']}` {c['status']}" for c in results[tid]["tests"]
        )
        lines.append(f"| {tid} | {results[tid]['status']} | {tests} |")
    if missing:
        lines += ["", f"⚠️ 테스트는 있는데 e2e-test.md에 없는 TC: {', '.join(missing)}"]
    if manual:
        lines += ["", f"자동 시험이 없는 TC (수동 시험·미실행): {', '.join(manual)}"]
    unmapped_fail = [c for c in unmapped if c["status"] == "FAIL"]
    lines += ["", f"TC ID가 없는 테스트 {len(unmapped)}개 (회귀 시험, 실패 {len(unmapped_fail)})"]
    lines += [f"- FAIL {c['suite']}: `{c['name']}`" for c in unmapped_fail]
    (ev_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    n_pass = sum(r["status"] == "PASS" for r in results.values())
    n_fail = sum(r["status"] == "FAIL" for r in results.values())
    where = (ev_dir / "summary.md").relative_to(ROOT)
    print(f"  전체 {overall} · TC {len(results)}개 (PASS {n_pass} · FAIL {n_fail}) → {where}")
    if missing:
        print(f"  ⚠️ e2e-test.md에 없는 TC: {', '.join(missing)} — 시험 목록에 행을 추가하세요")
    if dirty:
        print("  ⚠️ 커밋하지 않은 코드 변경이 있어 제출 근거가 아닙니다 — 커밋 후 다시 make e2e")
    return 0


if __name__ == "__main__":
    sys.exit(main())
