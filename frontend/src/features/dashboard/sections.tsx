'use client'

import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from 'recharts'
import { TriangleAlertIcon } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { countdown, memberStats, runState, testedSameAsRunning, type Dashboard, type GithubStatus } from './api'
import { DotStrip, Legend, ToneIcon, type Dot, type Tone } from './charts'

export function Section({
  title,
  children,
  aside,
}: {
  title: string
  children: React.ReactNode
  aside?: React.ReactNode
}) {
  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-xl font-semibold">{title}</h2>
        {aside && <div className="text-[13px] text-muted-foreground">{aside}</div>}
      </div>
      {children}
    </section>
  )
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>
}

const CHECK_TONE: Record<'ok' | 'fail' | 'na', Tone> = { ok: 'good', fail: 'bad', na: 'rest' }

/** 마감 카운트다운 + 제출 체크리스트 (make submit-check와 같은 기준). */
export function DeadlineSection({ data, gh, now }: { data: Dashboard; gh: GithubStatus | null; now: Date }) {
  const c = countdown(data.readiness.deadline, now)
  // "origin/main과 같음"은 GitHub의 main 최신 커밋과 실행 버전을 비교한다 (docker 안엔 git이 없다)
  const same = gh?.status === 'ok' ? testedSameAsRunning(data.server.version, gh.main_sha) : null
  const checks = [
    ...data.readiness.checks,
    {
      key: 'main',
      label: '실행 버전 = main 최신',
      status: same === null ? ('na' as const) : same ? ('ok' as const) : ('fail' as const),
      detail:
        same === null
          ? 'GitHub 정보 없음'
          : same
            ? `main ${gh?.main_sha?.slice(0, 7)}`
            : `main은 ${gh?.main_sha?.slice(0, 7)} — git pull 후 다시 실행`,
    },
  ]
  const ok = checks.filter((x) => x.status === 'ok').length
  const applicable = checks.filter((x) => x.status !== 'na').length
  return (
    <Section title="마감·제출 준비도" aside={`마감 ${new Date(data.readiness.deadline).toLocaleString('ko-KR')}`}>
      <Card>
        <CardContent className="grid gap-8 md:grid-cols-[240px_1fr]">
          <div className="space-y-2">
            <div className="text-[13px] text-muted-foreground">{c.past ? '개발 마감' : '마감까지'}</div>
            <div
              className={
                c.past || (c.days === 0 && c.hours < 2)
                  ? 'text-[40px] leading-none font-semibold tabular-nums text-destructive'
                  : 'text-[40px] leading-none font-semibold tabular-nums'
              }
            >
              {c.label}
            </div>
            <div className="text-[13px] text-muted-foreground">
              준비 {ok} / {applicable} 항목 · 제출 직전에는 make submit-check
            </div>
          </div>
          <ul className="space-y-2.5">
            {checks.map((x) => (
              <li key={x.key} className="flex items-start gap-2.5 text-sm">
                <ToneIcon tone={CHECK_TONE[x.status]} className="mt-0.5" />
                <div className="min-w-0">
                  <div className={x.status === 'na' ? 'text-muted-foreground' : undefined}>{x.label}</div>
                  <div className={x.status === 'fail' ? 'text-[13px] text-destructive' : 'text-[13px] text-muted-foreground'}>
                    {x.status === 'na' ? `해당 없음 — ${x.detail}` : x.detail}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </Section>
  )
}

const TREND: ChartConfig = {
  passed: { label: '통과', color: 'var(--chart-1)' },
  failed: { label: '실패', color: 'var(--destructive)' },
}

/** 시험 추이 (실행마다 통과·실패 테스트 수 누적 막대) + main 워크플로별 최근 실행 이력. */
export function TrendSection({ data, gh }: { data: Dashboard; gh: GithubStatus | null }) {
  const rows = data.test_history.map((r) => ({
    label: new Date(r.ran_at).toLocaleString('ko-KR', {
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }),
    passed: r.total - r.failed,
    failed: r.failed,
    sha: (r.sha ?? '').slice(0, 7) + (r.dirty ? '-dirty' : ''),
  }))
  const byWorkflow = new Map<string, Dot[]>()
  if (gh?.status === 'ok') {
    for (const r of gh.main_runs) {
      const st = runState(r.status, r.conclusion)
      const dots = byWorkflow.get(r.name) ?? []
      dots.push({
        key: r.url,
        tone: st === 'ok' ? 'good' : st === 'fail' ? 'bad' : 'rest',
        running: st === 'running',
        href: r.url,
        tip: `${r.sha} · ${st === 'running' ? '진행 중' : (r.conclusion ?? r.status)} · ${new Date(r.created_at).toLocaleString('ko-KR')}`,
      })
      byWorkflow.set(r.name, dots)
    }
  }
  return (
    <Section title="추이" aside={rows.length ? `시험 ${rows.length}회` : undefined}>
      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <Card>
          <CardContent className="space-y-2">
            <h3 className="text-[15px] font-semibold">시험 통과·실패 (make e2e 실행마다)</h3>
            {rows.length < 2 ? (
              <Empty>시험 기록이 2번 이상 쌓이면 추이가 보여요</Empty>
            ) : (
              <ChartContainer config={TREND} className="h-56 w-full">
                <BarChart data={rows} margin={{ left: 0, right: 8, top: 8 }}>
                  <CartesianGrid vertical={false} />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} minTickGap={24} />
                  <YAxis tickLine={false} axisLine={false} width={36} allowDecimals={false} />
                  <ChartTooltip
                    content={
                      <ChartTooltipContent
                        labelFormatter={(label, payload) => `${label} · ${payload?.[0]?.payload?.sha ?? ''}`}
                      />
                    }
                  />
                  {/* 30초마다 다시 그리므로 애니메이션은 끈다 (매번 막대가 0에서 자라면 산만하다) */}
                  <Bar dataKey="passed" stackId="t" fill="var(--color-passed)" maxBarSize={28} isAnimationActive={false} />
                  <Bar
                    dataKey="failed"
                    stackId="t"
                    fill="var(--color-failed)"
                    radius={[4, 4, 0, 0]}
                    maxBarSize={28}
                    isAnimationActive={false}
                  />
                </BarChart>
              </ChartContainer>
            )}
            {rows.length >= 2 && (
              <Legend
                segments={[
                  { key: 'p', label: '통과 (최근)', value: rows[rows.length - 1].passed, tone: 'good' },
                  { key: 'f', label: '실패 (최근)', value: rows[rows.length - 1].failed, tone: 'bad' },
                ]}
              />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="space-y-4">
            <h3 className="text-[15px] font-semibold">main 실행 이력 (왼쪽이 최신)</h3>
            {byWorkflow.size === 0 ? (
              <Empty>{gh?.status === 'ok' ? 'main에서 실행된 워크플로가 없어요' : 'GitHub 정보 없음'}</Empty>
            ) : (
              [...byWorkflow.entries()].map(([name, dots]) => (
                <div key={name} className="space-y-1.5">
                  <div className="flex items-baseline justify-between text-sm">
                    <span>{name}</span>
                    <span className="text-[13px] text-muted-foreground tabular-nums">
                      성공 {dots.filter((d) => d.tone === 'good').length} / {dots.length}
                    </span>
                  </div>
                  <DotStrip label={`${name} 실행 이력`} dots={dots} />
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </Section>
  )
}

/** 팀원별: 담당 Issue·선점·열린 PR·CI 실패 PR·24시간 머지, 24시간 넘은 선점 경고. */
export function TeamSection({ gh, now }: { gh: GithubStatus | null; now: Date }) {
  if (gh?.status !== 'ok') return null
  const rows = memberStats(gh, now)
  const stale = rows.flatMap((m) => m.staleClaims.map((n) => ({ login: m.login, n })))
  return (
    <Section title="팀원별" aside="담당·선점은 Issue 기준, 머지는 최근 24시간">
      {rows.length === 0 ? (
        <Empty>아직 담당·선점·PR이 없어요</Empty>
      ) : (
        <Card>
          <CardContent className="space-y-4">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>팀원</TableHead>
                  <TableHead className="w-24 text-right">담당 Issue</TableHead>
                  <TableHead className="w-20 text-right">선점</TableHead>
                  <TableHead className="w-20 text-right">열린 PR</TableHead>
                  <TableHead className="w-24 text-right">CI 실패 PR</TableHead>
                  <TableHead className="w-28 text-right">24시간 머지</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((m) => (
                  <TableRow key={m.login}>
                    <TableCell>{m.login}</TableCell>
                    <TableCell className="text-right tabular-nums">{m.issues}</TableCell>
                    <TableCell className="text-right tabular-nums">{m.claims}</TableCell>
                    <TableCell className="text-right tabular-nums">{m.pulls}</TableCell>
                    <TableCell className={m.failingPulls ? 'text-right tabular-nums text-destructive' : 'text-right tabular-nums text-muted-foreground'}>
                      {m.failingPulls}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{m.merges24h}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {stale.length > 0 && (
              <ul className="space-y-1">
                {stale.map((x) => (
                  <li key={x.n} className="flex items-center gap-1.5 text-[13px] text-muted-foreground">
                    <TriangleAlertIcon className="size-4 shrink-0" aria-hidden />
                    #{x.n} 선점이 24시간 넘게 그대로예요 ({x.login}) — 진행 중인지 확인하거나 make release ISSUE={x.n}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}
    </Section>
  )
}
