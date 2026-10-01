import type { Metadata } from 'next'
import { TrendsDashboard } from '@/features/trends/TrendsDashboard'

export const metadata: Metadata = { title: 'AI 활용 트렌드 · KT 해커톤' }

export default function TrendsPage() {
  return <TrendsDashboard />
}
