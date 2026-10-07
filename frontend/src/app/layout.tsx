import type { Metadata } from 'next'
import { Geist_Mono } from 'next/font/google'
import 'pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css'
import { AppShell } from '@/components/app-shell'
import { Providers } from '@/components/providers'
import './globals.css'

const geistMono = Geist_Mono({ variable: '--font-geist-mono', subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'KT Group AI Opportunity Radar',
  description: 'AI 활용 트렌드로 KT 그룹사의 AI 사업 기회와 PoC를 설계하는 에이전트',
}

export default function RootLayout({ children }: LayoutProps<'/'>) {
  return (
    <html
      lang="ko"
      suppressHydrationWarning
      className={`${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  )
}
