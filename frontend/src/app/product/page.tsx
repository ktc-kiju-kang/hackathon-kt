import type { Metadata } from 'next'
import { ProductView } from '@/features/product/ProductView'

export const metadata: Metadata = { title: 'Product Generator · KT Group' }

export default function ProductPage() {
  return <ProductView />
}
