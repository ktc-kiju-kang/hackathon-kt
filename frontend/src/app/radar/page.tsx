import type { Metadata } from 'next'
import { RadarView } from '@/features/radar/RadarView'

export const metadata: Metadata = { title: 'Opportunity Radar · KT 해커톤' }

export default function RadarPage() {
  return <RadarView />
}
