import { HealthCard } from '@/features/health/HealthCard'

// 화면 조립만 담당. 기능 UI는 src/features/<feature>/, 새 화면은 src/app/<route>/page.tsx
export default function Home() {
  return (
    <main className="mx-auto w-full max-w-3xl px-4 py-12">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">KT 해커톤</h1>
        <p className="mt-2 text-muted-foreground">프로젝트 주제 확정 전 기본 화면입니다.</p>
      </header>

      <div className="grid gap-6">
        <HealthCard />
      </div>
    </main>
  )
}
