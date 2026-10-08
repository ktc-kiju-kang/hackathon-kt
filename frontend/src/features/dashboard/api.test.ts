import { describe, expect, it } from 'vitest'
import { formatUptime, runState, testedSameAsRunning } from './api'

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
