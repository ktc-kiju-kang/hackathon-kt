'use client'

import { MoonIcon, SunIcon } from 'lucide-react'
import { useTheme } from 'next-themes'
import { useSyncExternalStore } from 'react'
import { Button } from '@/components/ui/button'
import { nextMode, toggleLabel } from '@/lib/theme'

const noop = () => () => {}

/** 상단 배너의 라이트/다크 전환. 선택은 next-themes가 localStorage에 저장한다. */
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  // 서버 렌더에는 테마를 모른다 — 하이드레이션 뒤에만 아이콘·이름을 정한다
  const mounted = useSyncExternalStore(noop, () => true, () => false)
  const resolved = mounted ? resolvedTheme : undefined
  const label = mounted ? toggleLabel(resolved) : '테마 전환'
  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={label}
      title={label}
      onClick={() => setTheme(nextMode(resolved))}
    >
      {resolved === 'dark' ? <SunIcon /> : <MoonIcon />}
    </Button>
  )
}
