#!/usr/bin/env python3
"""본선 시작 키트 내보내기 — 이 레포(= 키트 원본) + 팀 레포용 덮어쓰기 + 제출 문서 8개.

사용:
  python3 templates/starter/export.py <대상 폴더> [--force] [--dry-run]

- 대상 폴더는 배정받은 팀 레포를 clone한 곳 (빈 폴더도 가능).
- 대상에 이미 있는 파일은 **건너뛰고** 키트 버전을 <파일>.kit 로 옆에 둔다 (주최 측 README 보호).
  --force면 덮어쓴다. 단 주최 측 파일(PROTECTED)은 --force여도 건드리지 않는다.
- 이 레포 전용 파일(EXCLUDE)은 빠진다.
"""

import fnmatch
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
KIT = REPO / "templates" / "starter"
SUBMISSION = REPO / "templates" / "submission"

# 이 레포가 곧 키트다 (2026-10-08 정리). 추적 파일을 그대로 내보내고 EXCLUDE(이 레포 전용)만
# 뺀다. 팀 레포용으로 달라야 하는 파일만 overlay/에 있다 (CLAUDE.md, CI).
INCLUDE = ["**"]
EXCLUDE = [
    "templates/**",  # 키트 원본·제출 문서 템플릿 (제출 문서는 아래에서 따로 넣는다)
    "README.md",  # 팀 레포 README는 제출 문서 템플릿에서
    "CLAUDE.md",  # 팀 레포용은 overlay/CLAUDE.md
    ".github/workflows/ci.yml",  # 팀 레포용은 overlay (문서 검사 잡 포함)
    ".github/ISSUE_TEMPLATE/**",  # 주최 측이 넣는다
    ".gitleaksignore",  # 이 레포 이력의 오탐 fingerprint
    "docs/superpowers/plans/**",  # PR 점수 구현 계획 (이 레포 작업 기록)
]
# 주최 측이 제공하는 파일 — 어떤 경우에도 덮어쓰지 않는다
PROTECTED = ["docs/security-policy.md", ".github/ISSUE_TEMPLATE/**"]

# (파일, 바꿀 문자열, 새 문자열) — 원본이 바뀌어 문자열이 없으면 실패해서 알 수 있게 한다
PATCHES = [
    (
        "README.md",
        "요구 환경: {{Node 20 / Python 3.12 등}}\n\n```sh\n"
        "# 1. 설치\n{{명령}}\n"
        "# 2. 환경변수 (값은 .env.example 참고, 실제 키는 커밋하지 않음)\n{{명령}}\n"
        "# 3. 기동\n{{명령}}   # → http://localhost:{{포트}}\n"
        "# 4. 시험 (결과는 docs/e2e-test.md)\n{{명령}}\n"
        "# 5. 종료·정리\n{{명령}}\n```",
        "요구 환경: Node 20+, Python 3.11+"
        " (외부 서비스 없음 — DB는 SQLite, LLM 키가 없으면 mock).\n"
        "단계·게이트·장애 대응: [docs/pipeline.md](docs/pipeline.md)\n\n"
        "```sh\n"
        "make setup    # 1. 설치 (의존성·.env)\n"
        "make verify   # 2. 검사 전부 (lint·type·test·build·문서)\n"
        "make serve    # 3. 로컬 배포 → http://localhost:3000 , API http://localhost:8000/api/docs\n"
        "make e2e      # 4. 시험 + 결과 기록 (docs/e2e-test.md, docs/evidence/)\n"
        "make stop     # 5. 종료 (DB 초기화: rm backend/data/app.db)\n"
        "```\n\n"
        "개발 중에는 `make dev` (핫 리로드). 명령 목록 `make help`.",
    ),
]


JUNK = {".ruff_cache", "__pycache__", ".pytest_cache", ".DS_Store", "node_modules", ".venv"}


def files_under(base: Path) -> list[Path]:
    """overlay·submission 파일 (도구 캐시 제외 — git 추적 여부와 무관하게 폴더째 읽으므로)."""
    files = (p for p in base.rglob("*") if p.is_file())
    return [p for p in files if not JUNK & set(p.relative_to(base).parts)]


def matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, p) or path == p for p in patterns)


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(REPO), "ls-files"], capture_output=True, text=True, check=True
    )
    return out.stdout.splitlines()


def untracked_included() -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [f for f in out.stdout.splitlines() if matches(f, INCLUDE) and not matches(f, EXCLUDE)]


def merge_gitignore(src: Path, dst: Path, dry: bool) -> bool:
    """대상에 .gitignore가 있으면 덮어쓰지 않고 빠진 줄만 덧붙인다 (.env·DB 커밋 방지)."""
    have = set(dst.read_text(encoding="utf-8").splitlines())
    missing = [ln for ln in src.read_text(encoding="utf-8").splitlines() if ln and ln not in have]
    if missing and not dry:
        with dst.open("a", encoding="utf-8") as f:
            f.write("\n# --- 시작 키트 (templates/starter) ---\n" + "\n".join(missing) + "\n")
    return bool(missing)


def build(stage: Path) -> None:
    for rel in tracked_files():
        if matches(rel, INCLUDE) and not matches(rel, EXCLUDE) and (REPO / rel).is_file():
            dst = stage / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / rel, dst)
    # 제출 문서 8개 + 검사기 (GUIDE.md는 docs/submission-guide.md로)
    for src in files_under(SUBMISSION):
        rel = src.relative_to(SUBMISSION)
        dst = stage / ("docs/submission-guide.md" if rel.as_posix() == "GUIDE.md" else rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    # 로컬 실행용 덮어쓰기
    overlay = KIT / "overlay"
    for src in files_under(overlay):
        dst = stage / src.relative_to(overlay)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    for rel, old, new in PATCHES:
        p = stage / rel
        if not p.exists():
            raise SystemExit(f"패치 실패: {rel}이 키트에 없음 (INCLUDE·EXCLUDE 확인)")
        text = p.read_text(encoding="utf-8")
        if old not in text:
            raise SystemExit(f"패치 실패: {rel}에 바꿀 문자열이 없음 (원본 변경 → PATCHES 수정)")
        p.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if len(args) != 1 or flags - {"--force", "--dry-run"}:
        print(__doc__)
        return 2
    dest = Path(args[0]).resolve()
    if dest == REPO or REPO in dest.parents:
        print("대상은 이 레포 밖이어야 합니다")
        return 2
    force, dry = "--force" in flags, "--dry-run" in flags

    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp)
        build(stage)
        written, skipped, protected = [], [], []
        for src in sorted(p for p in stage.rglob("*") if p.is_file()):
            rel = src.relative_to(stage).as_posix()
            dst = dest / rel
            if dst.exists() and dst.read_bytes() == src.read_bytes():
                continue
            if dst.exists() and rel.endswith(".gitignore") and not force:
                if merge_gitignore(src, dst, dry):
                    written.append(f"{rel} (빠진 줄 덧붙임)")
                continue
            if dst.exists() and matches(rel, PROTECTED):
                protected.append(rel)
                continue
            if dst.exists() and not force:
                skipped.append(rel)
                if not dry:  # 합칠 수 있게 키트 버전을 옆에 둔다 (<파일>.kit, 합친 뒤 지운다)
                    shutil.copy2(src, dst.with_name(dst.name + ".kit"))
                continue
            written.append(rel)
            if not dry:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

    if extra := untracked_included():
        print(f"⚠️ git에 추가하지 않은 파일은 빠짐 {len(extra)}개: " + ", ".join(extra[:5]))
    verb = "쓸 파일" if dry else "쓴 파일"
    print(f"{verb} {len(written)}개 → {dest}")
    if protected:
        print(f"\n주최 측 파일이라 건드리지 않음 {len(protected)}개:")
        print("\n".join(f"  {p}" for p in protected))
    if skipped:
        print(f"\n이미 있어서 건너뜀 {len(skipped)}개 — 키트 버전은 <파일>.kit (합친 뒤 삭제):")
        print("\n".join(f"  {p}" for p in skipped))
    if not dry:
        print(
            "\n다음: CLAUDE.md·README.md·docs/의 {{자리표시}} 채우기 → "
            "docs/submission-guide.md 순서대로. 셋업 명령은 README.md '실행'."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
