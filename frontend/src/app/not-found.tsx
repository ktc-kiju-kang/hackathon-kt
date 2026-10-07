import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/page-header'

export default function NotFound() {
  return (
    <main className="mx-auto w-full max-w-3xl space-y-6 px-4 py-16">
      <PageHeader title="페이지를 찾을 수 없어요" description="주소가 바뀌었거나 없는 페이지예요." />
      <Button asChild>
        <Link href="/">홈으로 가기</Link>
      </Button>
    </main>
  )
}
