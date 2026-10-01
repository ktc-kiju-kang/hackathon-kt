import type { Metadata } from 'next'
import { ChatView } from '@/features/agent/ChatView'

export const metadata: Metadata = { title: 'AI 에이전트 · KT 해커톤' }

export default function AgentPage() {
  return <ChatView />
}
