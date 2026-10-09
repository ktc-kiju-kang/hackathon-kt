// 계약: docs/contracts/dashboard.md (#99)
import { isMock, request } from '@/lib/api-client'

// GET /api/health 와 같은 모양 (docs/contracts/health.md). 기능 폴더끼리 import하지 않아 여기 다시 적는다
export type Health = {
  status: 'ok' | 'mock'
  time: string
  version?: string | null
  db?: 'ok' | 'error' | 'unconfigured'
  llm?: string | null
  uptime_seconds?: number
}

export type Migration = { version: string; applied_at: string }
export type Tests = {
  status: 'ok' | 'none'
  run_id: string | null
  sha: string | null
  overall: 'PASS' | 'FAIL' | null
  ran_at: string | null
  dirty: boolean
  suites: { name: string; result: string }[]
  tcs: { tc: string; result: string; test: string }[]
}
export type Req = { id: string; title: string; priority: string; issue: string; state: string }
export type TestRun = {
  run_id: string
  sha: string | null
  ran_at: string
  overall: 'PASS' | 'FAIL' | null
  total: number
  failed: number
  dirty: boolean
}
export type Check = { key: string; label: string; status: 'ok' | 'fail' | 'na'; detail: string }
export type Dashboard = {
  generated_at: string
  server: Health
  migrations: Migration[]
  tests: Tests
  reqs: { status: 'ok' | 'none'; items: Req[] }
  test_history: TestRun[]
  readiness: { deadline: string; checks: Check[] }
}

export type Checks = 'pass' | 'fail' | 'pending' | 'none'
export type GithubStatus = {
  status: 'ok' | 'unconfigured' | 'error'
  message: string | null
  repo: string | null
  fetched_at: string | null
  issues: { number: number; title: string; assignees: string[]; labels: string[]; url: string }[]
  pulls: {
    number: number
    title: string
    author: string
    branch: string
    draft: boolean
    checks: Checks
    url: string
  }[]
  main_runs: {
    name: string
    status: string
    conclusion: string | null
    sha: string
    url: string
    created_at: string
  }[]
  claims: { issue: number; owner: string | null; claimed_at: string | null }[]
  main_sha: string | null
  recent_merges: { number: number; title: string; author: string; merged_at: string }[]
}

// GET /api/dashboard/leadtime — GitHub 현황과 따로 불러온다 (#107)
export type LeadBucket = { label: string; min_seconds: number; max_seconds: number | null; count: number }
export type LeadTime = {
  status: 'ok' | 'unconfigured' | 'error'
  message: string | null
  repo: string | null
  fetched_at: string | null
  count: number
  median_seconds: number | null
  buckets: LeadBucket[]
}

const now = () => new Date().toISOString()

const MOCK_DASHBOARD: Dashboard = {
  generated_at: now(),
  server: { status: 'mock', time: now(), version: null, db: 'unconfigured', llm: 'mock', uptime_seconds: 0 },
  migrations: [],
  tests: { status: 'none', run_id: null, sha: null, overall: null, ran_at: null, dirty: false, suites: [], tcs: [] },
  reqs: { status: 'none', items: [] },
  test_history: [],
  readiness: { deadline: '2026-10-15T00:00:00+09:00', checks: [] },
}

const MOCK_GITHUB: GithubStatus = {
  status: 'unconfigured',
  message: 'mock 모드 — NEXT_PUBLIC_API_BASE_URL을 설정하면 실제 값을 보여 줍니다',
  repo: null,
  fetched_at: null,
  issues: [],
  pulls: [],
  main_runs: [],
  claims: [],
  main_sha: null,
  recent_merges: [],
}

const MOCK_LEADTIME: LeadTime = {
  status: 'unconfigured',
  message: 'mock 모드 — NEXT_PUBLIC_API_BASE_URL을 설정하면 실제 값을 보여 줍니다',
  repo: null,
  fetched_at: null,
  count: 0,
  median_seconds: null,
  buckets: [],
}

