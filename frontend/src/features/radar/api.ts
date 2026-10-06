// 계약: docs/contracts/radar.md (Evidence는 docs/contracts/trends.md)
import { apiUrl, isMock, request } from '@/lib/api-client'
import { postSse } from '@/lib/sse'

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
  | { type: 'done'; data: { stop_reason: string; usage?: Record<string, number>; cached?: boolean } }
  | { type: 'error'; data: { message: string; code?: string } }

// 데모 예비안: 미리 실제 LLM으로 만든 결과 (계약 radar.md "snapshot"). LLM·한도를 쓰지 않는다
export type SnapshotInfo = { created_at: string; model: string }
export type RadarSnapshot = { company_id: string; country: string; snapshot: SnapshotInfo; opportunities: Opportunity[] }

/** 저장된 결과. 없거나(404) 불러오지 못하면 null — 예비안이라 실패해도 화면을 막지 않는다. */
export const getRadarSnapshot = (companyId: string): Promise<RadarSnapshot | null> =>
  isMock
    ? Promise.resolve(null)
    : request<RadarSnapshot>(`/api/radar/snapshot/${encodeURIComponent(companyId)}`).catch(() => null)

/** 화면 표시용: "2026. 10. 2. 오후 3:12" */
export const formatSnapshotTime = (iso: string) =>
  new Date(iso).toLocaleString('ko-KR', { dateStyle: 'medium', timeStyle: 'short' })

export const getCompanies = (): Promise<Company[]> =>
  isMock ? Promise.resolve(MOCK_COMPANIES) : request<Company[]>('/api/radar/companies')

/** Opportunity 생성을 요청하고 SSE 이벤트를 하나씩 onEvent로 넘긴다. */
export async function streamOpportunities(
  body: OpportunityRequest,
  onEvent: (ev: RadarEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  if (isMock) return mockStream(body, onEvent, signal)
  // 404·429 등은 서버 메시지(한국어)가 Error로 던져진다. done·error 없이 끊기면 연결 끊김 오류
  return postSse<RadarEvent>(apiUrl('/api/radar/opportunities'), body, onEvent, { signal })
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

const mockCompany = (id: string, name: string, areas: string[], customers: string[], assets: string[]): Company => ({
  id,
  name,
  name_en: name,
  summary: `[mock] ${name} 공개 자료 요약`,
  business_areas: areas,
  customers,
  assets,
  sources: [],
})

// 계약: 고정 5개
const MOCK_COMPANIES: Company[] = [
  mockCompany('kt', 'KT', ['유무선 통신(모바일·인터넷)', 'AI 컨택센터(AICC)'], ['개인 통신 가입자', '기업'], ['전국 유무선 통신망']),
  mockCompany('kt-cloud', 'KT Cloud', ['퍼블릭 클라우드', '데이터센터(IDC)'], ['공공기관', '엔터프라이즈'], ['전국 데이터센터']),
  mockCompany('kt-ds', 'KT DS', ['IT 시스템 구축·운영(SI/SM)', '클라우드 전환·운영(MSP)'], ['KT 그룹사'], ['대규모 IT 운영 인력']),
  mockCompany('bccard', 'BC카드', ['카드 결제 처리(프로세싱)', '가맹점 네트워크'], ['가맹점·소상공인'], ['전국 가맹점 네트워크']),
  mockCompany('kt-skylife', 'KT Skylife', ['위성 유료방송', '방송 채널·콘텐츠'], ['유료방송 가입자'], ['전국 위성방송망']),
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
      signal?.addEventListener(
        'abort',
        () => {
          clearTimeout(t)
          reject(new DOMException('aborted', 'AbortError'))
        },
        { once: true },
      )
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
  onEvent({ type: 'done', data: { stop_reason: 'end', usage: {} } })
}
