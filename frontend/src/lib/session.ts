// 탭 안에서만 유지되는 값 저장: sessionStorage, 못 쓰면(시크릿 모드 등) 탭 메모리.
// 브라우저에서만 동작하므로 effect·이벤트 핸들러 안에서 부른다.
const memoryStore = new Map<string, string>()

export function saveSession(key: string, value: unknown): void {
  const raw = JSON.stringify(value)
  memoryStore.set(key, raw)
  try {
    sessionStorage.setItem(key, raw)
  } catch {
    // 메모리 값만 쓴다
  }
}

export function loadSession<T>(key: string): T | null {
  let raw: string | null | undefined
  try {
    raw = sessionStorage.getItem(key)
  } catch {
    // 무시하고 메모리 값
  }
  raw ??= memoryStore.get(key)
  if (!raw) return null
  try {
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}
