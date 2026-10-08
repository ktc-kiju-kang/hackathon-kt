import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, request } from './api-client'

function reply(status: number, body?: unknown) {
  const init = { status, headers: { 'Content-Type': 'application/json' } }
  return new Response(body === undefined ? null : JSON.stringify(body), init)
}

afterEach(() => vi.unstubAllGlobals())

describe('request', () => {
  it('성공 응답은 JSON을 돌려준다', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => reply(200, { ok: 1 })))
    await expect(request('/x')).resolves.toEqual({ ok: 1 })
  })

  it('204는 본문 없이 끝난다', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => reply(204)))
    await expect(request('/x', { method: 'DELETE' })).resolves.toBeUndefined()
  })

  it('서버 detail 문자열을 오류 문구로 쓴다', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => reply(409, { detail: '이미 예약된 시간입니다' })))
    const err = await request('/x').catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err).toMatchObject({ status: 409, message: '이미 예약된 시간입니다' })
  })

  it('검증 오류 배열은 일반 문구로', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => reply(422, { detail: [{ msg: 'x' }] })))
    await expect(request('/x')).rejects.toMatchObject({ status: 422, message: '입력값을 확인해 주세요' })
  })

  it('JSON이 아닌 오류 본문도 처리한다', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('oops', { status: 502 })))
    await expect(request('/x')).rejects.toMatchObject({ status: 502 })
  })
})
