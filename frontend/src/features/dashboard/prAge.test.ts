import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import type { GithubStatus } from './api'
import { GithubSection } from './DashboardView'
import { elapsedMs, formatElapsed, formatKst } from './prAge'
import { PullRow } from './PullRow'

// 시험은 현재 시각을 고정해서 돌린다 (docs/backlog/e2e-test.md TC-01-2~4)
const NOW = new Date('2026-10-09T10:00:00Z')
const MIN = 60_000
const HOUR = 60 * MIN

type Pull = GithubStatus['pulls'][number]
const pull = (over: Partial<Pull> = {}): Pull => ({
  number: 9,
  title: '열린 PR',
  author: 'lee',
  branch: 'feat/9-x',
  draft: false,
  checks: 'pass',
  url: 'https://github.com/o/r/pull/9',
  opened_at: '2026-10-09T09:30:00Z',
  updated_at: '2026-10-09T05:05:00Z',
  ...over,
})

describe('elapsedMs', () => {
  it('열린 시각부터 now까지의 밀리초', () => {
    expect(elapsedMs('2026-10-09T09:30:00Z', NOW)).toBe(30 * MIN)
  })

  it('시계가 어긋나 열린 시각이 미래여도 음수가 되지 않는다', () => {
    expect(elapsedMs('2026-10-09T10:05:00Z', NOW)).toBe(0)
  })

  it('해석할 수 없는 시각은 NaN', () => {
    expect(Number.isNaN(elapsedMs('not-a-date', NOW))).toBe(true)
  })
})

describe('TC-01-2 formatElapsed', () => {
  it('1시간 미만은 n분', () => {
    expect(formatElapsed(30 * MIN)).toBe('30분')
    expect(formatElapsed(0)).toBe('0분')
    expect(formatElapsed(59 * MIN + 59_000)).toBe('59분')
  })

  it('24시간 미만은 n시간 (분은 버린다)', () => {
    expect(formatElapsed(5 * HOUR)).toBe('5시간')
    expect(formatElapsed(HOUR)).toBe('1시간')
    expect(formatElapsed(23 * HOUR + 59 * MIN)).toBe('23시간')
  })

  it('24시간 이상은 n일 n시간', () => {
    expect(formatElapsed(2 * 24 * HOUR + 3 * HOUR)).toBe('2일 3시간')
    expect(formatElapsed(24 * HOUR)).toBe('1일 0시간')
  })

  it('계산할 수 없으면 빈 칸 표시', () => {
    expect(formatElapsed(Number.NaN)).toBe('-')
  })
})

describe('TC-01-3 formatKst', () => {
  it('UTC를 한국 시간 MM-DD HH:mm로', () => {
    expect(formatKst('2026-10-09T05:05:00Z')).toBe('10-09 14:05')
  })

  it('날짜가 넘어가는 경계(UTC 15시 = KST 다음 날 0시)', () => {
    expect(formatKst('2026-10-08T15:00:00Z')).toBe('10-09 00:00')
    expect(formatKst('2026-12-31T15:30:00Z')).toBe('01-01 00:30')
  })

  it('해석할 수 없는 시각은 -', () => {
    expect(formatKst('not-a-date')).toBe('-')
  })
})

describe('PullRow 화면', () => {
  const render = (p: Pull) => renderToStaticMarkup(createElement(PullRow, { pull: p, now: NOW }))

  it('TC-01-2: 열린 지 30분·5시간·2일 3시간인 줄에 경과 시간이 보인다', () => {
    const rows = [
      pull({ number: 1, opened_at: '2026-10-09T09:30:00Z' }),
      pull({ number: 2, opened_at: '2026-10-09T05:00:00Z' }),
      pull({ number: 3, opened_at: '2026-10-07T07:00:00Z' }),
    ].map(render)
    expect(rows[0]).toContain('30분')
    expect(rows[1]).toContain('5시간')
    expect(rows[2]).toContain('2일 3시간')
  })

  it('TC-01-3: 마지막 업데이트 시각이 KST로 보인다', () => {
    expect(render(pull({ updated_at: '2026-10-09T05:05:00Z' }))).toContain('10-09 14:05')
  })

  it('초안 PR에도 시각이 보이고 기존 정보(작성자·브랜치·CI)는 그대로다', () => {
    const html = render(pull({ draft: true, checks: 'fail' }))
    expect(html).toContain('초안')
    expect(html).toContain('lee')
    expect(html).toContain('feat/9-x')
    expect(html).toContain('CI 실패')
    expect(html).toContain('30분')
  })
})

describe('TC-01-4 GitHub 현황 실패', () => {
  const gh = (over: Partial<GithubStatus>): GithubStatus => ({
    status: 'ok',
    message: null,
    repo: 'o/r',
    fetched_at: '2026-10-09T10:00:00Z',
    issues: [],
    pulls: [],
    main_runs: [],
    claims: [],
    main_sha: null,
    recent_merges: [],
    ...over,
  })
  const render = (g: GithubStatus) => renderToStaticMarkup(createElement(GithubSection, { gh: g, now: NOW }))

  it('error면 경과·업데이트 시각 없이 오류 안내만 보인다', () => {
    const html = render(gh({ status: 'error', message: 'GitHub 응답 실패', pulls: [pull()] }))
    expect(html).toContain('GitHub 응답 실패')
    expect(html).not.toContain('10-09 14:05')
    expect(html).not.toContain('30분')
  })

  it('정상이면 같은 컴포넌트가 PR 줄의 시각을 그린다', () => {
    const html = render(gh({ pulls: [pull()] }))
    expect(html).toContain('10-09 14:05')
    expect(html).toContain('30분')
  })
})
