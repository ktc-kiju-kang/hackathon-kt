'use client'

import { useCallback, useRef, useState } from 'react'
import { createConversation, sendMessage, type ChatEvent, type ChatMessage } from './api'

export type ToolActivity = {
  id: string
  name: string
  input: Record<string, unknown>
  result?: string
  isError?: boolean
}

/** 화면에 그릴 한 줄: 사용자 말풍선 / 에이전트 말풍선(텍스트 + 도구 실행 기록) */
export type ChatItem =
  | { kind: 'user'; text: string }
  | {
      kind: 'agent'
      text: string
      tools: ToolActivity[]
      streaming: boolean
      status?: string // 재시도 대기 등 진행 상태 (글자가 오면 지움)
      error?: string // 실패 사유 (말풍선 안에 표시)
      stopped?: boolean // 사용자가 중지함
    }

export function toItems(messages: ChatMessage[]): ChatItem[] {
  const items: ChatItem[] = []
  for (const m of messages) {
    if (m.role === 'user') items.push({ kind: 'user', text: m.content })
    else if (m.role === 'assistant') {
      const last = items.at(-1)
      const tools = m.tool_calls.map((c) => ({ id: c.id, name: c.name, input: c.input }))
      // 도구 왕복으로 나뉜 assistant 턴들은 말풍선 하나로 합친다
      if (last?.kind === 'agent') {
        last.text += m.content ? (last.text ? '\n\n' : '') + m.content : ''
        last.tools.push(...tools)
      } else items.push({ kind: 'agent', text: m.content, tools, streaming: false })
    } else {
      const last = items.at(-1)
      const t = last?.kind === 'agent' ? last.tools.find((x) => x.id === m.tool_call_id) : undefined
      if (t) Object.assign(t, { result: m.content, isError: m.is_error })
    }
  }
  return items
}

export function useChat() {
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [items, setItems] = useState<ChatItem[]>([])
  const [busy, setBusy] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const updateAgent = (fn: (a: Extract<ChatItem, { kind: 'agent' }>) => void) =>
    setItems((prev) => {
      const next = [...prev]
      const last = next.at(-1)
      if (last?.kind === 'agent') {
        const copy = { ...last, tools: [...last.tools] }
        fn(copy)
        next[next.length - 1] = copy
      }
      return next
    })

  const onEvent = useCallback((ev: ChatEvent) => {
    switch (ev.type) {
      case 'text':
        updateAgent((a) => {
          a.text += ev.data.text
          a.status = undefined
        })
        break
      case 'message':
        // 턴 경계: 스트리밍된 텍스트 뒤에 다음 턴 텍스트가 이어지도록 줄바꿈
        updateAgent((a) => void (a.text = a.text.trimEnd() + (ev.data.message.tool_calls.length ? '\n\n' : '')))
        break
      case 'tool_call':
        updateAgent((a) => void a.tools.push({ id: ev.data.id, name: ev.data.name, input: ev.data.input }))
        break
      case 'tool_result':
        updateAgent((a) => {
          const i = a.tools.findIndex((t) => t.id === ev.data.tool_call_id)
          if (i >= 0) a.tools[i] = { ...a.tools[i], result: ev.data.content, isError: ev.data.is_error }
        })
        break
      case 'retry': {
        const why = ev.data.code === 'rate_limit' ? '사용량 한도' : '일시 오류'
        updateAgent((a) => {
          a.status = `${why}로 ${Math.round(ev.data.wait_seconds)}초 뒤 다시 시도해요 (${ev.data.attempt}회)`
        })
        break
      }
      case 'error':
        updateAgent((a) => {
          a.error = ev.data.message
          a.status = undefined
        })
        break
    }
  }, [])

  const send = useCallback(
    async (text: string) => {
      if (!text.trim() || busy) return
      setBusy(true)
      setItems((prev) => [
        ...prev,
        { kind: 'user', text },
        { kind: 'agent', text: '', tools: [], streaming: true },
      ])
      abortRef.current = new AbortController()
      try {
        let id = conversationId
        if (!id) {
          id = (await createConversation()).id
          setConversationId(id)
        }
        await sendMessage(id, text, onEvent, abortRef.current.signal)
      } catch (e) {
        if ((e as Error).name === 'AbortError') {
          updateAgent((a) => {
            a.stopped = true
            a.status = undefined
          })
        } else {
          const message = (e as Error).message
          updateAgent((a) => void (a.error = message))
        }
      } finally {
        updateAgent((a) => void (a.streaming = false))
        setBusy(false)
      }
    },
    [busy, conversationId, onEvent],
  )

  const stop = () => abortRef.current?.abort()
  const reset = () => {
    stop()
    setConversationId(null)
    setItems([])
  }
  const load = (id: string, messages: ChatMessage[]) => {
    setConversationId(id)
    setItems(toItems(messages))
  }

  return { conversationId, items, busy, send, stop, reset, load }
}
