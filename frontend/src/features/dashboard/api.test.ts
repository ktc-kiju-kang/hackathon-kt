import { describe, expect, it } from 'vitest'
import { formatUptime, parseSuite, reqProgress, runState, testedSameAsRunning, testTotals } from './api'

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
