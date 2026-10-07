import Link from 'next/link'
import { ArrowRightIcon, ChartLineIcon, LightbulbIcon, RadarIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/page-header'

// 시연 순서대로 세 화면을 안내한다. 기능 UI는 src/features/<feature>/에 둔다.
const STEPS = [
  {
    href: '/trends',
    icon: ChartLineIcon,
    title: 'AI 활용 트렌드',
    description: 'OpenAI Signals로 나라별·업무별 AI 활용이 어떻게 바뀌는지 봐요.',
  },
  {
    href: '/radar',
    icon: RadarIcon,
    title: 'Opportunity Radar',
    description: 'KT 그룹사를 고르면 트렌드 근거와 함께 AI 사업 기회를 찾아요.',
  },
  {
    href: '/product',
    icon: LightbulbIcon,
    title: 'Product Generator',
    description: '고른 사업 기회를 프로덕트 카드와 PoC 계획으로 만들어요.',
  },
]

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-5xl space-y-10 px-4 py-12">
      <PageHeader
        title="KT Group AI Opportunity Radar"
        description="공개 AI 활용 데이터로 트렌드를 읽고, KT 그룹사의 사업 기회와 PoC까지 설계해요."
      />

      <ol className="grid gap-4 md:grid-cols-3">
        {STEPS.map(({ href, icon: Icon, title, description }, i) => (
          <li key={href}>
            <Link
              href={href}
              className="flex h-full flex-col gap-3 rounded-xl border border-border p-5 transition-colors hover:bg-muted"
            >
              <span className="flex items-center gap-2 text-sm text-muted-foreground">
                <Icon className="size-4" aria-hidden />
                {i + 1}단계
              </span>
              <span className="text-xl font-semibold">{title}</span>
              <span className="text-sm text-muted-foreground">{description}</span>
            </Link>
          </li>
        ))}
      </ol>

      <Button asChild size="lg">
        <Link href="/trends">
          시작하기 <ArrowRightIcon />
        </Link>
      </Button>
    </main>
  )
}
