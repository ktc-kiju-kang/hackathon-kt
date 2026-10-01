'use client'

import { useRef, useState } from 'react'
import { Bold, Eye, Italic, List, ListOrdered, Pencil, Save, Trash2, Underline } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'

const DRAFT_KEY = 'samples:editor:draft'
const MAX_LENGTH = 2000

const TOOLS = [
  { cmd: 'bold', label: '굵게', icon: Bold },
  { cmd: 'italic', label: '기울임', icon: Italic },
  { cmd: 'underline', label: '밑줄', icon: Underline },
  { cmd: 'insertUnorderedList', label: '글머리 목록', icon: List },
  { cmd: 'insertOrderedList', label: '번호 목록', icon: ListOrdered },
] as const

type Draft = { title: string; html: string; savedAt: string }

const ALLOWED_TAGS = new Set(['B', 'I', 'U', 'STRONG', 'EM', 'UL', 'OL', 'LI', 'BR', 'DIV', 'P', 'SPAN'])

// localStorage 등 신뢰할 수 없는 HTML은 허용 태그만 남기고 속성을 모두 제거한다.
// DOMParser 문서는 비활성이라 파싱 중 스크립트 실행·리소스 로드가 일어나지 않는다.
function sanitize(html: string): string {
  const doc = new DOMParser().parseFromString(html, 'text/html')
  const walk = (parent: Node) => {
    Array.from(parent.childNodes).forEach((node) => {
      if (node.nodeType !== Node.ELEMENT_NODE) return
      const el = node as Element
      if (!ALLOWED_TAGS.has(el.tagName)) {
        el.replaceWith(doc.createTextNode(el.textContent ?? ''))
        return
      }
      Array.from(el.attributes).forEach((a) => el.removeAttribute(a.name))
      walk(el)
    })
  }
  walk(doc.body)
  return doc.body.innerHTML
}

export function EditorSample() {
  const editorRef = useRef<HTMLDivElement>(null)
  const [title, setTitle] = useState('')
  const [html, setHtml] = useState('')
  const [length, setLength] = useState(0)
  const [mode, setMode] = useState<'edit' | 'preview'>('edit')
  const [savedAt, setSavedAt] = useState<string | null>(null)

  const sync = () => {
    const el = editorRef.current
    if (!el) return
    setHtml(el.innerHTML)
    // 다 지워도 남는 <br>·개행은 글자 수에서 제외
    setLength(el.innerText.trim().length)
  }

  const format = (cmd: string) => {
    editorRef.current?.focus()
    document.execCommand(cmd)
    sync()
  }

  // 붙여넣기는 서식 없이 텍스트만 받는다 (외부 HTML 유입 방지)
  const onPaste = (e: React.ClipboardEvent) => {
    e.preventDefault()
    document.execCommand('insertText', false, e.clipboardData.getData('text/plain'))
    sync()
  }

  const save = () => {
    const draft: Draft = { title, html, savedAt: new Date().toLocaleTimeString('ko-KR') }
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(draft))
      setSavedAt(draft.savedAt)
      toast.success('임시저장했습니다')
    } catch {
      toast.error('이 브라우저에서는 저장할 수 없습니다')
    }
  }

  const load = () => {
    try {
      const raw = localStorage.getItem(DRAFT_KEY)
      if (!raw) return toast.info('저장된 글이 없습니다')
      const draft = JSON.parse(raw) as Partial<Draft>
      if (typeof draft.title !== 'string' || typeof draft.html !== 'string') throw new Error('invalid draft')
      setTitle(draft.title)
      if (editorRef.current) editorRef.current.innerHTML = sanitize(draft.html)
      sync()
      setSavedAt(typeof draft.savedAt === 'string' ? draft.savedAt : null)
      toast.success('불러왔습니다')
    } catch {
      toast.error('저장된 글을 읽지 못했습니다')
    }
  }

  const clear = () => {
    setTitle('')
    if (editorRef.current) editorRef.current.innerHTML = ''
    sync()
  }

  const over = length > MAX_LENGTH

  return (
    <Card>
      <CardHeader>
        <CardTitle>글 작성</CardTitle>
        <CardDescription>서식 툴바, 글자 수 제한, 임시저장(브라우저 저장), 미리보기를 갖춘 에디터 샘플</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="제목" aria-label="제목" />

        <div className="flex flex-wrap items-center gap-1">
          {TOOLS.map(({ cmd, label, icon: Icon }) => (
            <Button
              key={cmd}
              type="button"
              variant="outline"
              size="icon"
              aria-label={label}
              title={label}
              disabled={mode === 'preview'}
              // mousedown 기본동작을 막아야 에디터 선택 영역이 유지된다
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => format(cmd)}
            >
              <Icon />
            </Button>
          ))}
          <Separator orientation="vertical" className="mx-1 h-6" />
          <Button type="button" variant={mode === 'edit' ? 'secondary' : 'ghost'} size="sm" aria-pressed={mode === 'edit'} onClick={() => setMode('edit')}>
            <Pencil /> 편집
          </Button>
          <Button type="button" variant={mode === 'preview' ? 'secondary' : 'ghost'} size="sm" aria-pressed={mode === 'preview'} onClick={() => setMode('preview')}>
            <Eye /> 미리보기
          </Button>
        </div>

        {/* 편집기는 항상 마운트해 두고 숨긴다 (미리보기 전환 시 내용 유지) */}
        <div
          ref={editorRef}
          contentEditable
          suppressContentEditableWarning
          role="textbox"
          aria-multiline
          aria-label="본문"
          onInput={sync}
          onPaste={onPaste}
          onDrop={(e) => e.preventDefault()}
          className={
            mode === 'edit'
              ? 'min-h-64 rounded-lg border bg-background p-4 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring [&_ol]:list-decimal [&_ol]:pl-5 [&_ul]:list-disc [&_ul]:pl-5'
              : 'hidden'
          }
        />
        {mode === 'preview' && (
          <div className="min-h-64 rounded-lg border bg-muted/30 p-4 text-sm [&_ol]:list-decimal [&_ol]:pl-5 [&_ul]:list-disc [&_ul]:pl-5">
            <h2 className="mb-3 text-xl font-semibold">{title || '(제목 없음)'}</h2>
            {length === 0 ? (
              <p className="text-muted-foreground">내용이 없습니다.</p>
            ) : (
              <div dangerouslySetInnerHTML={{ __html: sanitize(html) }} />
            )}
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Badge variant={over ? 'destructive' : 'secondary'}>
              {length.toLocaleString()} / {MAX_LENGTH.toLocaleString()}자
            </Badge>
            {savedAt && <span>마지막 저장 {savedAt}</span>}
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="ghost" onClick={clear}>
              <Trash2 /> 비우기
            </Button>
            <Button type="button" variant="outline" onClick={load}>
              불러오기
            </Button>
            <Button type="button" onClick={save} disabled={over}>
              <Save /> 임시저장
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
