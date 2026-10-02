'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import {
  ArchiveIcon,
  ArrowRightIcon,
  ChartColumnIcon,
  CheckIcon,
  CircleAlertIcon,
  CircleIcon,
  CopyIcon,
  DownloadIcon,
  LoaderCircleIcon,
  SparklesIcon,
  SquareIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { type Opportunity, type SnapshotInfo, formatSnapshotTime, loadSelectedOpportunity } from '@/features/radar/api'
import {
  type ProductCard,
  type ProductSnapshot,
  type ProductStage,
  SAMPLE_OPPORTUNITY,
  generateProduct,
  getProductSnapshot,
  toMarkdown,
} from './api'

const STAGES: { id: ProductStage; label: string; detail: string }[] = [
  { id: 'design', label: '프로덕트 설계', detail: '문제·사용자·기능·아키텍처' },
  { id: 'poc', label: 'PoC 계획', detail: 'MVP 범위·마일스톤·성공 지표' },
]

type StageState = { status: 'idle' | 'running' | 'done'; summary?: string }
const IDLE: Record<ProductStage, StageState> = { design: { status: 'idle' }, poc: { status: 'idle' } }
const halt = (s: Record<ProductStage, StageState>) =>
  Object.fromEntries(
    Object.entries(s).map(([k, v]) => [k, v.status === 'running' ? { status: 'idle', summary: '중단됨' } : v]),
  ) as Record<ProductStage, StageState>

const PRIORITY_LABEL = { must: '필수', should: '권장', could: '선택' } as const
const AVAILABILITY_LABEL = { public: '공개', internal: '내부', to_collect: '수집 필요' } as const

