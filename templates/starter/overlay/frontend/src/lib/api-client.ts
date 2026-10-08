// 공용 HTTP 클라이언트. 기능별 API 함수는 src/features/<feature>/api.ts 에 둔다.
// NEXT_PUBLIC_API_BASE_URL이 비어 있으면 mock 모드 (각 기능 api.ts가 mock 응답을 반환).
const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? ''

export const isMock = !BASE_URL

export const apiUrl = (path: string) => `${BASE_URL}${path}`

/** 서버 오류. message는 화면에 보여 줄 문구 (FastAPI `detail` 문자열이 있으면 그것). */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly detail?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

// FastAPI 오류 본문: {"detail": "문구"} 또는 검증 오류 {"detail": [{loc, msg, ...}]}
function errorMessage(status: number, detail: unknown): string {
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail)) return '입력값을 확인해 주세요'
  if (status >= 500) return '서버 오류가 났어요. 잠시 후 다시 시도해 주세요'
  return `요청에 실패했어요 (${status})`
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!res.ok) {
    const body: unknown = await res.json().catch(() => null)
    const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : undefined
    throw new ApiError(res.status, errorMessage(res.status, detail), detail)
  }
  if (res.status === 204 || res.headers.get('content-length') === '0') return undefined as T
  return res.json() as Promise<T>
}
