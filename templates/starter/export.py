#!/usr/bin/env python3
"""본선 시작 키트 내보내기 — 이 레포의 공용 부분 + 로컬 실행용 덮어쓰기 + 제출 문서 8개.

사용:
  python3 templates/starter/export.py <대상 폴더> [--force] [--dry-run]

- 대상 폴더는 배정받은 팀 레포를 clone한 곳 (빈 폴더도 가능).
- 대상에 이미 있는 파일은 **건너뛰고 목록을 보여 준다** (주최 측이 넣어 둔 README 등 보호).
  --force면 덮어쓴다. 단 주최 측 파일(PROTECTED)은 --force여도 건드리지 않는다.
- 기능 코드(trends·radar·product)·배포 설정(Vercel·Render·Supabase)은 빠진다.
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

# 이 레포에서 가져올 파일 (git이 추적하는 파일만, glob)
INCLUDE = [
    ".claude/**",
    ".github/pull_request_template.md",
    ".github/workflows/security.yml",
    ".gitignore",
    ".gitleaks.toml",
    "scripts/sync.sh",
    "scripts/check-conflicts.sh",
    "scripts/new-worktree.sh",
    "scripts/session-context.sh",
    "scripts/pr_review_score.py",
    "scripts/test_pr_review_score.py",
    ".github/workflows/pr-review.yml",
    "docs/superpowers/specs/2026-10-03-pr-review-scoring-design.md",
    "backend/**",
    "frontend/**",
    "docs/contracts/README.md",
    "docs/contracts/chat.md",
    "docs/contracts/health.md",
    "docs/decisions/0000-template.md",
]
# 그중 뺄 것 (이 레포의 주제 기능·배포 전용)
EXCLUDE = [
    ".claude/skills/deploy-status/**",
    "backend/data/**",
    "backend/evals/**",
    "backend/app/*/trends.py",
    "backend/app/*/radar.py",
    "backend/app/*/product.py",
    "backend/app/services/snapshot.py",
    "backend/app/agent/tools/get_ai_usage_trends.py",
    "backend/tests/test_trends.py",
    "backend/tests/test_radar.py",
    "backend/tests/test_product.py",
    "backend/tests/test_snapshot.py",
    "backend/tests/test_contracts.py",
    "backend/tests/test_tool_get_ai_usage_trends.py",
    "frontend/src/app/trends/**",
    "frontend/src/app/radar/**",
    "frontend/src/app/product/**",
    "frontend/src/features/trends/**",
    "frontend/src/features/radar/**",
    "frontend/src/features/product/**",
    "frontend/vercel.json",
]
# 주최 측이 제공하는 파일 — 어떤 경우에도 덮어쓰지 않는다
PROTECTED = ["docs/security-policy.md", ".github/ISSUE_TEMPLATE/**"]

# (파일, 바꿀 문자열, 새 문자열) — 원본이 바뀌어 문자열이 없으면 실패해서 알 수 있게 한다
PATCHES = [
    (
        "frontend/src/app/layout.tsx",
        "  title: 'KT Group AI Opportunity Radar',\n"
        "  description: 'AI 활용 트렌드로 KT 그룹사의 AI 사업 기회와 PoC를 설계하는 에이전트',",
        "  title: '서비스 이름',\n  description: '한 줄 소개',",
    ),
    (
        "frontend/src/app/agent/page.tsx",
        "title: 'AI 에이전트 · KT Group'",
        "title: 'AI 에이전트'",
    ),
    (
        "frontend/src/features/chat/ChatView.tsx",
        "// 서비스 주제(AI 활용 트렌드 → KT 그룹 사업 기회)에 맞춘 예시."
        " 에이전트 도구 get_ai_usage_trends로 답할 수 있는 질문\n"
        "const EXAMPLES = [\n"
        "  '한국에서 업무용 AI 활용은 1년 동안 어떻게 바뀌었어?',\n"
        "  '한국과 미국의 AI 활용 주제를 비교해 줘',\n"
        "  'KT Cloud가 주목할 만한 AI 활용 트렌드는?',\n]",
        "// 주제에 맞춘 예시 질문으로 바꾼다 (에이전트 도구로 답할 수 있는 질문)\n"
        "const EXAMPLES = ['지금 몇 시야?', '1234 곱하기 5678은?']",
    ),
    (
        "frontend/src/features/chat/ToolStep.tsx",
        "  get_ai_usage_trends: 'AI 활용 트렌드 조회',\n",
        "",
    ),
    (
        "frontend/src/lib/sse.ts",
        '(계약: docs/contracts/radar.md "스트림 형식")',
        "(계약: docs/contracts/chat.md)",
    ),
    (
        "frontend/src/features/chat/ToolStep.tsx",
        "const regionNames = new Intl.DisplayNames(['ko'], { type: 'region' })\n\n",
        "",
    ),
    (
        "frontend/src/features/chat/ToolStep.tsx",
        "  if (name === 'get_ai_usage_trends') {\n"
        "    const country = typeof input.country === 'string'"
        " ? safeRegion(input.country) : '전 세계'\n"
        "    const months = typeof input.months === 'number' ? input.months : 12\n"
        "    return `${country} · 최근 ${months}개월 비교`\n"
        "  }\n",
        "",
    ),
    (
        "frontend/src/features/chat/ToolStep.tsx",
        "function safeRegion(code: string): string {\n"
        "  try {\n"
        "    return regionNames.of(code) ?? code\n"
        "  } catch {\n"
        "    return code\n"
        "  }\n"
        "}\n\n",
        "",
    ),
    (
        "backend/app/agent/stages.py",
        '"""단계형 LLM 생성 파이프라인 실행 (radar·product 공통).',
        '"""단계형 LLM 생성 파이프라인 실행.',
    ),
    (
        "backend/app/agent/stages.py",
        '계약: docs/contracts/radar.md "스트림 형식"',
        "계약: docs/contracts/stages.md",
    ),
    (
        "backend/app/agent/stages.py",
        "(예: opportunity)",
        "",
    ),
    (
        "backend/app/agent/structured.py",
        '"""구조화 출력 + 단계형 SSE 헬퍼 (radar·product 공통). 계약: docs/contracts/radar.md',
        '"""구조화 출력 + 단계형 SSE 헬퍼. 계약: docs/contracts/stages.md',
    ),
    (
        "backend/app/services/chat.py",
        "Supabase 클라이언트는 동기라 모두 스레드에서 호출한다",
        "DB 호출(sqlite3)은 동기라 모두 스레드에서 호출한다",
    ),
    (
        "docs/contracts/README.md",
        "- [trends](trends.md) — OpenAI Signals 트렌드 지표 (#22)\n"
        "- [radar](radar.md) — 그룹사 + Opportunity 생성 (SSE, #23)\n"
        "- [product](product.md) — Product Card·PoC 생성 (SSE, #24)\n",
        "- [stages](stages.md) — LLM 단계형 생성 공통 스트림 형식\n",
    ),
    (
        "docs/contracts/README.md",
        "- Base: 로컬 `http://localhost:8000`, 배포 `https://hackathon-kt-api.onrender.com`",
        "- Base: 로컬 `http://localhost:8000`",
    ),
    (
        "docs/contracts/health.md",
        "(`db` = Supabase 연결·키 확인 결과. DB 장애여도 health는 200 — Render 헬스체크가 서비스를"
        " 내리지 않도록)",
        "(`db` = SQLite 연결·마이그레이션 확인 결과, `version` = 실행 중인 git 커밋."
        " DB 장애여도 health는 200)",
    ),
    (
        ".claude/settings.json",
        '      "Bash(scripts/smoke.sh:*)",\n',
        '      "Bash(python3 scripts/check-docs.py:*)",\n'
        '      "Bash(make help)",\n      "Bash(make verify)",\n      "Bash(make status)",\n'
        '      "Bash(make docs)",\n      "Bash(make smoke)",\n',
    ),
    (
        ".claude/rules/frontend.md",
        " (예: `features/radar/api.ts`의 `saveSelectedOpportunity`)",
        "",
    ),
    (
        ".claude/rules/frontend.md",
        "(`features/chat|radar|product/api.ts`)",
        "(`features/chat/api.ts`)",
    ),
    (
        ".claude/rules/frontend.md",
        "구조·분업 규칙은 `docs/architecture.md`.",
        "구조·분업 규칙은 `CLAUDE.md`.",
    ),
    (
        ".claude/skills/add-page/SKILL.md",
        ", 예시는 `features/trends/TrendCharts.tsx`",
        ", 예시는 `features/samples/DashboardSample.tsx`",
    ),
    (
        ".claude/skills/add-page/SKILL.md",
        " (예: radar → product, `sessionStorage`)",
        " (`sessionStorage`)",
    ),
    (
        "backend/tests/test_quota.py",
        "from app.agent.providers.mock import MockProvider\n",
        "",
    ),
    (
        "backend/tests/test_quota.py",
        "def test_spoofed_forwarded_for_does_not_bypass_quota(monkeypatch, use_provider):\n"
        "    from app.core.config import settings\n\n"
        '    monkeypatch.setattr(settings, "chat_rate_per_ip", 2)\n'
        "    use_provider(MockProvider())\n",
        "def test_spoofed_forwarded_for_does_not_bypass_quota(monkeypatch):\n"
        "    from app.core.config import settings\n\n"
        '    monkeypatch.setattr(settings, "chat_rate_per_ip", 2)\n'
        '    owner = {"X-Client-Id": "quota-client"}\n'
        '    conv = client.post("/api/chat/conversations", json={}, headers=owner).json()\n',
    ),
    (
        "backend/tests/test_quota.py",
        "        # 같은 요청은 재사용돼 한도를 쓰지 않으므로 요청마다 count를 바꾼다\n"
        '        body = {"company_id": "kt-cloud", "count": count}\n'
        '        return client.post("/api/radar/opportunities", json=body, headers=headers)'
        ".status_code\n",
        "        url = f\"/api/chat/conversations/{conv['id']}/messages\"\n"
        '        body = {"content": f"{count} 더하기 1"}\n'
        "        return client.post(url, json=body, headers={**owner, **headers}).status_code\n",
    ),
    (
        "docs/contracts/chat.md",
        "`database/migrations/0002_chat.sql`",
        "`database/migrations/0001_chat.sql`",
    ),
    (
        ".claude/skills/sync/SKILL.md",
        "`uv pip install -r requirements-dev.txt`",
        "`.venv/bin/pip install -r requirements-dev.txt`",
    ),
    (
        ".github/pull_request_template.md",
        "(frontend: lint+build / backend: ruff+pytest)",
        "(frontend: lint+test+build / backend: ruff+ty+pytest)",
    ),
    (
        ".claude/agents/reviewer.md",
        "**import 방향**(ADR 0007)",
        "**import 방향**(`CLAUDE.md` 구조)",
    ),
    (
        "backend/app/core/__init__.py",
        "(docs/decisions/0007-folder-structure.md)",
        "(CLAUDE.md 협업 규칙 5)",
    ),
    (
        ".github/workflows/security.yml",
        "# 설정: .gitleaks.toml · 문서: docs/SDLC.md",
        "# 설정: .gitleaks.toml",
    ),
    (
        ".gitleaks.toml",
        "(2026-10-02 실제로 정체불명의 53자 값이 들어갈 뻔함, docs/worklog/2026-10-02.md).",
        "(실제로 정체불명의 긴 값이 들어갈 뻔한 적이 있음).",
    ),
    (
        "frontend/eslint.config.mjs",
        '    ".next/**",\n',
        '    ".next/**",\n    ".next-e2e/**", // scripts/e2e.sh 격리 빌드\n',
    ),
    (
        ".github/workflows/pr-review.yml",
        "          pip install uv\n          uv venv\n"
        "          uv pip install -r requirements-dev.txt\n",
        "          python -m venv .venv\n"
        "          .venv/bin/pip install -r requirements-dev.txt\n",
    ),
    (
        ".github/workflows/pr-review.yml",
        "ty check --output-format concise app tests evals",
        "ty check --output-format concise app tests",
    ),
    (
        "scripts/pr_review_score.py",
        'TEST_RE = re.compile(r"^(backend/tests/.+|.+\\.test\\.(ts|tsx))$")',
        'TEST_RE = re.compile(r"^(backend/tests/.+|e2e/.+|.+\\.test\\.(ts|tsx))$")  # e2e/: 키트',
    ),
    (
        ".gitignore",
        "# 일반\n",
        "# 로컬 DB (SQLite)\nbackend/data/*.db\nbackend/data/*.db-*\n\n"
        "# 로컬 배포·시험 실행 파일 (scripts/serve.sh·e2e.sh)\n"
        ".run/\nfrontend/.next-e2e/\n\n# 일반\n",
    ),
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
        print(f"\n이미 있어서 건너뜀 {len(skipped)}개 (내용 비교 후 직접 합치거나 --force):")
        print("\n".join(f"  {p}" for p in skipped))
    if not dry:
        print(
            "\n다음: CLAUDE.md·README.md·docs/의 {{자리표시}} 채우기 → "
            "docs/submission-guide.md 순서대로. 셋업 명령은 README.md '실행'."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