export function ProductView() {
  const [opp, setOpp] = useState<Opportunity | null | undefined>(undefined) // undefined = 아직 읽는 중
  const [notes, setNotes] = useState('')
  const [running, setRunning] = useState(false)
  const [stages, setStages] = useState(IDLE)
  const [card, setCard] = useState<ProductCard | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [fallback, setFallback] = useState<ProductSnapshot | null>(null) // 실패 시 보여줄 수 있는 저장된 결과
  const [saved, setSaved] = useState<SnapshotInfo | null>(null) // 지금 저장된 결과를 보여주는 중
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    // sessionStorage는 브라우저에서만 읽을 수 있다 (effect 안에서 비동기로 반영)
    Promise.resolve()
      .then(loadSelectedOpportunity)
      .then(setOpp)
    return () => abortRef.current?.abort()
  }, [])

  async function run() {
    if (!opp) return
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setRunning(true)
    setStages(IDLE)
    setCard(null)
    setError(null)
    setNotice(null)
    setFallback(null)
    setSaved(null)
    try {
      await generateProduct(
        { opportunity: opp, notes: notes.trim() || undefined },
        (ev) => {
          if (ev.type === 'stage') {
            const { stage, status, summary } = ev.data
            setStages((s) => ({ ...s, [stage]: { status: status === 'start' ? 'running' : 'done', summary } }))
            setNotice(null)
          } else if (ev.type === 'product') {
            setCard(ev.data.product)
          } else if (ev.type === 'retry') {
            setNotice(`AI 서버가 바빠서 ${ev.data.wait_seconds}초 뒤 다시 시도합니다`)
          } else if (ev.type === 'error') {
            setError(ev.data.message)
            setStages(halt)
            offerFallback(opp.id, controller)
          }
        },
        controller.signal,
      )
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        setError((e as Error).message || '요청에 실패했습니다')
        setStages(halt)
        offerFallback(opp.id, controller)
      }
    } finally {
      if (abortRef.current === controller) setRunning(false)
    }
  }

  // 실시간 생성이 실패하면 저장된 결과가 있는지 확인한다 (radar 저장된 결과의 기회일 때 있다)
  function offerFallback(id: string, controller: AbortController) {
    getProductSnapshot(id).then((snap) => {
      // 그 사이 새로 실행했으면 이전 실행의 예비안은 버린다
      if (abortRef.current === controller && snap) setFallback(snap)
    })
  }

  function showSaved(snap: ProductSnapshot) {
    setStages({ design: { status: 'done', summary: '저장된 결과' }, poc: { status: 'done', summary: '저장된 결과' } })
    setCard(snap.product)
    setSaved(snap.snapshot)
    setError(null)
    setFallback(null)
  }

  function stop() {
    abortRef.current?.abort()
    setRunning(false)
    setStages(halt)
  }

  function copyMarkdown() {
    if (!card) return
    if (!navigator.clipboard) {
      toast.error('이 브라우저에서는 복사할 수 없습니다. .md로 내려받으세요')
      return
    }
    navigator.clipboard
      .writeText(toMarkdown(card, opp ?? null))
      .then(() => toast.success('Markdown을 복사했습니다'))
      .catch(() => toast.error('복사하지 못했습니다'))
  }

  function downloadMarkdown() {
    if (!card) return
    const url = URL.createObjectURL(new Blob([toMarkdown(card, opp ?? null)], { type: 'text/markdown' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `${card.name.replace(/[\\/:*?"<>|\n\r]/g, '_').trim() || 'product'}.md`
    document.body.append(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 0) // 바로 해제하면 일부 브라우저에서 다운로드가 취소된다
  }

  const started = running || stages.design.status !== 'idle'

  return (
    <div className="mx-auto w-full max-w-6xl space-y-4 p-4 md:p-6">
      <div>
        <h1 className="text-xl font-semibold">Product Generator</h1>
        <p className="text-sm text-muted-foreground">
          고른 사업 기회를 실제 프로덕트 설계와 PoC 계획으로 바꿉니다
        </p>
      </div>

      {opp === undefined ? (
        <Skeleton className="h-40" />
      ) : opp === null ? (
        <Card>
          <CardHeader>
            <CardTitle>선택한 사업 기회가 없습니다</CardTitle>
            <CardDescription>Opportunity Radar에서 기회를 고르거나, 샘플로 먼저 볼 수 있습니다</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Button asChild>
              <Link href="/radar">
                Opportunity Radar로 <ArrowRightIcon />
              </Link>
            </Button>
            <Button variant="outline" onClick={() => setOpp(SAMPLE_OPPORTUNITY)}>
              샘플로 보기 (Cloud 장애 대응 자동화)
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardDescription>사업 기회</CardDescription>
            <CardTitle>{opp.title}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <div className="text-xs font-medium text-muted-foreground">문제</div>
                <p>{opp.problem}</p>
              </div>
              <div>
                <div className="text-xs font-medium text-muted-foreground">해결</div>
                <p>{opp.solution}</p>
              </div>
            </div>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value.slice(0, 500))}
              placeholder="추가 요구사항 (선택) — 예: 3주 안에 PoC 가능해야 함"
              disabled={running}
              aria-label="추가 요구사항"
              rows={2}
            />
            <div className="flex justify-end gap-2">
              {running ? (
                <Button variant="outline" onClick={stop}>
                  <SquareIcon /> 중지
                </Button>
              ) : (
                <Button onClick={run}>
                  <SparklesIcon /> {card ? '다시 설계' : '프로덕트 설계'}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {started && (
        <Card>
          <CardContent>
            <ol className="grid gap-3 md:grid-cols-2">
              {STAGES.map((s) => {
                const st = stages[s.id]
                return (
                  <li key={s.id} className="flex gap-3 rounded-lg border p-3">
                    <StageIcon status={st.status} />
                    <div className="min-w-0 space-y-1">
                      <div className="text-sm font-medium">{s.label}</div>
                      <div className="text-xs text-muted-foreground">{st.summary ?? s.detail}</div>
                    </div>
                  </li>
                )
              })}
            </ol>
            {notice && <p className="mt-3 text-sm text-muted-foreground">{notice}</p>}
          </CardContent>
        </Card>
      )}

      {error && (
        <Card className="border-destructive/50">
          <CardContent className="flex items-center gap-2 text-sm text-destructive">
            <CircleAlertIcon className="size-4 shrink-0" /> {error}
            {fallback && fallback.product.opportunity_id === opp?.id && (
              <Button variant="outline" size="sm" className="ml-auto" onClick={() => showSaved(fallback)}>
                <ArchiveIcon /> 저장된 결과 보기
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {saved && (
        <Card className="border-dashed">
          <CardContent className="flex items-center gap-2 text-sm text-muted-foreground">
            <ArchiveIcon className="size-4 shrink-0" />
            실시간 생성이 아니라 {formatSnapshotTime(saved.created_at)}에 {saved.model}로 미리 만든 결과입니다. AI가 만든 예시이며 실제 사업 계획이 아닙니다
          </CardContent>
        </Card>
      )}

      {running && !card && <Skeleton className="h-96" />}
      {card && <ProductCardView card={card} onCopy={copyMarkdown} onDownload={downloadMarkdown} />}
    </div>
  )
}

function StageIcon({ status }: { status: StageState['status'] }) {
  if (status === 'running') return <LoaderCircleIcon className="mt-0.5 size-4 shrink-0 animate-spin" aria-label="진행 중" />
  if (status === 'done') return <CheckIcon className="mt-0.5 size-4 shrink-0 text-primary" aria-label="완료" />
  return <CircleIcon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-label="대기" />
}

function Section({ title, children, className }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent className="text-sm">{children}</CardContent>
    </Card>
  )
}

function Bullets({ items }: { items: string[] }) {
  return (
    <ul className="list-disc space-y-1 pl-5">
      {items.map((item, i) => (
        <li key={`${i}-${item}`}>{item}</li>
      ))}
    </ul>
  )
}

function ProductCardView({ card, onCopy, onDownload }: { card: ProductCard; onCopy: () => void; onDownload: () => void }) {
  const name = (id: string) => card.architecture.components.find((c) => c.id === id)?.name ?? id
  return (
    <section className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-3">
          <div className="space-y-1.5">
            <CardDescription>Product</CardDescription>
            <CardTitle className="text-2xl">{card.name}</CardTitle>
            <p className="text-sm text-muted-foreground">{card.tagline}</p>
          </div>
          <div className="flex shrink-0 gap-2">
            <Button variant="outline" size="sm" onClick={onCopy}>
              <CopyIcon /> 복사
            </Button>
            <Button variant="outline" size="sm" onClick={onDownload}>
              <DownloadIcon /> .md
            </Button>
          </div>
        </CardHeader>
        <CardContent className="text-sm">
          <div className="text-xs font-medium text-muted-foreground">문제</div>
          <p>{card.problem}</p>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Section title="대상 사용자">
          <ul className="space-y-2">
            {card.target_users.map((u, i) => (
              <li key={`${i}-${u.persona}`}>
                <span className="font-medium">{u.persona}</span>
                <span className="text-muted-foreground"> — {u.pain}</span>
              </li>
            ))}
          </ul>
        </Section>
        <Section title="가치">
          <Bullets items={card.value_props} />
        </Section>

        <Section title="핵심 기능">
          <ul className="space-y-2">
            {card.features.map((f, i) => (
              <li key={`${i}-${f.name}`} className="flex gap-2">
                <Badge variant={f.priority === 'must' ? 'default' : 'secondary'} className="shrink-0">
                  {PRIORITY_LABEL[f.priority]}
                </Badge>
                <span>
                  <span className="font-medium">{f.name}</span>
                  <span className="text-muted-foreground"> — {f.description}</span>
                </span>
              </li>
            ))}
          </ul>
        </Section>
        <Section title="사용자 흐름">
          <ol className="space-y-1">
            {card.user_flow.map((s, i) => (
              <li key={`${i}-${s}`} className="flex gap-2">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-muted text-xs tabular-nums">
                  {i + 1}
                </span>
                <span>{s}</span>
              </li>
            ))}
          </ol>
        </Section>

        <Section title="아키텍처">
          <div className="flex flex-wrap gap-2">
            {card.architecture.components.map((c, i) => (
              <div key={`${i}-${c.id}`} className="rounded-md border px-3 py-2">
                <div className="font-medium">{c.name}</div>
                <div className="text-xs text-muted-foreground">{c.role}</div>
              </div>
            ))}
          </div>
          {card.architecture.edges.length > 0 && (
            <ul className="mt-3 space-y-1 text-xs text-muted-foreground">
              {card.architecture.edges.map((e, i) => (
                <li key={`${e.from}-${e.to}-${i}`} className="flex items-center gap-1">
                  {name(e.from)} <ArrowRightIcon className="size-3" /> {name(e.to)}
                  {e.label && <span>({e.label})</span>}
                </li>
              ))}
            </ul>
          )}
        </Section>
        <Section title="필요한 데이터 · API">
          <ul className="space-y-1">
            {card.data_needed.map((d, i) => (
              <li key={`${i}-${d.name}`} className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{d.name}</span>
                <span className="text-muted-foreground">{d.source}</span>
                <Badge variant="outline">{AVAILABILITY_LABEL[d.availability]}</Badge>
              </li>
            ))}
          </ul>
          <ul className="mt-3 space-y-1">
            {card.apis.map((a, i) => (
              <li key={`${i}-${a.method} ${a.path}`}>
                <code className="rounded bg-muted px-1 py-0.5 text-xs">
                  {a.method} {a.path}
                </code>
                <span className="text-muted-foreground"> {a.description}</span>
              </li>
            ))}
          </ul>
        </Section>

        <Section title="MVP 범위">
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <div className="mb-1 text-xs font-medium text-muted-foreground">포함</div>
              <Bullets items={card.mvp_scope.in} />
            </div>
            <div>
              <div className="mb-1 text-xs font-medium text-muted-foreground">이번에는 제외</div>
              <Bullets items={card.mvp_scope.out} />
            </div>
          </div>
        </Section>
        <Section title={`PoC 계획 · ${card.poc_plan.duration_weeks}주`}>
          <ol className="space-y-1">
            {card.poc_plan.milestones.map((m, i) => (
              <li key={`${i}-${m.week}`}>
                <span className="font-medium tabular-nums">{m.week}주차</span> {m.goal}
              </li>
            ))}
          </ol>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div>
              <div className="mb-1 text-xs font-medium text-muted-foreground">성공 지표</div>
              <Bullets items={card.poc_plan.success_metrics} />
            </div>
            <div>
              <div className="mb-1 text-xs font-medium text-muted-foreground">위험</div>
              <Bullets items={card.poc_plan.risks} />
            </div>
          </div>
        </Section>
      </div>

      <Card>
        <CardContent className="space-y-1">
          <div className="flex items-center gap-1 text-xs font-medium">
            <ChartColumnIcon className="size-3.5" /> 데이터 근거 (서버가 OpenAI Signals로 다시 검증한 값)
          </div>
          {card.evidence.length ? (
            <ul className="space-y-0.5 text-xs text-muted-foreground">
              {card.evidence.map((e) => (
                <li key={`${e.metric}-${e.key}-${e.country}`}>{e.label}</li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-muted-foreground">검증된 근거가 없습니다</p>
          )}
          <p className="pt-1 text-xs text-muted-foreground">Data: OpenAI Signals v2.0 (CC BY 4.0)</p>
        </CardContent>
      </Card>
    </section>
  )
}
