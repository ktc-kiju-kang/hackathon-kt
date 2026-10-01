'use client'

import { useEffect, useRef, useState } from 'react'
import { Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

type Message = { id: number; role: 'me' | 'bot'; text: string }

// 백엔드 연동 전 임시 화면: 메시지는 브라우저 상태에만 있고 새로고침하면 사라진다.
const INITIAL: Message[] = [{ id: 0, role: 'bot', text: '안녕하세요! 무엇을 도와드릴까요?' }]

export function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>(INITIAL)
  const [text, setText] = useState('')
  const nextId = useRef(1)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = listRef.current
    el?.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const send = (e: React.FormEvent) => {
    e.preventDefault()
    const value = text.trim()
    if (!value) return
    const mine = { id: nextId.current++, role: 'me' as const, text: value }
    const reply = { id: nextId.current++, role: 'bot' as const, text: `"${value}" 라고 하셨네요. (임시 응답)` }
    setMessages((prev) => [...prev, mine, reply])
    setText('')
  }

  return (
    // 3rem = AppShell 상단 헤더(h-12). 메시지는 페이지가 아니라 목록 안에서 스크롤된다.
    <div className="mx-auto flex h-[calc(100svh-3rem)] w-full max-w-3xl flex-col px-4 py-6">
      <h1 className="mb-4 text-2xl font-bold tracking-tight">채팅</h1>

      <div
        ref={listRef}
        role="log"
        aria-live="polite"
        aria-label="대화 내용"
        className="min-h-0 flex-1 space-y-3 overflow-y-auto rounded-lg border bg-card p-4"
      >
        {messages.map((m) => (
          <div key={m.id} className={cn('flex', m.role === 'me' ? 'justify-end' : 'justify-start')}>
            <p
              className={cn(
                'max-w-[80%] rounded-2xl px-4 py-2 text-sm',
                m.role === 'me' ? 'bg-primary text-primary-foreground' : 'bg-muted text-foreground',
              )}
            >
              {m.text}
            </p>
          </div>
        ))}
      </div>

      <form onSubmit={send} className="mt-4 flex gap-2">
        <Input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="메시지를 입력하세요"
          aria-label="메시지 입력"
        />
        <Button type="submit" size="icon" aria-label="전송">
          <Send />
        </Button>
      </form>
    </div>
  )
}
