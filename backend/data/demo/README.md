# 데모 스냅샷 (LLM 생성 결과)

실시간 생성이 실패할 때(LLM 한도·장애) 화면이 "저장된 결과"로 보여주는 예비안이다. 계약: `docs/contracts/radar.md`·`product.md`의 snapshot.

- **실제 사업 계획이 아니다.** 해커톤 데모용으로 LLM이 만든 제안이다. 근거 수치만 OpenAI Signals v2.0 (CC BY 4.0) 실제 값이다.
- 만든 시각·모델은 파일의 `snapshot` 필드에 있고 화면에도 표시된다.
- 다시 만들기 (실제 LLM 호출, 기회 3건 기준 약 9회·3분):
  `cd backend && .venv/bin/python -m evals.make_demo_snapshot --company kt-cloud --count 3`
- 공개 저장소에 커밋되므로 공개 데이터로만 만들고, 커밋 전에 내용을 확인한다.
