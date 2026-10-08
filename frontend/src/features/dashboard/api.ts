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
export type Dashboard = {
  generated_at: string
  server: Health
  migrations: Migration[]
  tests: Tests
  reqs: { status: 'ok' | 'none'; items: Req[] }
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
  claims: { issue: number; owner: string | null }[]
}

const now = () => new Date().toISOString()

const MOCK_DASHBOARD: Dashboard = {
  generated_at: now(),
  server: { status: 'mock', time: now(), version: null, db: 'unconfigured', llm: 'mock', uptime_seconds: 0 },
  migrations: [],
  tests: { status: 'none', run_id: null, sha: null, overall: null, ran_at: null, dirty: false, suites: [], tcs: [] },
  reqs: { status: 'none', items: [] },
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
}

export const getDashboard = (): Promise<Dashboard> =>
  isMock ? Promise.resolve(MOCK_DASHBOARD) : request<Dashboard>('/api/dashboard')

export const getGithubStatus = (): Promise<GithubStatus> =>
  isMock ? Promise.resolve(MOCK_GITHUB) : request<GithubStatus>('/api/dashboard/github')

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
