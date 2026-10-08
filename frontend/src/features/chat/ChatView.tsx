'use client'

import { useEffect, useRef, useState } from 'react'
import { CircleAlertIcon, CopyIcon, LoaderCircleIcon, PlusIcon, SendIcon, SquareIcon } from 'lucide-react'
import { toast } from 'sonner'
import { AiGeneratedLabel } from '@/components/ai-generated-label'
import { PageHeader } from '@/components/page-header'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { isMock } from '@/lib/api-client'
import { Markdown } from './Markdown'
import { ToolStep } from './ToolStep'
import { useChat } from './useChat'

// 주제에 맞춘 예시 질문으로 바꾼다 (에이전트 도구로 답할 수 있는 질문)
const EXAMPLES = ['지금 몇 시야?', '1234 곱하기 5678은?']

function copy(text: string) {
  if (!navigator.clipboard) {
    toast.error('이 브라우저에서는 복사할 수 없어요')
    return
  }
  navigator.clipboard
    .writeText(text)
    .then(() => toast.success('답변을 복사했어요'))
    .catch(() => toast.error('복사하지 못했어요'))
}

export function ChatView() {
  const { items, busy, send, stop, reset } = useChat()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [items])

  const submit = () => {
    void send(input)
    setInput('')
  }

  return (
    // 3rem = AppShell 상단 헤더(h-12). 메시지는 페이지가 아니라 목록 안에서 스크롤된다.
    <div className="mx-auto flex h-[calc(100svh-3rem)] w-full max-w-[780px] flex-col gap-4 px-4 py-6">
      <PageHeader
        title={
          <span className="flex items-center gap-2">
            AI 에이전트 {isMock && <Badge variant="secondary">mock</Badge>}
          </span>
        }
        description="AI 활용 트렌드 데이터를 찾아보며 질문에 답해요"
        actions={
          <Button variant="outline" size="sm" onClick={reset} disabled={busy && items.length === 0}>
            <PlusIcon /> 새 대화
          </Button>
        }
      />

      <div role="log" aria-live="polite" aria-label="대화 내용" className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
        {items.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-muted-foreground">
            <p>AI 활용 트렌드나 KT 그룹 사업 기회에 대해 물어보세요.</p>
            <div className="flex flex-wrap justify-center gap-2">
              {EXAMPLES.map((q) => (
                <Button key={q} variant="outline" size="sm" onClick={() => void send(q)}>
                  {q}
                </Button>
              ))}
            </div>
          </div>
        )}
        {items.map((item, i) =>
          item.kind === 'user' ? (
            <div key={i} className="flex justify-end">
              <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl bg-primary px-4 py-2 text-primary-foreground">
                {item.text}
              </div>
            </div>
          ) : (
            <div key={i} className="max-w-[85%] space-y-2">
              {item.tools.map((t) => (
                <ToolStep key={t.id} tool={t} />
              ))}
              {item.text.trim() ? (
                <div className="rounded-2xl bg-muted px-4 py-2">
                  <Markdown>{item.text.trim()}</Markdown>
                </div>
              ) : (
                item.streaming &&
                !item.status &&
                !item.error && (
                  <p className="flex items-center gap-1.5 px-1 text-xs text-muted-foreground">
                    <LoaderCircleIcon className="size-3.5 animate-spin" aria-hidden /> 답변을 만들고 있어요
                  </p>
                )
              )}
              {item.stopped && <p className="px-1 text-xs text-muted-foreground">응답을 멈췄어요</p>}
              {!item.streaming && item.text.trim() && !item.error && (
                <div className="flex items-center gap-2 px-1">
                  <AiGeneratedLabel />
                  <Button variant="ghost" size="icon-sm" aria-label="답변 복사" onClick={() => copy(item.text.trim())}>
                    <CopyIcon />
                  </Button>
                </div>
              )}
              {item.status && (
                <p className="flex items-center gap-1.5 px-1 text-xs text-muted-foreground">
                  <LoaderCircleIcon className="size-3.5 animate-spin" /> {item.status}
                </p>
              )}
              {item.error && (
                <p role="alert" className="flex items-center gap-1.5 px-1 text-sm text-destructive">
                  <CircleAlertIcon className="size-4 shrink-0" /> {item.error}
                </p>
              )}
            </div>
          ),
        )}
        <div ref={bottomRef} />
      </div>

      <form
        className="flex items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          submit()
        }}
      >
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault()
              submit()
            }
          }}
          placeholder="질문을 입력해 주세요 (Enter 전송, Shift+Enter 줄바꿈)"
          className="max-h-40 min-h-11 resize-none"
          rows={1}
        />
        {busy ? (
          <Button type="button" size="icon" variant="outline" onClick={stop} aria-label="중지">
            <SquareIcon />
          </Button>
        ) : (
          <Button type="submit" size="icon" disabled={!input.trim()} aria-label="전송">
            <SendIcon />
          </Button>
        )}
      </form>
      <p className="-mt-2 text-center text-xs text-muted-foreground">
        AI는 실수할 수 있어요. 중요한 내용은 근거 데이터를 확인해 주세요.
      </p>
    </div>
  )
}
