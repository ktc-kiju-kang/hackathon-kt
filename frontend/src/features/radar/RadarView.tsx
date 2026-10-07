'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  ArchiveIcon,
  ArrowRightIcon,
  CheckIcon,
  CircleIcon,
  LoaderCircleIcon,
  RadarIcon,
  SquareIcon,
} from 'lucide-react'
import { AiGeneratedLabel } from '@/components/ai-generated-label'
import { ErrorLine } from '@/components/error-line'
import { PageHeader } from '@/components/page-header'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import {
  type Company,
  type Opportunity,
  type RadarSnapshot,
  type SnapshotInfo,
  type Stage,
  formatSnapshotTime,
  getCompanies,
  getRadarSnapshot,
  loadRadarResult,
  saveRadarResult,
  saveSelectedOpportunity,
  streamOpportunities,
} from './api'
import { EvidenceSheet } from './EvidenceSheet'

const STAGES: { id: Stage; label: string; detail: string }[] = [
  { id: 'trend', label: '트렌드 분석', detail: 'Signals 데이터에서 관련 트렌드 추출' },
  { id: 'match', label: '사업 매칭', detail: '그룹사 사업·자산과 연결' },
  { id: 'opportunity', label: '기회 발굴', detail: '근거가 있는 사업 기회 생성' },
]

type StageState = { status: 'idle' | 'running' | 'done'; summary?: string }
const IDLE: Record<Stage, StageState> = {
  trend: { status: 'idle' },
  match: { status: 'idle' },
  opportunity: { status: 'idle' },
}

// 중지·오류 시 진행 중이던 단계의 스피너를 멈춘다
const halt = (s: Record<Stage, StageState>) =>
  Object.fromEntries(
    Object.entries(s).map(([k, v]) => [k, v.status === 'running' ? { status: 'idle', summary: '중단됨' } : v]),
  ) as Record<Stage, StageState>

