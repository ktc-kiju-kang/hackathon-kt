// API 계약은 docs/CONTRACTS.md 기준. 백엔드가 준비되기 전에는 mock으로 동작한다.
// VITE_API_BASE_URL이 비어 있으면 mock, 값이 있으면 실제 서버 호출.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export type Health = { status: 'ok' | 'mock'; time: string }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const api = {
  health: (): Promise<Health> =>
    BASE_URL
      ? request<Health>('/api/health')
      : Promise.resolve({ status: 'mock', time: new Date().toISOString() }),
}
