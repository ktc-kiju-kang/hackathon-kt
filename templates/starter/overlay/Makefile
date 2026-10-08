# 파이프라인 입구. 상세: docs/pipeline.md
.DEFAULT_GOAL := help
.PHONY: help setup dev verify serve stop status smoke e2e docs submit-check

help: ## 명령 목록
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-13s %s\n", $$1, $$2}'

setup: ## 개발 환경 준비 (의존성·.env) — 처음 한 번, 의존성이 바뀌면 다시
	@scripts/setup.sh

dev: ## 개발 서버 (핫 리로드) api :8000 + web :3000
	@scripts/dev.sh

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

docs: ## 제출 문서 ID 사슬 검사 (작성 중)
	@python3 scripts/check-docs.py --draft

submit-check: ## 제출 직전 확인 → 포털에 넣을 SHA 출력
	@scripts/submit-check.sh
