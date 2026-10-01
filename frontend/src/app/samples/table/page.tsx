import { TableSample } from '@/features/samples/TableSample'

export default function Page() {
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold tracking-tight">테이블</h1>
      <TableSample />
    </div>
  )
}
