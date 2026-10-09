// 열린 PR의 경과 시간·업데이트 시각 표기 (REQ-01). 서버는 GitHub 시각을 그대로 보내고, 현재 시각에 의존하는 계산은 화면이 한다.
// docs/contracts/dashboard.md "화면 확장 지점" — REQ-02(24시간 넘은 PR 강조)가 elapsedMs를 다시 쓴다.

const MIN = 60_000
const HOUR = 60 * MIN
const DAY = 24 * HOUR
const KST_OFFSET = 9 * HOUR

/** 열린 시각부터 now까지의 밀리초. 시계가 어긋나 미래 시각이 와도 음수는 되지 않는다. 해석할 수 없으면 NaN. */
export function elapsedMs(openedAt: string, now: Date | number): number {
  const opened = new Date(openedAt).getTime()
  const at = typeof now === 'number' ? now : now.getTime()
  return Math.max(0, at - opened)
}

/** 24시간을 "넘은" PR인가 (REQ-02). 정확히 24시간은 아니다. 계산할 수 없는 값(NaN)은 강조하지 않는다. */
export function isStale(ms: number): boolean {
  return ms > DAY
}

/** 1시간 미만 "n분", 24시간 미만 "n시간", 그 이상 "n일 n시간" — 모자란 단위는 버린다. */
export function formatElapsed(ms: number): string {
  if (!Number.isFinite(ms)) return '-'
  if (ms < HOUR) return `${Math.floor(ms / MIN)}분`
  if (ms < DAY) return `${Math.floor(ms / HOUR)}시간`
  return `${Math.floor(ms / DAY)}일 ${Math.floor((ms % DAY) / HOUR)}시간`
}

const two = (n: number) => String(n).padStart(2, '0')

/** ISO 시각을 한국 시간 "MM-DD HH:mm"으로. 브라우저 시간대와 무관하게 KST(UTC+9)로 고정한다. */
export function formatKst(iso: string): string {
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return '-'
  const k = new Date(t + KST_OFFSET)
  return `${two(k.getUTCMonth() + 1)}-${two(k.getUTCDate())} ${two(k.getUTCHours())}:${two(k.getUTCMinutes())}`
}
