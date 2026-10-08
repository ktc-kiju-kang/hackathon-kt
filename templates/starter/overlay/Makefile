# 파이프라인 입구. 상세: docs/pipeline.md
.DEFAULT_GOAL := help
.PHONY: help setup dev sync verify serve stop status smoke e2e ship record lock-status claims release docs submit-check

help: ## 명령 목록
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-13s %s\n", $$1, $$2}'

setup: ## 개발 환경 준비 (의존성·.env) — 처음 한 번, 의존성이 바뀌면 다시
	@scripts/setup.sh

dev: ## 개발 서버 (핫 리로드) api :8000 + web :3000
	@scripts/dev.sh

sync: ## 최신 main을 지금 브랜치에 merge (작업 시작 전·중간중간)
	@scripts/sync.sh

verify: ## CI와 같은 검사 전부 (lint·type·test·build·문서)
	@scripts/verify.sh

serve: ## 로컬 배포 (프로덕션 빌드, 백그라운드) + 스모크
	@scripts/serve.sh

stop: ## 로컬 배포 종료
	@scripts/stop.sh

status: ## 로컬 배포 상태
	@scripts/status.sh

smoke: ## 떠 있는 서버 스모크 확인
	@scripts/smoke.sh

e2e: ## 시험 전부 + 격리 배포 E2E → docs/e2e-test.md·docs/evidence/ 기록
	@scripts/e2e.sh

ship: ## 작업 브랜치 → 검사·시험·PR·AI 리뷰·자동 머지 (사람은 이것만)
	@scripts/ship.sh

record: ## main에서 시험 기록(e2e-test.md·evidence)을 자동 PR로 머지 — 기록 담당이 2~3시간마다
	@scripts/record.sh

lock-status: ## 머지 잠금 상태 (누가 머지 중인지)
	@scripts/lock-status.sh

claims: ## 누가 어떤 Issue를 잡고 있는지 (선점 목록, 오래 멈춘 것 경고)
	@scripts/claim.sh list

release: ## Issue 선점 해제 (손 뗄 때) — make release ISSUE=12
	@scripts/claim.sh release $(ISSUE)

docs: ## 제출 문서 ID 사슬 검사 (작성 중)
	@python3 scripts/check-docs.py --draft

submit-check: ## 제출 직전 확인 → 포털에 넣을 SHA 출력
	@scripts/submit-check.sh
