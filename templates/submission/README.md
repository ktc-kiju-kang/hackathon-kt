# {{서비스 이름}}

> {{한 줄 소개 — 누가, 무엇을, 왜}}
> 팀: {{팀 번호}} · 주제: {{주제 번호·이름}} · 제출 SHA: {{40자 commit SHA}}

## 결과 한눈에
| 항목 | 값 | 근거 |
|---|---|---|
| 요구사항 | 검증됨 {{n}} / 전체 {{n}} (주최 {{n}} · 팀 {{n}}) | [prd.md](docs/prd.md) |
| 시험 | PASS {{n}} · FAIL {{n}} · SKIP {{n}} · 미실행 {{n}} | [e2e-test.md](docs/e2e-test.md) |
| 보안 | 적용-검증됨 {{n}} · 적용-미검증 {{n}} · 해당 없음 {{n}} · 예외 {{n}} | [security-compliance.md](docs/security-compliance.md) |
| 완료 Issue | {{n}} / {{n}} | {{Issues 링크}} |

<!-- 위 숫자는 시작 키트의 make record(scripts/readme_summary.py)가 문서의 실제 표를 세어 채운다. 손으로 고치지 않는다 — check-docs가 어긋나면 잡는다. -->

## 문서
| 문서 | 내용 |
|---|---|
| [project-brief.md](docs/project-brief.md) | 문제·사용자·목표·범위 |
| [prd.md](docs/prd.md) | 요구사항(REQ) 인덱스 → REQ별 확인 조건(AC) `docs/prd/` |
| [arch.md](docs/arch.md) | 구조·기술 선택·REQ별 코드 위치 |
| [experience.md](docs/experience.md) | 화면 흐름·UX·KDS 적용 |
| [development.md](docs/development.md) | 개발 과정·AI 활용과 검증 기록 |
| [security-compliance.md](docs/security-compliance.md) | 보안 기준(SEC) 적용·검증 결과 |
| [e2e-test.md](docs/e2e-test.md) | 시험 재현 방법·결과 |
| [security-policy.md](docs/security-policy.md) | 주최 측 보안 기준 (수정하지 않음) |

## 실행
요구 환경: {{Node 20 / Python 3.12 등}}

```sh
# 1. 설치
{{명령}}
# 2. 환경변수 (값은 .env.example 참고, 실제 키는 커밋하지 않음)
{{명령}}
# 3. 기동
{{명령}}   # → http://localhost:{{포트}}
# 4. 시험 (결과는 docs/e2e-test.md)
{{명령}}
# 5. 종료·정리
{{명령}}
```

배포 주소(있으면): {{URL}}

## 구조
```
{{주요 디렉터리 3~6줄}}
```
상세: [arch.md](docs/arch.md)

## 한계
- {{구현하지 않은 것·미검증인 것 — 숨기지 않고 적는다}}
