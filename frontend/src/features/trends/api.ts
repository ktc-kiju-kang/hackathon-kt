// 계약: docs/contracts/trends.md
import { isMock, request } from '@/lib/api-client'

export const TOPICS = [
  'Writing',
  'Practical Guidance',
  'Seeking information',
  'Technical help',
  'Multimedia',
  'Self-expression',
  'Other/Unknown',
] as const
export type Topic = (typeof TOPICS)[number]
export type AskDoExpress = 'asking' | 'doing' | 'expressing'
export type Month = string // "YYYY-MM"
export type Dimension = 'topic' | 'work_related' | 'ask_do_express'

export type TrendsMeta = {
  months: { from: Month; to: Month }
  countries: string[]
  topics: Topic[]
  source: { name: string; license: string; url: string }
}

export type TrendSeries = {
  dimension: Dimension
  country: string | null
  work_related: 0 | 1 | null
  points: { month: Month; key: string; share: number }[]
}

export type TopicChange = { topic: Topic; from_share: number; to_share: number; change_pp: number }

export type TrendSummary = {
  country: string | null
  period: { from: Month; to: Month }
  topics: TopicChange[]
  work_topics: TopicChange[]
  work_share: { from: number; to: number; change_pp: number }
  work_intent: { intent: AskDoExpress; from_share: number; to_share: number; change_pp: number }[]
  usage_rank: {
    quarter: Month
    rank: number
    previous_quarter: Month | null
    previous_rank: number | null
  } | null
}

export type SeriesQuery = {
  dimension: Dimension
  country?: string | null
  work_related?: 0 | 1
  from?: Month
  to?: Month
}

const qs = (params: Record<string, string | number | null | undefined>) => {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== null && v !== undefined) q.set(k, String(v))
  return q.toString()
}

export const getMeta = (): Promise<TrendsMeta> =>
  isMock ? Promise.resolve(mockMeta()) : request<TrendsMeta>('/api/trends/meta')

export const getSeries = (query: SeriesQuery): Promise<TrendSeries> =>
  isMock ? Promise.resolve(mockSeries(query)) : request<TrendSeries>(`/api/trends/series?${qs(query)}`)

export const getSummary = (country: string | null, months = 12): Promise<TrendSummary> =>
  isMock
    ? Promise.resolve(mockSummary(country, months))
    : request<TrendSummary>(`/api/trends/summary?${qs({ country, months })}`)

// ---- mock (계약 형태의 가짜 데이터: 백엔드 없이 화면 개발용) ----

const MONTHS: Month[] = Array.from({ length: 24 }, (_, i) => {
  const d = new Date(Date.UTC(2024, 6 + i, 1))
  return d.toISOString().slice(0, 7)
})

const mockMeta = (): TrendsMeta => ({
  months: { from: MONTHS[0], to: MONTHS[MONTHS.length - 1] },
  countries: ['JP', 'KR', 'US'],
  topics: [...TOPICS],
  source: { name: 'OpenAI Signals v2.0', license: 'CC BY 4.0', url: 'https://openai.com/signals/data-download/' },
})

// 시작값 → 끝값을 선형으로 잇고 key별로 정규화한다
const MOCK_SHARES: Record<Dimension, Record<string, [number, number]>> = {
  topic: {
    Writing: [0.34, 0.21],
    'Practical Guidance': [0.23, 0.34],
    'Seeking information': [0.15, 0.19],
    'Technical help': [0.17, 0.04],
    Multimedia: [0.03, 0.05],
    'Self-expression': [0.04, 0.1],
    'Other/Unknown': [0.03, 0.06],
  },
  work_related: { '0': [0.45, 0.68], '1': [0.55, 0.32] },
  ask_do_express: { asking: [0.47, 0.37], doing: [0.43, 0.37], expressing: [0.1, 0.26] },
}

function mockSeries(query: SeriesQuery): TrendSeries {
  const shares = MOCK_SHARES[query.dimension]
  const scale = query.country ? 1 : 0.9 // 전 세계는 조금 다르게
  const months = MONTHS.filter((m) => (!query.from || m >= query.from) && (!query.to || m <= query.to))
  const points = months.flatMap((month) => {
    const t = MONTHS.indexOf(month) / (MONTHS.length - 1)
    const raw = Object.entries(shares).map(([key, [a, b]]) => [key, a + (b - a) * t * scale] as const)
    const total = raw.reduce((s, [, v]) => s + v, 0)
    return raw
      .map(([key, v]) => ({ month, key, share: Math.round((v / total) * 1000) / 1000 }))
      .sort((x, y) => x.key.localeCompare(y.key))
  })
  return { dimension: query.dimension, country: query.country ?? null, work_related: query.work_related ?? null, points }
}

function mockSummary(country: string | null, months: number): TrendSummary {
  const from = MONTHS[MONTHS.length - 1 - months]
  const to = MONTHS[MONTHS.length - 1]
  const at = (dimension: Dimension) => {
    const s = mockSeries({ dimension, country, from, to }).points
    return (month: Month, key: string) => s.find((p) => p.month === month && p.key === key)?.share ?? 0
  }
  const pp = (a: number, b: number) => Math.round((b - a) * 1000) / 10
  const topic = at('topic')
  const topics = TOPICS.map((t) => ({ topic: t, from_share: topic(from, t), to_share: topic(to, t) }))
    .map((r) => ({ ...r, change_pp: pp(r.from_share, r.to_share) }))
    .sort((a, b) => b.change_pp - a.change_pp)
  const work = at('work_related')
  const intent = at('ask_do_express')
  return {
    country,
    period: { from, to },
    topics,
    work_topics: topics,
    work_share: { from: work(from, '1'), to: work(to, '1'), change_pp: pp(work(from, '1'), work(to, '1')) },
    work_intent: (['asking', 'doing', 'expressing'] as const)
      .map((i) => ({ intent: i, from_share: intent(from, i), to_share: intent(to, i), change_pp: pp(intent(from, i), intent(to, i)) }))
      .sort((a, b) => b.change_pp - a.change_pp),
    usage_rank: country ? { quarter: '2026-04', rank: 25, previous_quarter: '2025-01', previous_rank: 57 } : null,
  }
}
