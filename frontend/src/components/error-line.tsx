import { CircleAlertIcon, RotateCwIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

// KDS: 오류는 상자 없이 아이콘 + 빨간 글자 한 줄. 다시 시도할 수 있으면 onRetry를 넘긴다.
// children에는 "저장된 결과 보기" 같은 다른 선택지를 넣는다.
export function ErrorLine({
  message,
  onRetry,
  children,
  className,
}: {
  message: string
  onRetry?: () => void
  children?: React.ReactNode
  className?: string
}) {
  return (
    <div role="alert" className={cn('flex flex-wrap items-center gap-x-3 gap-y-2', className)}>
      <p className="flex items-center gap-1.5 text-sm text-destructive">
        <CircleAlertIcon className="size-4 shrink-0" aria-hidden />
        {message}
      </p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RotateCwIcon /> 다시 시도
        </Button>
      )}
      {children}
    </div>
  )
}