export function RadarView() {
  const router = useRouter()
  const [companies, setCompanies] = useState<Company[] | null>(null)
  const [companyId, setCompanyId] = useState('kt-cloud')
  const [focus, setFocus] = useState('')
  const [running, setRunning] = useState(false)
  const [stages, setStages] = useState(IDLE)
  const [opps, setOpps] = useState<Opportunity[]>([])
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [snapshot, setSnapshot] = useState<RadarSnapshot | null>(null) // 고른 그룹사의 저장된 결과 (데모 예비안)
  const [saved, setSaved] = useState<SnapshotInfo | null>(null) // 지금 저장된 결과를 보여주는 중
  const abortRef = useRef<AbortController | null>(null)

  function loadCompanies() {
    setError(null)
    getCompanies()
      .then(setCompanies)
      .catch(() => setError('그룹사 목록을 불러오지 못했어요'))
  }

  useEffect(() => {
    getCompanies()
      .then(setCompanies)
      .catch(() => setError('그룹사 목록을 불러오지 못했어요'))
    // /product에 다녀왔으면 마지막 결과를 다시 보여 준다 (sessionStorage는 effect 안에서 비동기로)
    Promise.resolve()
      .then(loadRadarResult)
      .then((r) => {
        if (!r || r.opportunities.length === 0) return
        const summary = r.snapshot ? '저장된 결과' : '이전 결과'
        setCompanyId(r.company_id)
        setFocus(r.focus)
        setOpps(r.opportunities)
        setSaved(r.snapshot)
        setStages({
          trend: { status: 'done', summary },
          match: { status: 'done', summary },
          opportunity: { status: 'done', summary: `${summary} ${r.opportunities.length}건` },
        })
      })
    return () => abortRef.current?.abort()
  }, [])

  // 그룹사를 고를 때마다 저장된 결과가 있는지 미리 확인한다 (있으면 언제든 볼 수 있다)
  useEffect(() => {
    let cancelled = false
    getRadarSnapshot(companyId).then((snap) => {
      if (!cancelled) setSnapshot(snap && snap.opportunities.length > 0 ? snap : null)
    })
    return () => {
      cancelled = true
    }
  }, [companyId])

  const company = companies?.find((c) => c.id === companyId)
  const available = snapshot?.company_id === companyId ? snapshot : null

  async function run() {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setRunning(true)
    setStages(IDLE)
    setOpps([])
    setError(null)
    setNotice(null)
    setSaved(null)
    const request = { company_id: companyId, focus: focus.trim() }
    const found: Opportunity[] = []
    try {
      await streamOpportunities(
        { company_id: request.company_id, focus: request.focus || undefined },
        (ev) => {
          if (ev.type === 'stage') {
            const { stage, status, summary } = ev.data
            setStages((s) => ({ ...s, [stage]: { status: status === 'start' ? 'running' : 'done', summary } }))
            setNotice(null)
          } else if (ev.type === 'opportunity') {
            found.push(ev.data.opportunity)
            setOpps((o) => [...o, ev.data.opportunity])
          } else if (ev.type === 'retry') {
            setNotice(`AI 서버가 바빠서 ${ev.data.wait_seconds}초 뒤 다시 시도해요`)
          } else if (ev.type === 'error') {
            setError(ev.data.message)
            setStages(halt)
          }
        },
        controller.signal,
      )
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        setError((e as Error).message || '요청에 실패했어요')
        setStages(halt)
      }
    } finally {
      // 새 실행에 밀려난 실행은 저장하지 않는다. 화면을 떠나 끊긴 경우는 받은 기회까지 남긴다 (0건이면 복원 안 함)
      if (abortRef.current === controller) {
        setRunning(false)
        saveRadarResult({ ...request, opportunities: found, snapshot: null })
      }
    }
  }

  function showSaved(snap: RadarSnapshot) {
    const label = '저장된 결과'
    setStages({ trend: { status: 'done', summary: label }, match: { status: 'done', summary: label }, opportunity: { status: 'done', summary: `${label} ${snap.opportunities.length}건` } })
    setOpps(snap.opportunities)
    setSaved(snap.snapshot)
    setError(null)
    setNotice(null)
    saveRadarResult({ company_id: snap.company_id, focus: '', opportunities: snap.opportunities, snapshot: snap.snapshot })
  }

  function stop() {
    abortRef.current?.abort()
    setRunning(false)
    setStages(halt)
  }

  function design(opp: Opportunity) {
    saveSelectedOpportunity(opp)
    router.push('/product')
  }

  const started = running || stages.trend.status !== 'idle'

  return (
    <div className="mx-auto w-full max-w-6xl space-y-4 p-4 md:p-6">
      <PageHeader
        title="Opportunity Radar"
        description="그룹사를 고르면 AI 활용 트렌드 데이터와 사업을 연결해 새로운 AI 사업 기회를 찾아요"
      />

      <Card>
        <CardHeader>
          <CardTitle>1. 그룹사 선택</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-5">
            {companies
              ? companies.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    disabled={running}
                    onClick={() => setCompanyId(c.id)}
                    aria-pressed={c.id === companyId}
                    className={cn(
                      'rounded-lg border p-3 text-left transition-colors hover:bg-muted disabled:opacity-60',
                      c.id === companyId && 'border-primary bg-muted',
                    )}
                  >
                    <div className="font-medium">{c.name}</div>
                    <div className="line-clamp-2 text-xs text-muted-foreground">{c.business_areas.join(' · ')}</div>
                  </button>
                ))
              : Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-16" />)}
          </div>
          {company && <p className="text-sm text-muted-foreground">{company.summary}</p>}
          <div className="flex flex-col gap-2 sm:flex-row">
            <Input
              value={focus}
              onChange={(e) => setFocus(e.target.value.slice(0, 200))}
              placeholder="관심 방향 (선택) — 예: B2B 운영 자동화"
              disabled={running}
              aria-label="관심 방향"
            />
            {running ? (
              <Button variant="outline" onClick={stop}>
                <SquareIcon /> 중지
              </Button>
            ) : (
              <>
                <Button onClick={run} disabled={!company}>
                  <RadarIcon /> 기회 찾기
                </Button>
                {available && (
                  // 데모 예비안: 실시간 생성 대신 미리 만든 결과 (product 단계에서 막혔을 때도 여기로 돌아온다)
                  <Button variant="ghost" onClick={() => showSaved(available)}>
                    <ArchiveIcon /> 저장된 결과
                  </Button>
                )}
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {started && (
        <Card>
          <CardHeader>
            <CardTitle>2. 분석 단계</CardTitle>
            <CardDescription>근거 데이터: 대한민국 · 전 세계 OpenAI Signals (2024-07 → 2026-06)</CardDescription>
          </CardHeader>
          <CardContent>
            <ol className="grid gap-3 md:grid-cols-3">
              {STAGES.map((s) => {
                const st = stages[s.id]
                return (
                  <li key={s.id} className="flex gap-3">
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
        <ErrorLine message={error} onRetry={companies ? run : loadCompanies}>
          {companies && available && (
            <Button variant="ghost" size="sm" onClick={() => showSaved(available)}>
              <ArchiveIcon /> 저장된 결과 보기
            </Button>
          )}
        </ErrorLine>
      )}

      {saved && <SavedNotice info={saved} />}

      {(opps.length > 0 || stages.opportunity.status === 'running') && (
        <section className="space-y-3">
          <div className="space-y-1">
            <h2 className="text-xl font-semibold">3. 사업 기회</h2>
            <AiGeneratedLabel withNotice />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            {opps.map((o) => (
              <OpportunityCard
                key={o.id}
                opp={o}
                sources={companies?.find((c) => c.id === o.company_id)?.sources}
                onDesign={() => design(o)}
              />
            ))}
            {stages.opportunity.status === 'running' && <Skeleton className="h-72" />}
          </div>
        </section>
      )}
    </div>
  )
}

function SavedNotice({ info }: { info: SnapshotInfo }) {
  return (
    <p className="flex items-center gap-2 text-sm text-muted-foreground">
      <ArchiveIcon className="size-4 shrink-0" />
      실시간 생성이 아니라 {formatSnapshotTime(info.created_at)}에 {info.model}로 미리 만든 결과예요. AI가 만든 예시이고
      실제 사업 계획이 아니에요
    </p>
  )
}

function StageIcon({ status }: { status: StageState['status'] }) {
  if (status === 'running') return <LoaderCircleIcon className="mt-0.5 size-4 shrink-0 animate-spin" aria-label="진행 중" />
  if (status === 'done') return <CheckIcon className="mt-0.5 size-4 shrink-0 text-primary" aria-label="완료" />
  return <CircleIcon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-label="대기" />
}

function Score({ label, value }: { label: string; value: number }) {
  return (
    <span className="text-xs text-muted-foreground">
      {label} <span className="font-medium tabular-nums text-foreground">{value}</span>/5
    </span>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs font-medium text-muted-foreground">{label}</div>
      <div>{children}</div>
    </div>
  )
}

function OpportunityCard({
  opp,
  sources,
  onDesign,
}: {
  opp: Opportunity
  sources?: string[]
  onDesign: () => void
}) {
  return (
    <Card className="flex flex-col">
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base">{opp.title}</CardTitle>
          <div className="flex shrink-0 gap-3">
            <Score label="임팩트" value={opp.score.impact} />
            <Score label="실현성" value={opp.score.feasibility} />
          </div>
        </div>
        <p className="text-xs text-muted-foreground">대상 · {opp.target.join(' · ')}</p>
      </CardHeader>
      <CardContent className="flex-1 space-y-3 text-sm">
        <Field label="문제">{opp.problem}</Field>
        <Field label="해결">{opp.solution}</Field>
        {opp.kt_assets.length > 0 && <Field label="활용 자산">{opp.kt_assets.join(' · ')}</Field>}
        <Field label="AI 추론">
          <span className="text-muted-foreground">{opp.rationale}</span>
        </Field>
      </CardContent>
      <CardFooter className="justify-between gap-2">
        {opp.evidence.length > 0 ? (
          <EvidenceSheet evidence={opp.evidence} sources={sources} title={opp.title} />
        ) : (
          <span />
        )}
        <Button variant="outline" onClick={onDesign}>
          프로덕트 설계 <ArrowRightIcon />
        </Button>
      </CardFooter>
    </Card>
  )
}
