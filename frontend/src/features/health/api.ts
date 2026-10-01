// 계약: docs/contracts/health.md
import { isMock, request } from '@/lib/api-client'

export type Health = { status: 'ok' | 'mock'; time: string; version?: string | null }

export const getHealth = (): Promise<Health> =>
  isMock
    ? Promise.resolve({ status: 'mock', time: new Date().toISOString() })
    : request<Health>('/api/health')
