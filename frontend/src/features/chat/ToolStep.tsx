import { CheckIcon, CircleAlertIcon, LoaderCircleIcon } from 'lucide-react'
import type { ToolActivity } from './useChat'

// 도구 실행을 한글 단계로 보여 주고, 원문(JSON)은 접어 둔다
const TOOL_LABEL: Record<string, string> = {
  calculator: '계산',
  get_current_time: '현재 시간 확인',
}

function describeInput(name: string, input: Record<string, unknown>): string {
  if (name === 'calculator' && typeof input.expression === 'string') return input.expression
  return ''
}

export function ToolStep({ tool }: { tool: ToolActivity }) {
  const pending = tool.result === undefined
  const detail = describeInput(tool.name, tool.input)
  return (
    <div className="space-y-1 text-xs text-muted-foreground">
      <p className="flex items-center gap-1.5">
        {pending ? (
          <LoaderCircleIcon className="size-3.5 animate-spin" aria-hidden />
        ) : tool.isError ? (
          <CircleAlertIcon className="size-3.5 text-destructive" aria-hidden />
        ) : (
          <CheckIcon className="size-3.5" aria-hidden />
        )}
        <span className="font-medium text-foreground">{TOOL_LABEL[tool.name] ?? tool.name}</span>
        {detail && <span>· {detail}</span>}
        <span className={tool.isError ? 'text-destructive' : undefined}>
          · {pending ? '진행 중이에요' : tool.isError ? '실패했어요' : '완료'}
        </span>
      </p>
      <details className="pl-5">
        <summary className="cursor-pointer select-none">원문 보기</summary>
        <pre className="mt-1 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(tool.input, null, 2)}</pre>
        {!pending && <pre className="mt-1 max-h-60 overflow-auto whitespace-pre-wrap">{tool.result}</pre>}
      </details>
    </div>
  )
}
