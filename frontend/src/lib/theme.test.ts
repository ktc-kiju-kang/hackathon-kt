import { describe, expect, it } from 'vitest'
import { nextMode, toggleLabel } from './theme'

describe('nextMode', () => {
  it('보이는 테마의 반대로 바꾼다 (시스템 설정이 다크면 resolved=dark)', () => {
    expect(nextMode('dark')).toBe('light')
    expect(nextMode('light')).toBe('dark')
  })
  it('아직 모르면(첫 렌더·저장소 접근 실패 직후) 다크로', () => {
    expect(nextMode(undefined)).toBe('dark')
  })
})

describe('toggleLabel', () => {
  it('누르면 일어나는 일을 이름으로', () => {
    expect(toggleLabel('light')).toBe('다크 모드로 전환')
    expect(toggleLabel('dark')).toBe('라이트 모드로 전환')
  })
})
