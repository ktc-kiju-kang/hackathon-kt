import Link from 'next/link'
import { ArrowRightIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/page-header'
import { HealthCard } from '@/features/health/HealthCard'

// 홈. 주제가 정해지면 서비스 소개와 첫 화면으로 가는 버튼으로 바꾼다. 기능 UI는 src/features/<feature>/에 둔다.
export default function Home() {
  return (
    <main className="mx-auto w-full max-w-5xl space-y-10 px-4 py-12">
      <PageHeader title="서비스 이름" description="한 줄 소개 — 누가, 무엇을, 왜" />
      <HealthCard />
      <Button asChild size="lg">
        <Link href="/agent">
          AI 에이전트 열기 <ArrowRightIcon />
        </Link>
      </Button>
    </main>
  )
}
