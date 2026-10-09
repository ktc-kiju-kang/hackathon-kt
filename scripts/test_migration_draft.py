"""migration_draft.py · lib.sh migration_gate 시험 — 새 마이그레이션이 계약의 테이블 SQL 초안 그대로인지."""

import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).parent
spec = importlib.util.spec_from_file_location("migration_draft", SCRIPTS / "migration_draft.py")
md = importlib.util.module_from_spec(spec)
spec.loader.exec_module(md)

CONTRACT = """# memo

## POST /api/memo
Response 201: { ... }

## 테이블 (SQL 초안)
초안 설명 줄은 SQL이 아니다.

    CREATE TABLE memos (
      id bigint generated always as identity primary key,
      content text not null,  -- 200자 이하
      created_at timestamptz not null default now()
    );
    CREATE INDEX memos_created_idx ON memos (created_at desc);

## 변경 이력
"""

SAME = """-- REQ-01 메모
create table memos(id bigint generated always as identity primary key,
  content text not null, created_at timestamptz not null default now());
create index memos_created_idx on memos(created_at desc);
"""


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60, **kw)


class NormalizeTest(unittest.TestCase):
    def test_ignores_comments_case_and_spacing(self):
        self.assertEqual(md.normalize(md.draft_sql(CONTRACT)), md.normalize(SAME))

    def test_draft_is_only_the_table_section_code(self):
        sql = md.draft_sql(CONTRACT)
        self.assertIn("CREATE TABLE memos", sql)
        self.assertNotIn("설명 줄", sql)
        self.assertNotIn("POST", sql)
        fenced = "## 테이블\n```sql\ncreate table a (id int);\n```\n## 다음\n    create table b (id int);\n"
        self.assertEqual(md.normalize(md.draft_sql(fenced)), ["create table a(id int)"])
        self.assertEqual(md.draft_sql("# x\n## API\n    create table c (id int);\n"), "")


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = self.tmp / "repo"
        self.env = {
            **{k: v for k, v in os.environ.items() if not k.startswith(("TICKET_", "SHIP_"))},
            "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
        }
        run(["git", "init", "-q", "--bare", str(self.tmp / "origin.git")])
        run(["git", "init", "-q", "-b", "main", str(self.repo)])
        self.git("remote", "add", "origin", str(self.tmp / "origin.git"))
        (self.repo / "scripts").mkdir()
        for name in ("migration_draft.py", "lib.sh"):
            shutil.copy(SCRIPTS / name, self.repo / "scripts" / name)
        self.commit({"database/migrations/0001_chat.sql": "create table chat (id int);\n", "docs/contracts/memo.md": CONTRACT,
                     "docs/contracts/README.md": "## 테이블 (SQL 초안)\n    CREATE TABLE <이름> (...);\n"})
        self.git("push", "-q", "origin", "main")
        self.git("fetch", "-q", "origin")
        self.git("switch", "-q", "-c", "feat/2-memo-api")

    def git(self, *args):
        r = run(["git", "-C", str(self.repo), *args], env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)

    def commit(self, files):
        for path, text in files.items():
            f = self.repo / path
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "x")

    def check(self):
        return md.check("origin/main", self.repo)

    def test_new_migration_same_as_draft_passes(self):
        self.assertEqual(self.check(), [])  # 새 마이그레이션 없음
        self.commit({"database/migrations/202610092054_add_memos.sql": SAME})
        self.assertEqual(self.check(), [])

    def test_extra_column_or_other_statement_is_reported(self):
        self.commit({"database/migrations/202610092054_add_memos.sql": SAME.replace("content text not null", "content text not null, owner text")})
        self.assertIn("초안에 없는 문장", self.check()[0])
        self.git("reset", "-q", "--hard", "origin/main")
        self.commit({"database/migrations/202610092054_add_memos.sql": SAME + "drop table chat;\n"})
        self.assertEqual(len(self.check()), 1)
        self.assertIn("CREATE TABLE·INDEX가 아닌 문장 — drop table chat", self.check()[0])

    def test_template_in_readme_is_not_a_draft(self):
        self.commit({"database/migrations/202610092054_add_x.sql": "CREATE TABLE <이름> (...);\n"})
        self.assertIn("초안에 없는 문장", self.check()[0])

    def test_editing_an_existing_migration_is_reported(self):
        self.commit({"database/migrations/0001_chat.sql": "create table chat (id int, x int);\n"})
        self.assertIn("기존 마이그레이션을 고치거나 지움 (M)", self.check()[0])

    def test_draft_changed_in_same_pr_does_not_count(self):
        """초안은 base(사람이 G3에서 본 계약)에서 읽는다 — PR이 초안과 마이그레이션을 함께 바꾸면 다르다고 본다."""
        changed = SAME.replace("content text not null", "content text not null, owner text")
        self.commit({"docs/contracts/memo.md": CONTRACT.replace("content text not null,", "content text not null, owner text,"),
                     "database/migrations/202610092054_add_memos.sql": changed})
        self.assertIn("초안에 없는 문장", self.check()[0])

    def test_renamed_or_deleted_migration_is_reported(self):
        self.git("mv", "database/migrations/0001_chat.sql", "database/migrations/0002_chat.sql")
        self.git("commit", "-q", "-m", "mv")
        self.assertTrue(any("기존 마이그레이션을 고치거나 지움 (R" in r for r in self.check()), self.check())

    def gate(self, loop=True, no_merge=False):
        env = {**self.env, "TICKET_LOOP_MERGE": "1" if loop else "", "SHIP_NO_MERGE": "1" if no_merge else ""}
        return run(["bash", "-c", ". scripts/lib.sh; migration_gate 99; echo MERGE"], env=env, cwd=self.repo)

    def test_gate_stops_only_loop_auto_merge(self):
        self.commit({"database/migrations/202610092054_add_memos.sql": SAME.replace("not null default now()", "")})
        r = self.gate()
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("MERGE", r.stdout)
        self.assertIn("초안에 없는 문장", r.stdout)
        self.assertIn("PR #99", r.stderr)
        r = self.gate(no_merge=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("확인하고 머지하세요", r.stdout)
        self.assertEqual(self.gate(loop=False).stdout.strip(), "MERGE")  # 사람이 직접 ship
        self.git("reset", "-q", "--hard", "origin/main")
        self.commit({"database/migrations/202610092054_add_memos.sql": SAME})
        r = self.gate()
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "MERGE"), r.stderr)
        self.git("update-ref", "-d", "refs/remotes/origin/main")  # 대조 실패(base 없음)도 머지하지 않는다
        r = self.gate()
        self.assertEqual(r.returncode, 1)
        self.assertIn("대조 실패", r.stdout)
        self.assertEqual(r.stdout.count("대조 실패"), 1)


if __name__ == "__main__":
    unittest.main()
