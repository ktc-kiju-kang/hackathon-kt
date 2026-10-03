import { afterEach, describe, expect, it, vi } from 'vitest'
import { parseSseFrame, postSse, type SseEvent } from '@/lib/sse'

const enc = new TextEncoder()

function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(enc.encode(chunk))
      controller.close()
    },
  })
}

type FetchCall = { url: string; init: RequestInit & { headers: Record<string, string> } }

/** fetch 를 가짜로 바꾸고, 마지막 호출 인자를 돌려주는 함수를 반환한다. */
function mockFetch(res: unknown): () => FetchCall {
  let last: FetchCall | undefined
  vi.stubGlobal('fetch', async (url: string, init: FetchCall['init']) => {
    last = { url, init }
    return res
  })
  return () => {
    if (!last) throw new Error('fetch 가 호출되지 않았다')
    return last
  }
}

const ok = (chunks: string[]) => ({ ok: true, body: streamOf(chunks) })

afterEach(() => vi.unstubAllGlobals())

describe('parseSseFrame', () => {
  it('event 와 data 를 해석한다', () => {
    expect(parseSseFrame('event: stage\ndata: {"a":1}')).toEqual({ type: 'stage', data: { a: 1 } })
  })

  it('ping 주석·빈 프레임·data 없는 프레임은 null', () => {
    expect(parseSseFrame(': ping')).toBeNull()
    expect(parseSseFrame('')).toBeNull()
    expect(parseSseFrame('event: x')).toBeNull()
  })

  it('data 줄이 여러 개면 \\n 으로 이어 붙인다 (옛 정규식은 첫 줄만 읽었다)', () => {
    expect(parseSseFrame('event: t\ndata: {"a":\ndata: 1}')).toEqual({ type: 't', data: { a: 1 } })
  })

  it('콜론 뒤 공백이 없어도 해석한다', () => {
    expect(parseSseFrame('event:t\ndata:{"a":1}')).toEqual({ type: 't', data: { a: 1 } })
  })

  it('잘못된 JSON 은 던진다', () => {
    expect(() => parseSseFrame('event: t\ndata: {nope')).toThrow()
  })
})

describe('postSse', () => {
  it('이벤트 중간에서 청크가 잘려도 순서대로 전달하고 ping 은 무시한다', async () => {
    const lastCall = mockFetch(
      ok([': ping\n\nevent: stage\nda', 'ta: {"n":1}\n\nevent: done\ndata: {"stop_reason":"end"}', '\n\n']),
    )
    const got: SseEvent[] = []
    await postSse('http://x/api', { q: 1 }, (e) => got.push(e))

    expect(got).toEqual([
      { type: 'stage', data: { n: 1 } },
      { type: 'done', data: { stop_reason: 'end' } },
    ])
    const { init } = lastCall()
    expect(init.method).toBe('POST')
    expect(init.body).toBe('{"q":1}')
    expect(init.headers['Content-Type']).toBe('application/json')
  })

  it('추가 헤더(X-Client-Id)를 Content-Type 과 함께 전달한다', async () => {
    const lastCall = mockFetch(ok(['event: done\ndata: {}\n\n']))
    await postSse('http://x', {}, () => {}, { headers: { 'X-Client-Id': 'abc' } })

    expect(lastCall().init.headers['X-Client-Id']).toBe('abc')
    expect(lastCall().init.headers['Content-Type']).toBe('application/json')
  })

  it('error 이벤트도 정상 종료로 보고 이벤트는 전달한다', async () => {
    mockFetch(ok(['event: error\ndata: {"message":"m"}\n\n']))
    const got: SseEvent[] = []
    await postSse('http://x', {}, (e) => got.push(e))
    expect(got[0].type).toBe('error')
  })

  it('done·error 없이 끝나면 연결 끊김 오류를 던진다 (끊기기 전 이벤트는 전달)', async () => {
    mockFetch(ok(['event: stage\ndata: {"n":1}\n\n']))
    const got: SseEvent[] = []
    await expect(postSse('http://x', {}, (e) => got.push(e))).rejects.toThrow('서버 연결이 끊겼습니다')
    expect(got).toHaveLength(1)
  })

  it('스트림 시작 전 오류는 서버 detail 문구로 던진다', async () => {
    mockFetch({ ok: false, status: 429, statusText: 'Too Many', body: null, json: async () => ({ detail: '요청이 너무 많아요' }) })
    await expect(postSse('http://x', {}, () => {})).rejects.toThrow('요청이 너무 많아요')
  })

  it('detail 이 없으면 상태 코드 문구로 던진다', async () => {
    mockFetch({
      ok: false,
      status: 500,
      statusText: 'Server Error',
      body: null,
      json: async () => {
        throw new Error('JSON 아님')
      },
    })
    await expect(postSse('http://x', {}, () => {})).rejects.toThrow('500 Server Error')
  })

  it('이벤트 data 가 JSON 이 아니면 postSse 도 그 오류를 그대로 던진다', async () => {
    mockFetch(ok(['event: stage\ndata: {nope\n\n']))
    await expect(postSse('http://x', {}, () => {})).rejects.toThrow()
  })

  it('응답은 ok 인데 body 가 없으면 상태 코드 문구로 던진다', async () => {
    mockFetch({
      ok: true,
      status: 204,
      statusText: 'No Content',
      body: null,
      json: async () => {
        throw new Error('body 없음')
      },
    })
    await expect(postSse('http://x', {}, () => {})).rejects.toThrow('204 No Content')
  })

  it('signal 을 fetch 에 전달한다 (취소는 호출자가 AbortError 로 구분)', async () => {
    const lastCall = mockFetch(ok(['event: done\ndata: {}\n\n']))
    const controller = new AbortController()
    await postSse('http://x', {}, () => {}, { signal: controller.signal })
    expect(lastCall().init.signal).toBe(controller.signal)
  })
})
