'use client'

import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'

// 에이전트 답변 Markdown. HTML은 렌더링하지 않는다(react-markdown 기본값) — LLM 출력이라 안전하게.
const components: Components = {
  p: (props) => <p className="leading-relaxed [&:not(:first-child)]:mt-2" {...props} />,
  ul: (props) => <ul className="mt-2 list-disc space-y-1 pl-5" {...props} />,
  ol: (props) => <ol className="mt-2 list-decimal space-y-1 pl-5" {...props} />,
  h1: (props) => <h3 className="mt-3 font-semibold" {...props} />,
  h2: (props) => <h3 className="mt-3 font-semibold" {...props} />,
  h3: (props) => <h3 className="mt-3 font-semibold" {...props} />,
  strong: (props) => <strong className="font-semibold" {...props} />,
  a: (props) => <a className="underline" target="_blank" rel="noreferrer" {...props} />,
  code: (props) => <code className="rounded bg-background px-1 py-0.5 font-mono text-[0.9em]" {...props} />,
  pre: (props) => <pre className="mt-2 overflow-x-auto rounded-md bg-background p-3 text-xs [&_code]:p-0" {...props} />,
  blockquote: (props) => <blockquote className="mt-2 border-l-2 border-border pl-3 text-muted-foreground" {...props} />,
  table: (props) => (
    <div className="mt-2 overflow-x-auto">
      <table className="w-full border-collapse text-sm" {...props} />
    </div>
  ),
  th: (props) => <th className="border-b border-border px-2 py-1 text-left font-medium" {...props} />,
  td: (props) => <td className="border-b border-border px-2 py-1 align-top" {...props} />,
}

export function Markdown({ children }: { children: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
      {children}
    </ReactMarkdown>
  )
}
