import { EditorSample } from '@/features/samples/EditorSample'

export default function Page() {
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold tracking-tight">텍스트 에디터</h1>
      <EditorSample />
    </div>
  )
}
