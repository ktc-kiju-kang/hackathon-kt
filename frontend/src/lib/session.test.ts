import { describe, expect, it } from 'vitest'
import { loadSession, saveSession } from './session'

describe('session', () => {
  it('저장한 값을 다시 읽는다 (sessionStorage가 없으면 메모리)', () => {
    saveSession('t:key', { a: 1 })
    expect(loadSession<{ a: number }>('t:key')).toEqual({ a: 1 })
  })

  it('없는 키는 null', () => {
    expect(loadSession('t:missing')).toBeNull()
  })
})
