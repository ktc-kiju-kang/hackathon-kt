// 계약: docs/contracts/chat.md
import { apiUrl, isMock, request } from '@/lib/api-client'
import { postSse } from '@/lib/sse'

export type ToolCall = { id: string; name: string; input: Record<string, unknown> }

export type ChatMessage = {
  role: 'user' | 'assistant' | 'tool'
  content: string
  tool_calls: ToolCall[]
  tool_call_id: string | null
  is_error: boolean
  created_at?: string
}

export type Conversation = { id: string; title: string | null; created_at: string }

export type ChatEvent =
  | { type: 'text'; data: { text: string } }
  | { type: 'tool_call'; data: ToolCall }
  | { type: 'tool_result'; data: { tool_call_id: string; content: string; is_error: boolean } }
  | { type: 'message'; data: { message: ChatMessage } }
  | { type: 'done'; data: { stop_reason: string; usage?: Record<string, number> } }
  | { type: 'retry'; data: { code: string; wait_seconds: number; attempt: number } }
  | { type: 'error'; data: { message: string; code?: string } }

// 로그인 없는 소유권: 브라우저별 임의 ID (docs/contracts/chat.md)
let memoryClientId: string | null = null // localStorage를 못 쓰면 탭 단위 임의 ID

function clientId(): string {
  const KEY = 'kt-hackathon-client-id'
  try {
    let id = localStorage.getItem(KEY)
    if (!id) {
      id = crypto.randomUUID()
      localStorage.setItem(KEY, id)
    }
    return id
  } catch {
    memoryClientId ??= crypto.randomUUID()
    return memoryClientId
  }
}

const headers = () => ({ 'X-Client-Id': clientId() })

export async function createConversation(): Promise<Conversation> {
  if (isMock) return { id: crypto.randomUUID(), title: null, created_at: new Date().toISOString() }
  return request('/api/chat/conversations', { method: 'POST', body: '{}', headers: headers() })
}

export async function listConversations(): Promise<Conversation[]> {
  if (isMock) return []
  return request('/api/chat/conversations', { headers: headers() })
}

export async function listMessages(id: string): Promise<ChatMessage[]> {
  if (isMock) return []
  return request(`/api/chat/conversations/${id}/messages`, { headers: headers() })
}

/** 메시지를 보내고 SSE 이벤트를 하나씩 onEvent로 넘긴다. */
export async function sendMessage(
  id: string,
  content: string,
  onEvent: (ev: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  if (isMock) return mockStream(content, onEvent)
  // 429(사용량 한도)·409(대화 길이) 등은 서버 메시지가 Error로 던져진다
  return postSse<ChatEvent>(apiUrl(`/api/chat/conversations/${id}/messages`), { content }, onEvent, {
    headers: headers(),
    signal,
  })
}

/** 마지막 답변을 지우고 다시 생성한다 (SSE). */
export async function regenerate(
  id: string,
  onEvent: (ev: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  if (isMock) return mockStream('(재생성)', onEvent)
  return postSse<ChatEvent>(apiUrl(`/api/chat/conversations/${id}/regenerate`), {}, onEvent, {
    headers: headers(),
    signal,
  })
}

async function mockStream(content: string, onEvent: (ev: ChatEvent) => void) {
  const text = `[mock] 백엔드 연결 없이 동작 중입니다. 받은 메시지: ${content}`
  for (const word of text.split(' ')) {
    await new Promise((r) => setTimeout(r, 40))
    onEvent({ type: 'text', data: { text: word + ' ' } })
  }
  onEvent({
    type: 'message',
    data: {
      message: { role: 'assistant', content: text, tool_calls: [], tool_call_id: null, is_error: false },
    },
  })
  onEvent({ type: 'done', data: { stop_reason: 'end_turn' } })
}
