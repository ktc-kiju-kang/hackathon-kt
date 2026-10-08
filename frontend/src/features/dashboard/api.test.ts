import { describe, expect, it } from 'vitest'
import {
  countdown,
  failureAlerts,
  formatUptime,
  memberStats,
  parseSuite,
  reqProgress,
  runState,
  testedSameAsRunning,
  testTotals,
  type Dashboard,
  type GithubStatus,
} from './api'

describe('formatUptime', () => {
  it('큰 단위 두 개까지 보여 준다', () => {
    expect(formatUptime(3 * 86400 + 4 * 3600 + 5 * 60)).toBe('3일 4시간')
    expect(formatUptime(2 * 3600 + 5 * 60 + 9)).toBe('2시간 5분')
    expect(formatUptime(5 * 60)).toBe('5분')
  })
  it('1분 미만은 초, 값이 없으면 -', () => {
    expect(formatUptime(30)).toBe('30초')
    expect(formatUptime(0)).toBe('0초')
    expect(formatUptime(undefined)).toBe('-')
  })
})

describe('testedSameAsRunning', () => {
  it('-dirty를 떼고 앞 7자리로 비교한다', () => {
    expect(testedSameAsRunning('b54b3d891b4b-dirty', 'b54b3d891b4b1f0be69d')).toBe(true)
    expect(testedSameAsRunning('aaaaaaa', 'bbbbbbb')).toBe(false)
  })
  it('어느 쪽이든 모르면 null', () => {
    expect(testedSameAsRunning(null, 'abc')).toBeNull()
    expect(testedSameAsRunning('abc', undefined)).toBeNull()
  })
})

describe('runState', () => {
  it('진행 중·성공·실패·대체됨을 나눈다', () => {
    expect(runState('in_progress', null)).toBe('running')
    expect(runState('completed', 'success')).toBe('ok')
    expect(runState('completed', 'failure')).toBe('fail')
    expect(runState('completed', 'cancelled')).toBe('other')
  })
})

describe('parseSuite·testTotals', () => {
  it('"N개 중 실패 M"을 읽고, 실행 실패 묶음은 missing으로 센다', () => {
    expect(parseSuite('61개 중 실패 2')).toEqual({ total: 61, failed: 2 })
    expect(parseSuite('결과 없음 (실행 실패)')).toBeNull()
    expect(
      testTotals([
        { name: 'a', result: '61개 중 실패 2' },
        { name: 'b', result: '3개 중 실패 0' },
        { name: 'c', result: '결과 없음 (실행 실패)' },
      ]),
    ).toEqual({ total: 64, failed: 2, passed: 62, missing: 1 })
  })
})

describe('reqProgress', () => {
  it('제외된 REQ는 전체에서 뺀다', () => {
    const r = (id: string, state: string) => ({ id, title: '', priority: '', issue: '', state })
    expect(reqProgress([r('REQ-01', '검증됨'), r('REQ-02', '계획'), r('REQ-11', '제외(시간)')])).toEqual({
      verified: 1,
      total: 2,
      byState: [
        ['검증됨', 1],
        ['계획', 1],
      ],
    })
  })
})


describe('countdown', () => {
  const deadline = '2026-10-15T00:00:00+09:00'
  it('남은 일·시:분', () => {
    expect(countdown(deadline, new Date('2026-10-13T21:30:00+09:00')).label).toBe('1일 02:30')
    expect(countdown(deadline, new Date('2026-10-14T23:05:00+09:00')).label).toBe('00:55')
  })
  it('지나면 past', () => {
    expect(countdown(deadline, new Date('2026-10-15T00:00:01+09:00'))).toMatchObject({ past: true, label: '마감 지남' })
  })
})

const NOW = new Date('2026-10-08T12:00:00Z')
const gh = (over: Partial<GithubStatus> = {}): GithubStatus => ({
  status: 'ok',
  message: null,
  repo: 'team/app',
  fetched_at: NOW.toISOString(),
  issues: [],
  pulls: [],
  main_runs: [],
  claims: [],
  main_sha: null,
  recent_merges: [],
  ...over,
})
const pr = (number: number, author: string, checks: 'pass' | 'fail') => ({
  number,
  title: '',
  author,
  branch: '',
  draft: false,
  checks,
  url: `p${number}`,
})
const run = (name: string, url: string, conclusion: string) => ({
  name,
  status: 'completed',
  conclusion,
  sha: url,
  url,
  created_at: NOW.toISOString(),
})

describe('memberStats', () => {
  it('담당·선점·PR·CI 실패·24시간 머지·오래된 선점을 사람별로 센다', () => {
    const rows = memberStats(
      gh({
        issues: [{ number: 1, title: '', assignees: ['kim', 'lee'], labels: [], url: '' }],
        claims: [
          { issue: 1, owner: 'kim', claimed_at: '2026-10-08T10:00:00Z' },
          { issue: 2, owner: 'kim', claimed_at: '2026-10-06T10:00:00Z' }, // 2일 전
        ],
        pulls: [pr(9, 'lee', 'fail'), pr(10, 'lee', 'pass')],
        recent_merges: [
          { number: 5, title: '', author: 'kim', merged_at: '2026-10-08T01:00:00Z' },
          { number: 4, title: '', author: 'kim', merged_at: '2026-10-06T01:00:00Z' }, // 24시간 넘음
        ],
      }),
      NOW,
    )
    expect(rows).toEqual([
      { login: 'kim', issues: 1, claims: 2, pulls: 0, failingPulls: 0, merges24h: 1, staleClaims: [2] },
      { login: 'lee', issues: 1, claims: 0, pulls: 2, failingPulls: 1, merges24h: 0, staleClaims: [] },
    ])
  })
})

describe('failureAlerts', () => {
  const dash = (over: Partial<Dashboard['tests']> = {}, db: 'ok' | 'error' = 'ok') =>
    ({
      server: { status: 'ok', time: '', db },
      tests: { status: 'ok', run_id: 'r1', overall: 'PASS', ...over },
    }) as Dashboard
  it('처음 불러올 때는 알리지 않는다', () => {
    expect(failureAlerts({ data: null, gh: null }, { data: dash({ overall: 'FAIL' }), gh: null })).toEqual([])
  })
  it('PASS→FAIL, 새 실패 실행, DB 끊김', () => {
    expect(failureAlerts({ data: dash(), gh: null }, { data: dash({ overall: 'FAIL' }), gh: null })).toEqual(['시험 실패 — r1'])
    expect(
      failureAlerts({ data: dash({ overall: 'FAIL' }), gh: null }, { data: dash({ overall: 'FAIL' }), gh: null }),
    ).toEqual([]) // 같은 실패를 반복해서 알리지 않는다
    expect(failureAlerts({ data: dash(), gh: null }, { data: dash({}, 'error'), gh: null })).toEqual(['DB 연결이 끊겼어요'])
  })
  it('main 워크플로·PR CI가 새로 실패하면', () => {
    const before = gh({ main_runs: [run('CI', 'a', 'success')], pulls: [pr(9, 'lee', 'pass')] })
    const after = gh({ main_runs: [run('CI', 'b', 'failure'), run('CI', 'a', 'success')], pulls: [pr(9, 'lee', 'fail')] })
    expect(failureAlerts({ data: null, gh: before }, { data: null, gh: after })).toEqual(['main CI 실패 (b)', 'PR #9 CI 실패'])
    expect(failureAlerts({ data: null, gh: after }, { data: null, gh: after })).toEqual([])
  })
})
