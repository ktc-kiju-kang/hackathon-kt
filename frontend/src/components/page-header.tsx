import { cn } from '@/lib/utils'

// 화면 맨 위 제목. KDS: 페이지 타이틀은 32px KT Flow(font-brand), 설명은 보조 글자색.
// actions에는 제목 오른쪽에 둘 필터·버튼을 넣는다.
export function PageHeader({
  title,
  description,
  actions,
  className,
}: {
  title: React.ReactNode
  description?: React.ReactNode
  actions?: React.ReactNode
  className?: string
}) {
  return (
    <header className={cn('flex flex-wrap items-end justify-between gap-3', className)}>
      <div className="space-y-2">
        <h1 className="font-brand text-[32px] leading-tight font-bold tracking-tight">{title}</h1>
        {description && <p className="text-[15px] text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  )
}
