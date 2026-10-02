// 계약: docs/contracts/product.md (Opportunity·Evidence는 radar 계약)
import { apiUrl, isMock } from '@/lib/api-client'
import type { Evidence, Opportunity } from '@/features/radar/api'
import { postSse } from '@/lib/sse'

export type ProductCard = {
  id: string
  opportunity_id: string
  name: string
  tagline: string
  problem: string
  target_users: { persona: string; pain: string }[]
  value_props: string[]
  features: { name: string; description: string; priority: 'must' | 'should' | 'could' }[]
  user_flow: string[]
  data_needed: { name: string; source: string; availability: 'public' | 'internal' | 'to_collect' }[]
  apis: { method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'; path: string; description: string }[]
  architecture: {
    components: { id: string; name: string; role: string }[]
    edges: { from: string; to: string; label?: string | null }[]
  }
  mvp_scope: { in: string[]; out: string[] }
  poc_plan: {
    duration_weeks: number
    milestones: { week: number; goal: string }[]
    success_metrics: string[]
    risks: string[]
  }
  evidence: Evidence[]
}

export type ProductStage = 'design' | 'poc'

export type ProductEvent =
  | { type: 'stage'; data: { stage: ProductStage; status: 'start' | 'done'; summary?: string } }
  | { type: 'product'; data: { product: ProductCard } }
  | { type: 'retry'; data: { code: string; wait_seconds: number; attempt: number } }
  | { type: 'done'; data: { stop_reason: string; usage?: Record<string, number> } }
  | { type: 'error'; data: { message: string; code?: string } }

/** Product Card 생성을 요청하고 SSE 이벤트를 하나씩 onEvent로 넘긴다. */
export async function generateProduct(
  body: { opportunity: Opportunity; notes?: string },
  onEvent: (ev: ProductEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  if (isMock) return mockStream(body.opportunity, onEvent, signal)
  // 422·429 등은 서버 메시지(한국어)가 Error로 던져진다. done·error 없이 끊기면 연결 끊김 오류
  return postSse<ProductEvent>(apiUrl('/api/product/generate'), body, onEvent, { signal })
}

/** 발표·공유용 Markdown. 데이터 근거 출처를 함께 적는다. */
export function toMarkdown(card: ProductCard, opp: Opportunity | null): string {
  const list = (items: string[]) => items.map((i) => `- ${i}`).join('\n')
  const lines = [
    `# ${card.name}`,
    `> ${card.tagline}`,
    '',
    ...(opp ? [`**사업 기회**: ${opp.title}`, ''] : []),
    '## 문제',
    card.problem,
    '',
    '## 대상 사용자',
    list(card.target_users.map((u) => `**${u.persona}** — ${u.pain}`)),
    '',
    '## 가치',
    list(card.value_props),
    '',
    '## 핵심 기능',
    list(card.features.map((f) => `[${f.priority}] **${f.name}** — ${f.description}`)),
    '',
    '## 사용자 흐름',
    card.user_flow.map((s, i) => `${i + 1}. ${s}`).join('\n'),
    '',
    '## 필요한 데이터',
    list(card.data_needed.map((d) => `${d.name} (${d.source}, ${d.availability})`)),
    '',
    '## API',
    list(card.apis.map((a) => `\`${a.method} ${a.path}\` — ${a.description}`)),
    '',
    '## 아키텍처',
    list(card.architecture.components.map((c) => `**${c.name}** — ${c.role}`)),
    '',
    list(
      card.architecture.edges.map((e) => {
        const name = (id: string) => card.architecture.components.find((c) => c.id === id)?.name ?? id
        return `${name(e.from)} → ${name(e.to)}${e.label ? ` (${e.label})` : ''}`
      }),
    ),
    '',
    '## MVP 범위',
    `**포함**\n${list(card.mvp_scope.in)}`,
    '',
    `**제외**\n${list(card.mvp_scope.out)}`,
    '',
    `## PoC 계획 (${card.poc_plan.duration_weeks}주)`,
    list(card.poc_plan.milestones.map((m) => `${m.week}주차: ${m.goal}`)),
    '',
    `**성공 지표**\n${list(card.poc_plan.success_metrics)}`,
    '',
    `**위험**\n${list(card.poc_plan.risks)}`,
    '',
    '## 데이터 근거',
    card.evidence.length ? list(card.evidence.map((e) => e.label)) : '- (검증된 근거 없음)',
    '',
    '_Data: OpenAI Signals v2.0 (CC BY 4.0)_',
  ]
  return lines.join('\n')
}

// ---- 샘플 Opportunity: /radar를 거치지 않고 화면을 볼 때 ----

export const SAMPLE_OPPORTUNITY: Opportunity = {
  id: 'opp_sample',
  company_id: 'kt-cloud',
  country: 'KR',
  title: 'Cloud 장애 대응 자동화',
  trend: '업무 메시지 중 실무 가이드 요청이 늘고 기술 지원 질문은 줄었다',
  target: ['KT Cloud 운영 조직', '기업 Cloud 고객'],
  problem: '장애가 나면 운영자가 모니터링·로그·CMDB·런북을 각각 찾아보며 원인을 확인해야 한다.',
  solution: 'AI 에이전트가 이벤트·로그·런북을 함께 분석해 원인 후보와 조치 방법을 제안한다.',
  kt_assets: ['클라우드 운영 조직', '전국 데이터센터'],
  // 서버가 (metric, key, country)로 값을 다시 채운다
  evidence: [
    {
      metric: 'work_topic_share',
      key: 'Practical Guidance',
      country: 'KR',
      from: '',
      to: '',
      from_value: null,
      to_value: 0,
      change_pp: null,
      label: '',
    },
  ],
  rationale: '업무에서 즉시 쓸 수 있는 실무 안내 수요가 커져, 운영 현장의 즉답형 AI 도우미 수요로 이어진다.',
  score: { impact: 4, feasibility: 4 },
}

// ---- mock (백엔드 없이 화면 개발용, 계약 형태) ----

async function mockStream(opp: Opportunity, onEvent: (ev: ProductEvent) => void, signal?: AbortSignal) {
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
  onEvent({ type: 'stage', data: { stage: 'design', status: 'start' } })
  await wait(700)
  onEvent({ type: 'stage', data: { stage: 'design', status: 'done', summary: '[mock] 기능 3개' } })
  onEvent({ type: 'stage', data: { stage: 'poc', status: 'start' } })
  await wait(500)
  onEvent({ type: 'stage', data: { stage: 'poc', status: 'done', summary: '[mock] PoC 3주' } })
  onEvent({
    type: 'product',
    data: {
      product: {
        id: 'prd_mock',
        opportunity_id: opp.id,
        name: `[mock] ${opp.title} Agent`,
        tagline: `[mock] ${opp.solution}`,
        problem: opp.problem,
        target_users: opp.target.map((t) => ({ persona: t, pain: opp.problem })),
        value_props: ['[mock] 처리 시간 단축', '[mock] 운영 인력 절감'],
        features: [
          { name: '[mock] 데이터 수집', description: '관련 데이터를 모은다', priority: 'must' },
          { name: '[mock] AI 분석', description: '원인과 조치안을 제안한다', priority: 'must' },
          { name: '[mock] 리포트', description: '결과를 공유한다', priority: 'should' },
        ],
        user_flow: ['[mock] 요청 접수', '[mock] AI 분석', '[mock] 조치안 확인'],
        data_needed: [{ name: '[mock] 운영 로그', source: '내부 시스템', availability: 'internal' }],
        apis: [{ method: 'POST', path: '/analyze', description: '[mock] 분석 요청' }],
        architecture: {
          components: [
            { id: 'ui', name: '웹 화면', role: '요청·결과 표시' },
            { id: 'agent', name: 'AI 에이전트', role: '분석·추론' },
            { id: 'data', name: '데이터 저장소', role: '로그·문서' },
          ],
          edges: [
            { from: 'ui', to: 'agent', label: '요청' },
            { from: 'agent', to: 'data', label: '조회' },
          ],
        },
        mvp_scope: { in: ['[mock] 데이터 수집', '[mock] AI 분석'], out: ['[mock] 자동 조치'] },
        poc_plan: {
          duration_weeks: 3,
          milestones: [
            { week: 1, goal: '[mock] 데이터 연결' },
            { week: 2, goal: '[mock] AI 분석 프로토타입' },
            { week: 3, goal: '[mock] 현업 시연' },
          ],
          success_metrics: ['[mock] 분석 정확도 80%'],
          risks: ['[mock] 데이터 접근 권한'],
        },
        evidence: opp.evidence.filter((e) => e.label),
      },
    },
  })
  onEvent({ type: 'done', data: { stop_reason: 'end', usage: {} } })
}
