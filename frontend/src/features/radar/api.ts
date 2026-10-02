// 계약: docs/contracts/radar.md (Evidence는 docs/contracts/trends.md)
import { apiUrl, isMock, request } from '@/lib/api-client'

export type Company = {
  id: string
  name: string
  name_en: string
  summary: string
  business_areas: string[]
  customers: string[]
  assets: string[]
  sources: string[]
}

export type Evidence = {
  metric: 'topic_share' | 'work_topic_share' | 'work_share' | 'work_intent' | 'usage_rank'
  key: string | null
  country: string | null
  from: string
  to: string
  from_value: number | null
  to_value: number
  change_pp: number | null
  label: string
}

export type Opportunity = {
  id: string
  company_id: string
  country: string
  title: string
  trend: string
  target: string[]
  problem: string
  solution: string
  kt_assets: string[]
  evidence: Evidence[]
  rationale: string
  score: { impact: number; feasibility: number }
}

export type OpportunityRequest = { company_id: string; country?: string; focus?: string; count?: number }

export type Stage = 'trend' | 'match' | 'opportunity'

export type RadarEvent =
  | { type: 'stage'; data: { stage: Stage; status: 'start' | 'done'; summary?: string } }
  | { type: 'opportunity'; data: { opportunity: Opportunity } }
  | { type: 'retry'; data: { code: string; wait_seconds: number; attempt: number } }
  | { type: 'done'; data: { stop_reason: string; usage?: Record<string, number> } }
  | { type: 'error'; data: { message: string; code?: string } }

export const getCompanies = (): Promise<Company[]> =>
  isMock ? Promise.resolve(MOCK_COMPANIES) : request<Company[]>('/api/radar/companies')

/** Opportunity 생성을 요청하고 SSE 이벤트를 하나씩 onEvent로 넘긴다. */
export async function streamOpportunities(
  body: OpportunityRequest,
  onEvent: (ev: RadarEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  if (isMock) return mockStream(body, onEvent, signal)
  const res = await fetch(apiUrl('/api/radar/opportunities'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok || !res.body) {
    // 404·429 등은 서버 메시지(한국어)를 그대로 보여준다
    const detail = await res.json().then((b) => b?.detail, () => null)
    throw new Error(typeof detail === 'string' ? detail : `${res.status} ${res.statusText}`)
  }

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader()
  let buf = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buf += value
    let sep: number
    while ((sep = buf.indexOf('\n\n')) >= 0) {
      const chunk = buf.slice(0, sep)
      buf = buf.slice(sep + 2)
      const event = /^event: (.+)$/m.exec(chunk)?.[1]
      const data = /^data: (.+)$/m.exec(chunk)?.[1]
      if (event && data) onEvent({ type: event, data: JSON.parse(data) } as RadarEvent)
    }
  }
}

// ---- 화면 간 전달: /radar에서 고른 Opportunity를 /product가 읽는다 (계약 radar.md) ----

const SELECTED_KEY = 'radar:selected-opportunity'
let memorySelected: Opportunity | null = null // sessionStorage를 못 쓰면 탭 메모리

export function saveSelectedOpportunity(opp: Opportunity): void {
  memorySelected = opp
  try {
    sessionStorage.setItem(SELECTED_KEY, JSON.stringify(opp))
  } catch {
    // 시크릿 모드 등: 메모리 값만 쓴다
  }
}

export function loadSelectedOpportunity(): Opportunity | null {
  try {
    const raw = sessionStorage.getItem(SELECTED_KEY)
    if (raw) return JSON.parse(raw) as Opportunity
  } catch {
    // 무시하고 메모리 값
  }
  return memorySelected
}

// ---- mock (백엔드 없이 화면 개발용, 계약 형태) ----

const MOCK_COMPANIES: Company[] = [
  {
    id: 'kt-cloud',
    name: 'KT Cloud',
    name_en: 'kt cloud',
    summary: '[mock] KT 그룹의 클라우드·데이터센터 사업자.',
    business_areas: ['퍼블릭 클라우드', '데이터센터(IDC)', 'AI 인프라(GPU 클라우드)'],
    customers: ['공공기관', '엔터프라이즈'],
    assets: ['전국 데이터센터', '클라우드 운영 조직'],
    sources: ['https://www.ktcloud.com/'],
  },
  {
    id: 'kt',
    name: 'KT',
    name_en: 'KT Corporation',
    summary: '[mock] 국내 대표 유무선 통신사.',
    business_areas: ['유무선 통신(모바일·인터넷)', 'AI 컨택센터(AICC)'],
    customers: ['개인 통신 가입자', '기업'],
    assets: ['전국 유무선 통신망', '대규모 고객센터 운영 경험'],
    sources: ['https://corp.kt.com/'],
  },
]

const MOCK_EVIDENCE: Evidence = {
  metric: 'topic_share',
  key: 'Practical Guidance',
  country: 'KR',
  from: '2024-07',
  to: '2026-06',
  from_value: 0.232,
  to_value: 0.341,
  change_pp: 10.9,
  label: 'KR 메시지 중 Practical Guidance 23.2% → 34.1% (2024-07 → 2026-06)',
}

async function mockStream(body: OpportunityRequest, onEvent: (ev: RadarEvent) => void, signal?: AbortSignal) {
  const wait = (ms: number) =>
    new Promise<void>((resolve, reject) => {
      const t = setTimeout(resolve, ms)
      signal?.addEventListener('abort', () => {
        clearTimeout(t)
        reject(new DOMException('aborted', 'AbortError'))
      })
    })
  const company = MOCK_COMPANIES.find((c) => c.id === body.company_id) ?? MOCK_COMPANIES[0]
  const stages: [Stage, string][] = [
    ['trend', '[mock] 실무 가이드 증가 · 기술 지원 감소'],
    ['match', `[mock] 2건 연결: ${company.business_areas.slice(0, 2).join(', ')}`],
  ]
  for (const [stage, summary] of stages) {
    onEvent({ type: 'stage', data: { stage, status: 'start' } })
    await wait(600)
    onEvent({ type: 'stage', data: { stage, status: 'done', summary } })
  }
  onEvent({ type: 'stage', data: { stage: 'opportunity', status: 'start' } })
  const count = body.count ?? 4
  for (let n = 0; n < count; n++) {
    await wait(400)
    onEvent({
      type: 'opportunity',
      data: {
        opportunity: {
          id: `opp_mock${n}`,
          company_id: company.id,
          country: body.country ?? 'KR',
          title: `[mock] ${company.business_areas[n % company.business_areas.length]} AI 에이전트`,
          trend: MOCK_EVIDENCE.label,
          target: company.customers,
          problem: '[mock] 반복 업무와 문의 대응에 많은 인력이 든다.',
          solution: '[mock] AI 에이전트가 데이터를 분석해 답변·조치안을 제안한다.',
          kt_assets: company.assets.slice(0, 1),
          evidence: [MOCK_EVIDENCE],
          rationale: '[mock] 실무 가이드 요청이 늘어난 만큼 업무 현장의 즉답형 AI 수요가 커진다.',
          score: { impact: 4 - (n % 2), feasibility: 3 + (n % 2) },
        },
      },
    })
  }
  onEvent({ type: 'stage', data: { stage: 'opportunity', status: 'done', summary: `[mock] 기회 ${count}건` } })
  onEvent({ type: 'done', data: { stop_reason: 'end' } })
}
