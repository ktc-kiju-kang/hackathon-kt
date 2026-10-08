// 계약: docs/contracts/health.md
import { isMock, request } from '@/lib/api-client'

export type Health = {
  status: 'ok' | 'mock'
  time: string
  version?: string | null
  db?: 'ok' | 'error' | 'unconfigured'
  llm?: string | null
  client_ip?: string | null
  uptime_seconds?: number
}

export const getHealth = (): Promise<Health> =>
  isMock
    ? Promise.resolve({ status: 'mock', time: new Date().toISOString(), uptime_seconds: 0 })
    : request<Health>('/api/health')
