import { SparklesIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

// AI가 만든 결과 위에 붙이는 표시. KDS에서 빨강은 요청이 있을 때만 쓰므로 회색으로 둔다.
// withNotice: "AI는 실수할 수 있어요" 안내를 함께 보여 준다.
export function AiGeneratedLabel({
  withNotice = false,
  className,
}: {
  withNotice?: boolean
  className?: string
}) {
  return (
    <p className={cn('flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground', className)}>
      <span className="inline-flex items-center gap-1">
        <SparklesIcon className="size-3.5" aria-hidden />
        AI로 생성된 콘텐츠
      </span>
      {withNotice && <span>· AI는 실수할 수 있어요. 중요한 내용은 근거를 확인해 주세요.</span>}
    </p>
  )
}
