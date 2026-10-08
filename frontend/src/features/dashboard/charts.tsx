'use client'

import { CheckCircle2Icon, CircleDashedIcon, CircleDotIcon, LoaderCircleIcon, XCircleIcon } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'

// 색은 세 가지만: 통과·성공·검증됨 = teal(--chart-1, 진행 중은 옅은 teal), 실패 = 빨강(--destructive, 오류에만),
// 나머지 = KDS 회색.
// 색만으로 구분하지 않게 아이콘·글자를 함께 둔다 (색각 이상·흑백 인쇄).
export type Tone = 'good' | 'partial' | 'bad' | 'rest'

const FILL: Record<Tone, string> = {
  good: 'bg-[var(--chart-1)]',
  partial: 'bg-[var(--chart-1)]/40', // 같은 teal의 옅은 단계 — 진행 중(구현됨-미검증)
  bad: 'bg-destructive',
  rest: 'bg-[var(--data-visual-default-gray)]',
}

export function ToneIcon({ tone, running, className }: { tone: Tone; running?: boolean; className?: string }) {
  const cls = cn('size-4 shrink-0', className)
  if (running) return <LoaderCircleIcon className={cn(cls, 'animate-spin text-muted-foreground')} aria-label="진행 중" />
  if (tone === 'good') return <CheckCircle2Icon className={cn(cls, 'text-[var(--chart-1)]')} aria-label="정상" />
  if (tone === 'partial') return <CircleDotIcon className={cn(cls, 'text-[var(--chart-1)]')} aria-label="진행 중" />
  if (tone === 'bad') return <XCircleIcon className={cn(cls, 'text-destructive')} aria-label="실패" />
  return <CircleDashedIcon className={cn(cls, 'text-muted-foreground')} aria-label="기타" />
}

/** 지표 카드 하나: 제목 · 큰 숫자 · 보조 글 · 아래 그래픽(막대 등). */
export function StatTile({
  label,
  value,
  sub,
  tone,
  children,
}: {
  label: string
  value: React.ReactNode
  sub?: React.ReactNode
  tone?: Tone
  children?: React.ReactNode
}) {
  return (
    <Card className="gap-0 py-5">
      <CardContent className="space-y-3 px-5">
        <div className="flex items-center gap-1.5 text-[13px] text-muted-foreground">
          {tone && <ToneIcon tone={tone} />}
          {label}
        </div>
        <div className="text-[28px] leading-none font-semibold tabular-nums">{value}</div>
        {sub && <div className="text-[13px] text-muted-foreground">{sub}</div>}
        {children}
      </CardContent>
    </Card>
  )
}

export type Segment = { key: string; label: string; value: number; tone: Tone }

/** 가로 누적 막대: 조각 사이 2px 틈, 양 끝 둥글게, 조각마다 마우스를 올리면 개수. */
export function Meter({ segments, height = 8, label }: { segments: Segment[]; height?: number; label: string }) {
  const total = segments.reduce((s, x) => s + x.value, 0)
  if (total === 0) {
    return <div className={cn('w-full rounded-full', FILL.rest)} style={{ height }} role="img" aria-label={`${label}: 없음`} />
  }
  return (
    <div className="flex w-full gap-0.5" style={{ height }} role="img" aria-label={`${label}: ${segments.map((s) => `${s.label} ${s.value}`).join(', ')}`}>
      {segments
        .filter((s) => s.value > 0)
        .map((s) => (
          <Tooltip key={s.key}>
            <TooltipTrigger asChild>
              <div
                className={cn('h-full min-w-1 first:rounded-l-full last:rounded-r-full', FILL[s.tone])}
                style={{ flexGrow: s.value, flexBasis: 0 }}
              />
            </TooltipTrigger>
            <TooltipContent>
              {s.label} {s.value}개 ({Math.round((s.value / total) * 100)}%)
            </TooltipContent>
          </Tooltip>
        ))}
    </div>
  )
}

/** 범례: 색 점 + 이름 + 개수 (글자는 글자색, 색은 점에만). */
export function Legend({ segments }: { segments: Segment[] }) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-[13px] text-muted-foreground">
      {segments.map((s) => (
        <li key={s.key} className="flex items-center gap-1.5">
          <span className={cn('inline-block size-2 rounded-full', FILL[s.tone])} aria-hidden />
          {s.label} <span className="font-medium text-foreground tabular-nums">{s.value}</span>
        </li>
      ))}
    </ul>
  )
}

export type Dot = { key: string; tone: Tone; running?: boolean; tip: React.ReactNode; href?: string }

/** 상태 점 줄 (최근 실행·PR CI): 왼쪽이 최신. 점마다 마우스를 올리면 내용, 누르면 링크. */
export function DotStrip({ dots, label }: { dots: Dot[]; label: string }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5" role="list" aria-label={label}>
      {dots.map((d) => {
        const dot = (
          <span
            role="listitem"
            className={cn(
              'inline-block size-3.5 rounded-[4px]',
              d.running ? 'animate-pulse' : '',
              FILL[d.running ? 'rest' : d.tone],
            )}
          />
        )
        return (
          <Tooltip key={d.key}>
            <TooltipTrigger asChild>
              {d.href ? (
                <a href={d.href} target="_blank" rel="noreferrer" className="inline-flex p-0.5">
                  {dot}
                </a>
              ) : (
                <span className="inline-flex p-0.5">{dot}</span>
              )}
            </TooltipTrigger>
            <TooltipContent>{d.tip}</TooltipContent>
          </Tooltip>
        )
      })}
    </div>
  )
}
