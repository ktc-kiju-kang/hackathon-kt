#!/usr/bin/env python3
"""make ship의 PR 본문 갱신 — 사람이 쓴 본문은 두고 <!-- ship:start/end --> 구역과 Issue 연결 줄만 다룬다.

사용: python3 scripts/pr_body.py <기존 본문 파일> <ship 블록 파일> <Issue 번호|""> <Closes|Refs>
link=Refs는 이미 닫힌 Issue의 후속 PR: Closes로 이으면 칸반 'PR 연결' 자동화가 닫힌 카드를
In Review로 되돌리고 다시 닫히지 않아 Done으로 돌아오지 않는다 (#109).
"""

import re
import sys

SHIP = re.compile(r"<!-- ship:start -->.*?<!-- ship:end -->", re.S)
# GitHub이 PR 본문 어디에서든 읽는 닫기 키워드 (코드 예시 안이어도 Issue와 연결된다)
CLOSING = re.compile(
    r"(?i)\b(close[sd]?|fix(?:e[sd])?|resolve[sd]?)(:?\s+)((?:[\w.-]+/[\w.-]+)?)#(\d+)"
)


def defuse(text: str) -> str:
    """AI 리뷰 같은 생성 글의 'Closes #12'를 'Closes \\#12'로 — 화면에는 그대로 #12로 보이지만
    GitHub이 Issue 연결로 읽지 않는다. 연결되면 칸반 'PR 연결' 자동화가 닫힌 카드를 되돌린다 (#12)."""
    return CLOSING.sub(lambda m: f"{m[1]}{m[2]}{m[3]}\\#{m[4]}", text)


def update(body: str, block: str, issue: str, link: str) -> str:
    body = SHIP.sub(lambda _: block, body) if SHIP.search(body) else body.rstrip() + "\n\n" + block
    if not issue:
        return body
    if link == "Refs":  # ship이 예전에 맨 앞에 넣은 Closes 줄만 바꾼다 (사람이 쓴 문장은 두고)
        body = re.sub(rf"\A(?:closes|fixes|resolves) #{issue}\b", f"Refs #{issue}", body, flags=re.I)
    if not re.search(rf"(?im)^(closes|fixes|resolves|refs) #{issue}\b", body):
        body = f"{link} #{issue}\n\n" + body
    return body


if __name__ == "__main__":
    old, blk, issue, link = sys.argv[1:5]
    print(update(open(old).read(), open(blk).read().strip(), issue, link))
