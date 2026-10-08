// 공용 SSE 클라이언트. 기능별 api.ts는 URL·이벤트 타입·mock만 갖고, 스트림 읽기·파싱은 여기서 한다.
// 서버 형식: `event: <type>\ndata: <json>\n\n`, 15초마다 `: ping` 주석 (계약: docs/contracts/chat.md)

export type SseEvent = { type: string; data: unknown }

/** 이벤트 한 덩어리(빈 줄로 구분된 줄들)를 해석한다. 이벤트가 아니면(`: ping` 등) null. */
export function parseSseFrame(frame: string): SseEvent | null {
  let type: string | undefined
  const data: string[] = []
  for (const line of frame.split('\n')) {
    if (!line || line.startsWith(':')) continue // 빈 줄·주석(ping)
    const i = line.indexOf(':')
    const field = i < 0 ? line : line.slice(0, i)
    // 값 앞의 공백 하나는 구분자다 (SSE 표준)
    const value = i < 0 ? '' : line.slice(i + 1).replace(/^ /, '')
    if (field === 'event') type = value
    else if (field === 'data') data.push(value) // data 줄이 여러 개면 \n으로 이어 붙인다
  }
  if (!type || data.length === 0) return null
  return { type, data: JSON.parse(data.join('\n')) }
}

/**
 * POST로 요청하고 SSE 이벤트를 하나씩 onEvent로 넘긴다.
 *
 * - 응답이 실패(4xx·5xx)면 서버가 준 `detail`(한국어 메시지)로 Error를 던진다. 스트림 시작 전 오류(404·422·429)가 여기에 해당한다.
 * - `done`·`error` 이벤트 없이 스트림이 끝나면 연결이 끊긴 것으로 보고 Error를 던진다.
 * - 취소는 `signal`(AbortController)로 한다. 취소되면 AbortError가 던져지므로 호출자가 구분한다.
 */
export async function postSse<E extends SseEvent>(
  url: string,
  body: unknown,
  onEvent: (ev: E) => void,
  opts: { headers?: Record<string, string>; signal?: AbortSignal } = {},
): Promise<void> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    body: JSON.stringify(body),
    signal: opts.signal,
  })
  if (!res.ok || !res.body) {
    // 404·409·422·429 등은 서버 메시지를 그대로 보여준다
    const detail = await res.json().then((b) => b?.detail, () => null)
    throw new Error(typeof detail === 'string' ? detail : `${res.status} ${res.statusText}`)
  }

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader()
  let buf = ''
  let finished = false
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buf += value
    let sep: number
    while ((sep = buf.indexOf('\n\n')) >= 0) {
      const frame = buf.slice(0, sep)
      buf = buf.slice(sep + 2)
      const ev = parseSseFrame(frame)
      if (!ev) continue
      if (ev.type === 'done' || ev.type === 'error') finished = true
      onEvent(ev as E)
    }
  }
  if (!finished) throw new Error('서버 연결이 끊겼습니다. 다시 시도해 주세요.')
}
