import type { Metadata } from 'next'
import { ProductView } from '@/features/product/ProductView'

export const metadata: Metadata = { title: 'Product Generator · KT 해커톤' }

export default function ProductPage() {
  return <ProductView />
}
