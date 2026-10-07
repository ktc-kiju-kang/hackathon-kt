import type { Metadata } from 'next'
import { TrendsDashboard } from '@/features/trends/TrendsDashboard'

export const metadata: Metadata = { title: 'AI 활용 트렌드 · KT Group' }

export default function TrendsPage() {
  return <TrendsDashboard />
}
