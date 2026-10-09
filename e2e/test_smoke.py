"""기본 흐름 E2E — 키트에 들어 있는 기능(health·화면·AI 대화)이 배포 상태에서 동작하는지.

주제 기능의 E2E는 test_<feature>.py로 추가하고 이름에 TC ID를 넣는다
(예: test_tc_01_2_saved_item_survives_reload).
"""

import os

from conftest import read_sse


def test_health_reports_running_source(api):
    body = api.get("/api/health").json()
    assert body["status"] == "ok" and body["db"] == "ok"
    assert body["llm_mode"] in ("mock", "real")  # TC-HEALTH-1·2: 배포 상태에서도 LLM 모드가 보인다
    if want := os.environ.get("E2E_EXPECT_VERSION"):
        assert body["version"] == want  # 시험 결과가 어느 커밋의 것인지 보장


def test_main_pages_render(web):
    for path in ("/", "/agent"):
        assert web.get(path).status_code == 200, path


def test_chat_flow_saves_and_hides_from_others(api, user, other_user):
    conv = api.post("/api/chat/conversations", json={}, headers=user).json()
    url = f"/api/chat/conversations/{conv['id']}/messages"

    with api.stream("POST", url, json={"content": "2+3*4 계산"}, headers=user) as res:
        assert res.status_code == 200
        events = [e for e, _ in read_sse(res)]
    assert events[-1] == "done"

    saved = api.get(url, headers=user).json()
    assert [m["role"] for m in saved][0] == "user" and len(saved) >= 2  # 저장 후 재조회
    assert api.get(url, headers=other_user).status_code == 404  # 다른 사용자에게는 없음
    res = api.post(url, json={"content": "끼어들기"}, headers=other_user)
    assert res.status_code == 404
    assert len(api.get(url, headers=user).json()) == len(saved)  # 저장값 불변
