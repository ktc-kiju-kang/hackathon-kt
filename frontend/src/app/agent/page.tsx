import type { Metadata } from 'next'
import { ChatView } from '@/features/chat/ChatView'

export const metadata: Metadata = { title: 'AI 에이전트' }

export default function AgentPage() {
  return <ChatView />
}
