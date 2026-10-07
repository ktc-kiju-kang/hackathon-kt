import type { Metadata } from 'next'
import { RadarView } from '@/features/radar/RadarView'

export const metadata: Metadata = { title: 'Opportunity Radar · KT Group' }

export default function RadarPage() {
  return <RadarView />
}
