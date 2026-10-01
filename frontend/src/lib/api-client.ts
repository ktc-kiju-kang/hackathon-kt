// 공용 HTTP 클라이언트. 기능별 API 함수는 src/features/<feature>/api.ts 에 둔다.
// NEXT_PUBLIC_API_BASE_URL이 비어 있으면 mock 모드 (각 기능 api.ts가 mock 응답을 반환).
const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? ''

export const isMock = !BASE_URL

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}