export const getDashboard = (): Promise<Dashboard> =>
  isMock ? Promise.resolve(MOCK_DASHBOARD) : request<Dashboard>('/api/dashboard')

export const getGithubStatus = (): Promise<GithubStatus> =>
  isMock ? Promise.resolve(MOCK_GITHUB) : request<GithubStatus>('/api/dashboard/github')

export const getLeadTime = (): Promise<LeadTime> =>
  isMock ? Promise.resolve(MOCK_LEADTIME) : request<LeadTime>('/api/dashboard/leadtime')

/** 초 → "3일 4시간" · "2시간 5분" · "5분" · "30초" (큰 단위 두 개까지). */
export function formatUptime(seconds: number | undefined): string {
  if (seconds === undefined) return '-'
  const units: [string, number][] = [
    ['일', 86400],
    ['시간', 3600],
    ['분', 60],
  ]
  const parts: string[] = []
  let rest = Math.max(0, Math.floor(seconds))
  for (const [name, size] of units) {
    if (rest >= size) {
      parts.push(`${Math.floor(rest / size)}${name}`)
      rest %= size
    }
    if (parts.length === 2) break
  }
  return parts.length ? parts.join(' ') : `${rest}초`
}

/** 실행 중인 버전과 마지막 시험의 커밋이 같은지 (-dirty는 떼고 앞 7자리로 비교). 모르면 null. */
export function testedSameAsRunning(running?: string | null, tested?: string | null): boolean | null {
  if (!running || !tested) return null
  const short = (v: string) => v.replace(/-dirty$/, '').slice(0, 7)
  return short(running) === short(tested)
}

/** main 워크플로 실행 결과 → 화면 표시. 실패만 강조한다 (KDS: 정상에는 태그를 붙이지 않는다). */
export function runState(status: string, conclusion: string | null): 'ok' | 'fail' | 'running' | 'other' {
  if (status !== 'completed') return 'running'
  if (conclusion === 'success' || conclusion === 'skipped' || conclusion === 'neutral') return 'ok'
  if (conclusion === 'failure' || conclusion === 'timed_out' || conclusion === 'startup_failure') return 'fail'
  return 'other' // cancelled 등 — 새 실행으로 대체된 것
}

/** 시험 묶음 결과 "61개 중 실패 0" → 개수. "결과 없음 (실행 실패)" 등은 null. */
export function parseSuite(result: string): { total: number; failed: number } | null {
  const m = /(\d+)개 중 실패 (\d+)/.exec(result)
  return m ? { total: Number(m[1]), failed: Number(m[2]) } : null
}

/** 모든 묶음 합계. 결과가 없는 묶음(실행 실패)은 missing으로 센다. */
export function testTotals(suites: Tests['suites']) {
  let total = 0
  let failed = 0
  let missing = 0
  for (const s of suites) {
    const p = parseSuite(s.result)
    if (!p) missing += 1
    else {
      total += p.total
      failed += p.failed
    }
  }
  return { total, failed, passed: total - failed, missing }
}

/** REQ 진행: 검증됨 / 전체 (제외는 전체에서 뺀다), 상태별 개수. */
export function reqProgress(items: Req[]) {
  const counted = items.filter((i) => !i.state.startsWith('제외'))
  const byState = new Map<string, number>()
  for (const i of counted) byState.set(i.state, (byState.get(i.state) ?? 0) + 1)
  return {
    verified: counted.filter((i) => i.state === '검증됨').length,
    total: counted.length,
    byState: [...byState.entries()],
  }
}


/** 마감까지 남은 시간. 지났으면 past. */
export function countdown(deadline: string, now: Date) {
  const ms = new Date(deadline).getTime() - now.getTime()
  const past = ms <= 0
  const rest = Math.floor(Math.abs(ms) / 60000)
  const days = Math.floor(rest / 1440)
  const hours = Math.floor((rest % 1440) / 60)
  const minutes = rest % 60
  const hhmm = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
  return { past, days, hours, minutes, label: past ? '마감 지남' : days ? `${days}일 ${hhmm}` : hhmm }
}

