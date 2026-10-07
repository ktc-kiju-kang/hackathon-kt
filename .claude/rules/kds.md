---
paths:
  - "frontend/**"
---

# KDS 2.0 디자인 규칙 (해커톤 공식 디자인 시스템)

> `frontend/**`를 다룰 때 자동으로 로드된다. 원본은 주최 측 코드 키트의 `AGENTS.md`(각자 `hackathon-rules/kds-hackathon-kit.zip`, gitignore됨)이고, 여기서는 Next.js + Tailwind v4 + shadcn/ui 기준으로 다시 정리했다.
> **KDS가 정하는 것은 생김새다**(색·글꼴·모서리·그림자·차트 색·아이콘). 화면 구성·배치·기능은 정하지 않는다.

## 적용 구조
- `src/styles/kds-tokens.css`: 키트의 토큰 파일 원본. **수정하지 않는다**(Beta라 통째로 교체할 수 있게 둔다).
- `src/app/globals.css`: shadcn 변수(`--primary`·`--border`·`--chart-*`·`--sidebar*` 등)를 KDS 시맨틱 토큰에 연결한다. 그래서 `bg-primary`·`text-muted-foreground`·`border-border` 같은 **기존 테마 클래스를 그대로 쓰면 KDS 색이 나온다**.
- 다크모드: next-themes가 `<html class="dark" data-mode="dark">`를 붙이고, KDS 토큰이 다크 값으로 바뀐다.
- 키트의 `kds-base.css`·`kds-components.css`(`kds-*` 클래스)는 가져오지 않았다. 컴포넌트는 shadcn(`src/components/ui/`)을 쓴다.

## 글꼴 — ⚠️ KT Flow 공개 금지
- 본문·버튼·폼·표: **Pretendard**(npm `pretendard`, 기본 `font-sans`).
- 큰 제목(페이지 타이틀·히어로)만 `font-brand`(KT Flow). 카드 제목·본문·버튼에는 쓰지 않는다.
- **KT Flow 폰트 파일(`KTFLOW*`)은 레포·`public/`·배포에 절대 넣지 않는다**(참가자 전용, 공개 업로드 금지). `globals.css`의 `@font-face`는 `local()`만 쓰므로 폰트를 설치한 시연 PC에서만 KT Flow로, 나머지는 Pretendard로 보인다.

## 점검 기준 (주최 측 6가지 + 자주 고치는 것)
| 규칙 | 우리 코드에서 |
|---|---|
| 주요 버튼은 검정 | shadcn `Button` 기본(`bg-primary` = `--fill-primary`). 보조는 `variant="outline"`. KT 레드(`var(--fill-accent-primary)`)는 사용자가 요청할 때만, 화면당 1곳 |
| 색 비율 8:2 | 흰색·회색 80%, 포인트 색 20%. 큰 면을 색으로 칠하지 않는다 |
| 빨강은 글자 강조·에러에만 | `text-destructive`(= `--text-feedback-critical-01`). 버튼·큰 면·최댓값 강조에 쓰지 않는다 |
| 상자 안에 상자 금지 | 면은 한 겹, 경계는 1px `border-border`. 카드 안에 카드를 넣지 않는다. 섹션 제목은 카드 밖 |
| 그림자는 떠 있는 것에만 | 팝업·드롭다운·시트·툴팁(`shadow-sm/md/lg`는 KDS `--shadow-1~3`). 카드에 그림자를 넣지 않는다 |
| 차트는 teal부터 | `var(--chart-1)`~`--chart-5` = teal → yellow → blue → purple → red. 검정 막대 금지. 비교 기준·나머지는 `var(--data-visual-default-gray)`, 강조 1개는 `var(--data-visual-strong-teal)`. 막대는 가늘게(24~32) |
| 아이콘은 SVG | `lucide-react`. 글자(`<` `>` `X`)·이모지로 대신하지 않는다 |
| 태그는 예외 상태에만 | 정상·기본 상태에는 `Badge`를 붙이지 않는다 |
| 오류는 한 줄 | 아이콘 + 빨간 글자 한 줄. 분홍·노랑 박스로 감싸지 않는다 |
| 빈 상태는 회색 글자 한 줄 | 큰 그림·긴 설명·이모지 금지 |
| 글자 크기 4~5단계 | 32 제목 / 20·24 섹션 / 15·16 본문 / 13·14 보조 / 12 캡션. 위계는 크기보다 **글자색**(`text-foreground` → `text-muted-foreground`)으로 |
| 간격은 바깥이 크게 | 안쪽 8·16 < 요소 사이 24 < 덩어리 사이 40 < 큰 구역 64 |
| 폭 고정 | 대화 748, 폼 932, 콘솔 1200. 화면을 꽉 채우지 않는다 |
| 왼쪽 메뉴 선택 | 연회색 면 + 검정 글자(사이드바 `--sidebar-accent`). 검정 면 금지 |

## 색이 테마 클래스로 안 될 때
- 하드코딩(`#191a1b`, `text-red-500`) 대신 KDS 토큰을 변수로: `bg-[var(--surface-primary-02)]`, `text-[var(--text-tertiary-01)]`.
- 자주 쓰는 토큰: 배경 `--background-default` · 연회색 면 `--surface-primary-02` · 글자 `--text-primary`/`--text-secondary-01`/`--text-tertiary-01` · 선 `--border-secondary-01` · 차트 `--data-visual-default-{teal,yellow,blue,purple,red,gray}`.
- 전체 토큰은 `src/styles/kds-tokens.css`(68KB) — 통째로 읽지 말고 `grep`으로 찾는다.
