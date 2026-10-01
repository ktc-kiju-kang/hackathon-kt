import type { AskDoExpress, Topic } from './api'

export const TOPIC_LABEL: Record<Topic, string> = {
  Writing: '글쓰기',
  'Practical Guidance': '실무 가이드',
  'Seeking information': '정보 탐색',
  'Technical help': '기술 지원',
  Multimedia: '멀티미디어',
  'Self-expression': '자기 표현',
  'Other/Unknown': '기타',
}

export const INTENT_LABEL: Record<AskDoExpress, string> = {
  asking: '질문',
  doing: '작업 요청',
  expressing: '표현',
}

const regionNames = new Intl.DisplayNames(['ko'], { type: 'region' })

export function countryLabel(code: string | null): string {
  if (!code) return '전 세계'
  try {
    return regionNames.of(code) ?? code
  } catch {
    return code
  }
}

export const pct = (share: number) => `${(share * 100).toFixed(1)}%`
export const signedPp = (pp: number) => `${pp > 0 ? '+' : ''}${pp.toFixed(1)}%p`