export type Member = {
  login: string
  issues: number
  claims: number
  pulls: number
  failingPulls: number
  merges24h: number
  staleClaims: number[]
}

const DAY = 24 * 3600 * 1000

/** GitHub 응답 → 팀원별 집계 (담당 Issue·선점·열린 PR·CI 실패 PR·24시간 머지·24시간 넘은 선점). */
export function memberStats(gh: GithubStatus, now: Date): Member[] {
  const by = new Map<string, Member>()
  const get = (login: string) => {
    let m = by.get(login)
    if (!m) {
      m = { login, issues: 0, claims: 0, pulls: 0, failingPulls: 0, merges24h: 0, staleClaims: [] }
      by.set(login, m)
    }
    return m
  }
  for (const i of gh.issues) for (const a of i.assignees) get(a).issues += 1
  for (const c of gh.claims) {
    if (!c.owner) continue
    const m = get(c.owner)
    m.claims += 1
    if (c.claimed_at && now.getTime() - new Date(c.claimed_at).getTime() > DAY) m.staleClaims.push(c.issue)
  }
  for (const p of gh.pulls) {
    const m = get(p.author)
    m.pulls += 1
    if (p.checks === 'fail') m.failingPulls += 1
  }
  for (const r of gh.recent_merges) {
    if (now.getTime() - new Date(r.merged_at).getTime() <= DAY) get(r.author).merges24h += 1
  }
  return [...by.values()].sort((a, b) => a.login.localeCompare(b.login))
}

/** 새로 고침 사이에 "실패로 바뀐 것" — 화면 알림용. 처음 불러올 때(prev 없음)는 알리지 않는다. */
export function failureAlerts(
  prev: { data: Dashboard | null; gh: GithubStatus | null },
  next: { data: Dashboard | null; gh: GithubStatus | null },
): string[] {
  const out: string[] = []
  const pd = prev.data
  const nd = next.data
  if (pd && nd) {
    if (pd.server.db === 'ok' && nd.server.db !== 'ok') out.push('DB 연결이 끊겼어요')
    const pt = pd.tests
    const nt = nd.tests
    if (nt.overall === 'FAIL' && (pt.overall !== 'FAIL' || pt.run_id !== nt.run_id)) {
      out.push(`시험 실패 — ${nt.run_id}`)
    }
  }
  const pg = prev.gh?.status === 'ok' ? prev.gh : null
  const ng = next.gh?.status === 'ok' ? next.gh : null
  if (pg && ng) {
    const latest = (g: GithubStatus) => {
      const m = new Map<string, GithubStatus['main_runs'][number]>()
      for (const r of g.main_runs) if (!m.has(r.name)) m.set(r.name, r) // 최신이 앞
      return m
    }
    const before = latest(pg)
    for (const [name, r] of latest(ng)) {
      const b = before.get(name)
      if (runState(r.status, r.conclusion) === 'fail' && (!b || b.url !== r.url || runState(b.status, b.conclusion) !== 'fail')) {
        out.push(`main ${name} 실패 (${r.sha})`)
      }
    }
    const wasFailing = new Set(pg.pulls.filter((p) => p.checks === 'fail').map((p) => p.number))
    for (const p of ng.pulls) {
      if (p.checks === 'fail' && !wasFailing.has(p.number)) out.push(`PR #${p.number} CI 실패`)
    }
  }
  return out
}

/** 리드타임 칸 상태. 머지된 PR이 없는 것(empty)은 오류가 아니다. */
export function leadTimeState(lt: LeadTime | null): 'loading' | 'error' | 'unconfigured' | 'empty' | 'ok' {
  if (!lt) return 'loading'
  if (lt.status !== 'ok') return lt.status
  return lt.count === 0 ? 'empty' : 'ok'
}

/** 구간별 건수 → 막대 차트 행 (키는 영문 — ChartConfig 규칙). */
export function leadTimeBars(lt: LeadTime): { label: string; count: number }[] {
  return lt.buckets.map((b) => ({ label: b.label, count: b.count }))
}
