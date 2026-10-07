'use client'

import { ThemeProvider } from 'next-themes'
import { Toaster } from '@/components/ui/sonner'

export function Providers({ children }: { children: React.ReactNode }) {
  // data-mode: KDS 토큰(src/styles/kds-tokens.css)이 [data-mode="dark"]일 때 다크 값으로 바뀐다
  return (
    <ThemeProvider
      attribute={['class', 'data-mode']}
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      {children}
      <Toaster richColors />
    </ThemeProvider>
  )
}
