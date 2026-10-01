'use client'

import { useEffect, useRef, useState } from 'react'
import { LoaderCircleIcon, PlusIcon, SendIcon, SquareIcon, WrenchIcon } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { isMock } from '@/lib/api-client'
import { useChat, type ToolActivity } from './useChat'

const EXAMPLES = ['지금 서울은 몇 시야?', '1234 * 5678 / 9 계산해줘', '오늘 기준 100일 뒤는 무슨 요일이야?']

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
    <div className="mx-auto flex h-[calc(100svh-3rem)] w-full max-w-3xl flex-col gap-4 px-4 py-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold tracking-tight">AI 에이전트</h1>
          {isMock && <Badge variant="secondary">mock</Badge>}
        </div>
        <Button variant="outline" size="sm" onClick={reset} disabled={busy && items.length === 0}>
          <PlusIcon /> 새 대화
        </Button>
      </div>

      <div role="log" aria-live="polite" aria-label="대화 내용" className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
        {items.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-muted-foreground">
            <p>무엇이든 물어보세요. 필요하면 도구를 써서 답합니다.</p>
            <div className="flex flex-wrap justify-center gap-2">
              {EXAMPLES.map((q) => (
                <Button key={q} variant="secondary" size="sm" onClick={() => void send(q)}>
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
                <ToolCard key={t.id} tool={t} />
              ))}
              {(item.text || item.streaming) && (
                <div className="whitespace-pre-wrap rounded-2xl bg-muted px-4 py-2">
                  {item.text}
                  {item.streaming && <span className="ml-0.5 inline-block w-2 animate-pulse">▍</span>}
                </div>
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
          placeholder="메시지 입력 (Enter 전송, Shift+Enter 줄바꿈)"
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
    </div>
  )
}

function ToolCard({ tool }: { tool: ToolActivity }) {
  const pending = tool.result === undefined
  return (
    <Card size="sm" className={cn('gap-1 py-2', tool.isError && 'border-destructive')}>
      <CardContent className="space-y-1 px-3 text-xs">
        <div className="flex items-center gap-1.5 font-medium">
          {pending ? <LoaderCircleIcon className="size-3.5 animate-spin" /> : <WrenchIcon className="size-3.5" />}
          {tool.name}
          {tool.isError && <Badge variant="destructive">오류</Badge>}
        </div>
        <pre className="overflow-x-auto text-muted-foreground">{JSON.stringify(tool.input)}</pre>
        {!pending && <pre className="overflow-x-auto whitespace-pre-wrap">{tool.result}</pre>}
      </CardContent>
    </Card>
  )
}
