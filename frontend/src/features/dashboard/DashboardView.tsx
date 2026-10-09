'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { PauseIcon, PlayIcon, RefreshCwIcon } from 'lucide-react'
import { ErrorLine } from '@/components/error-line'
import { PageHeader } from '@/components/page-header'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  failureAlerts,
  formatUptime,
  getDashboard,
  getGithubStatus,
  getLeadTime,
  parseSuite,
  reqProgress,
  runState,
  testedSameAsRunning,
  testTotals,
  type Dashboard,
  type GithubStatus,
  type LeadTime,
} from './api'
import { DotStrip, Legend, Link, Meter, StatTile, ToneIcon, type Dot, type Segment, type Tone } from './charts'
import { PullRow } from './PullRow'
import { DeadlineSection, Empty, LeadTimeSection, Section, TeamSection, TrendSection } from './sections'

const AUTO_SEC = 30 // 자동 새로 고침 간격 (GitHub은 서버가 1~5분 캐시하므로 한도 걱정 없음)
const AUTO_KEY = 'dashboard:auto'

// KDS: 섹션 제목은 카드 밖, 카드 안에 카드 없음, 정상에는 태그 없음(예외만 강조), 빨강은 실패에만, 빈 상태는 회색 한 줄
export function DashboardView() {
  const [data, setData] = useState<Dashboard | null>(null)
  const [gh, setGh] = useState<GithubStatus | null>(null)
  const [lead, setLead] = useState<LeadTime | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [auto, setAuto] = useState(true)
  const [now, setNow] = useState(() => new Date())
  const [loadedAt, setLoadedAt] = useState<Date | null>(null)
  // 직전 화면 상태 — "실패로 바뀐 것"만 알리려고 (처음 불러올 때는 알리지 않는다)
  const last = useRef<{ data: Dashboard | null; gh: GithubStatus | null }>({ data: null, gh: null })

  const notify = useCallback((next: { data: Dashboard | null; gh: GithubStatus | null }) => {
    for (const msg of failureAlerts(last.current, next)) toast.error(msg)
    last.current = next
  }, [])

  // 로컬 칸과 GitHub 칸을 따로 불러온다 — GitHub이 느리거나 실패해도 로컬 칸은 바로 보인다
  const load = useCallback(() => {
    void getDashboard()
      .then((d) => {
        setData(d)
        setError(null)
        setLoadedAt(new Date())
        notify({ ...last.current, data: d })
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
    void getGithubStatus()
      .then((g) => {
        setGh(g)
        notify({ ...last.current, gh: g })
      })
      .catch((e: Error) => setGh({ ...EMPTY_GH, status: 'error', message: e.message }))
    // 리드타임도 따로 — 실패하면 이 칸만 오류로 보이고 나머지 화면은 그대로다
    void getLeadTime()
      .then(setLead)
      .catch((e: Error) => setLead({ ...EMPTY_LEAD, status: 'error', message: e.message }))
  }, [notify])

  useEffect(() => {
    load()
  }, [load])

  // 자동 새로 고침 켜기/끄기는 이 브라우저에 기억한다
  useEffect(() => {
    void Promise.resolve().then(() => {
      try {
        if (localStorage.getItem(AUTO_KEY) === 'off') setAuto(false)
      } catch {
        /* 저장소를 못 쓰면 기본값(켜짐) */
      }
    })
  }, [])

  useEffect(() => {
    if (!auto) return
    const id = setInterval(load, AUTO_SEC * 1000)
    return () => clearInterval(id)
  }, [auto, load])

  // 마감 카운트다운·"n초 전" 표시용 시계
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  const refresh = () => {
    setLoading(true)
    load()
  }
  const toggleAuto = () => {
    setAuto((on) => {
      try {
        localStorage.setItem(AUTO_KEY, on ? 'off' : 'on')
      } catch {
        /* 무시 */
      }
      return !on
    })
  }
  const ago = loadedAt ? Math.max(0, Math.round((now.getTime() - loadedAt.getTime()) / 1000)) : null

  return (
    <div className="mx-auto w-full max-w-[1200px] space-y-10 px-4 py-6">
      <PageHeader
        title="현황판"
        description="이 PC의 서버·DB·시험 결과와 요구사항·GitHub 진행 상황"
        actions={
          <div className="flex items-center gap-2">
            {ago !== null && (
              <span className="text-[13px] text-muted-foreground tabular-nums">
                {ago}초 전 갱신{auto ? ` · ${AUTO_SEC}초마다` : ''}
              </span>
            )}
            <Button variant="outline" size="sm" onClick={toggleAuto} aria-pressed={auto}>
              {auto ? <PauseIcon /> : <PlayIcon />} 자동 {auto ? '끄기' : '켜기'}
            </Button>
            <Button variant="outline" size="sm" onClick={refresh} disabled={loading}>
              <RefreshCwIcon className={loading ? 'animate-spin' : undefined} /> 새로 고침
            </Button>
          </div>
        }
      />
      {error && <ErrorLine message={`현황을 불러오지 못했어요: ${error}`} onRetry={refresh} />}
      {!data && !error && <p className="text-sm text-muted-foreground">불러오는 중…</p>}
      {data && <Kpis data={data} gh={gh} />}
      {data && <DeadlineSection data={data} gh={gh} now={now} />}
      {data && <TrendSection data={data} gh={gh} />}
      {data && (
        <div className="grid gap-10 lg:grid-cols-2">
          <TestsSection data={data} />
          <ReqsSection data={data} />
        </div>
      )}
      <LeadTimeSection lt={lead} />
      <TeamSection gh={gh} now={now} />
      <GithubSection gh={gh} now={now} />
      {data && <ServerSection data={data} />}
    </div>
  )
}

const EMPTY_GH: GithubStatus = {
  status: 'unconfigured',
  message: null,
  repo: null,
  fetched_at: null,
  issues: [],
  pulls: [],
  main_runs: [],
  claims: [],
  main_sha: null,
  recent_merges: [],
}

const EMPTY_LEAD: LeadTime = {
  status: 'unconfigured',
  message: null,
  repo: null,
  fetched_at: null,
  count: 0,
  median_seconds: null,
  buckets: [],
}

const short = (sha?: string | null) => (sha ? sha.slice(0, 7) + (sha.endsWith('-dirty') ? '-dirty' : '') : '-')

/** 맨 위 지표 4개: 서버 · 시험 통과 · 요구사항 검증 · main CI. */
function Kpis({ data, gh }: { data: Dashboard; gh: GithubStatus | null }) {
  const s = data.server
  const serverOk = s.status === 'ok' && s.db === 'ok'
  const t = testTotals(data.tests.suites)
  const testTone: Tone = data.tests.status === 'none' ? 'rest' : t.failed || t.missing ? 'bad' : 'good'
  const r = reqProgress(data.reqs.items)
  const runs = gh?.status === 'ok' ? gh.main_runs.slice(0, 6) : [] // 카드에는 최근 6개만
  const runStates = runs.map((x) => runState(x.status, x.conclusion))
  const lastRun = runStates[0]
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatTile
        label="서버·DB"
        tone={serverOk ? 'good' : 'bad'}
        value={serverOk ? '정상' : s.db === 'ok' ? s.status : 'DB 오류'}
        sub={`실행 ${formatUptime(s.uptime_seconds)} · ${short(s.version)} · 마이그레이션 ${data.migrations.length}개`}
      />
      <StatTile
        label="시험 통과"
        tone={testTone}
        value={
          data.tests.status === 'none' ? (
            <span className="text-muted-foreground">-</span>
          ) : (
            <>
              {t.passed}
              <span className="text-base font-normal text-muted-foreground"> / {t.total}</span>
            </>
          )
        }
        sub={data.tests.status === 'none' ? '시험 기록 없음 — make e2e' : `실패 ${t.failed}${t.missing ? ` · 실행 실패 묶음 ${t.missing}` : ''} · ${data.tests.ran_at ?? ''}`}
      >
        <Meter
          label="시험"
          segments={[
            { key: 'p', label: '통과', value: t.passed, tone: 'good' },
            { key: 'f', label: '실패', value: t.failed, tone: 'bad' },
          ]}
        />
      </StatTile>
      <StatTile
        label="요구사항 검증"
        tone={r.total === 0 ? 'rest' : r.verified === r.total ? 'good' : 'rest'}
        value={
          r.total === 0 ? (
            <span className="text-muted-foreground">-</span>
          ) : (
            <>
              {r.verified}
              <span className="text-base font-normal text-muted-foreground"> / {r.total}</span>
            </>
          )
        }
        sub={r.total === 0 ? 'docs/prd.md 없음' : `${Math.round((r.verified / r.total) * 100)}% 검증됨`}
      >
        <Meter
          label="요구사항"
          segments={[
            { key: 'v', label: '검증됨', value: r.verified, tone: 'good' },
            { key: 'o', label: '미검증', value: r.total - r.verified, tone: 'rest' },
          ]}
        />
      </StatTile>
      <StatTile
        label="main CI"
        tone={lastRun === 'fail' ? 'bad' : lastRun === 'ok' ? 'good' : 'rest'}
        value={
          runs.length === 0 ? (
            <span className="text-muted-foreground">-</span>
          ) : (
            <>
              {runStates.filter((x) => x === 'ok').length}
              <span className="text-base font-normal text-muted-foreground"> / {runs.length} 성공</span>
            </>
          )
        }
        sub={gh?.status === 'ok' ? '최근 실행 (왼쪽이 최신)' : gh?.status === 'error' ? 'GitHub 불러오기 실패' : 'GitHub 설정 필요'}
      >
        {runs.length > 0 && <DotStrip label="main 최근 실행" dots={runDots(runs)} />}
      </StatTile>
    </div>
  )
}

function runDots(runs: GithubStatus['main_runs']): Dot[] {
  return runs.map((r) => {
    const st = runState(r.status, r.conclusion)
    return {
      key: r.url,
      tone: st === 'ok' ? 'good' : st === 'fail' ? 'bad' : 'rest',
      running: st === 'running',
      href: r.url,
      tip: `${r.name} · ${r.sha} · ${st === 'running' ? '진행 중' : (r.conclusion ?? r.status)} · ${new Date(r.created_at).toLocaleString('ko-KR')}`,
    }
  })
}

function TestsSection({ data }: { data: Dashboard }) {
  const t = data.tests
  if (t.status === 'none') {
    return (
      <Section title="시험 결과">
        <Empty>아직 시험 기록이 없어요 — make e2e를 실행하면 여기에 보여요</Empty>
      </Section>
    )
  }
  const same = testedSameAsRunning(data.server.version, t.sha)
  return (
    <Section title="시험 결과" aside={t.ran_at ?? undefined}>
      <Card>
        <CardContent className="space-y-5">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-[13px] text-muted-foreground">
            {t.overall === 'FAIL' && <Badge variant="destructive">FAIL</Badge>}
            <span>
              커밋 <code>{short(t.sha)}</code>
            </span>
            {t.dirty && <Badge variant="outline">커밋 안 된 코드로 실행 — 제출 근거 아님</Badge>}
            {same === false && <Badge variant="outline">실행 중인 버전과 다른 커밋을 시험함</Badge>}
          </div>
          <ul className="space-y-4">
            {t.suites.map((s) => {
              const p = parseSuite(s.result)
              return (
                <li key={s.name} className="space-y-1.5">
                  <div className="flex items-baseline justify-between gap-2 text-sm">
                    <span>{s.name}</span>
                    <span className={p && p.failed === 0 ? 'text-muted-foreground tabular-nums' : 'text-destructive tabular-nums'}>
                      {p ? `${p.total - p.failed} / ${p.total}` : s.result}
                    </span>
                  </div>
                  <Meter
                    label={s.name}
                    segments={
                      p
                        ? [
                            { key: 'p', label: '통과', value: p.total - p.failed, tone: 'good' },
                            { key: 'f', label: '실패', value: p.failed, tone: 'bad' },
                          ]
                        : [{ key: 'x', label: '실행 실패', value: 1, tone: 'bad' }]
                    }
                  />
                </li>
              )
            })}
          </ul>
          <Legend
            segments={[
              { key: 'p', label: '통과', value: testTotals(t.suites).passed, tone: 'good' },
              { key: 'f', label: '실패', value: testTotals(t.suites).failed, tone: 'bad' },
            ]}
          />
          {t.tcs.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-24">TC</TableHead>
                  <TableHead className="w-20">결과</TableHead>
                  <TableHead>테스트</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {t.tcs.map((c) => (
                  <TableRow key={c.tc}>
                    <TableCell>{c.tc}</TableCell>
                    <TableCell>
                      <span className="flex items-center gap-1.5">
                        <ToneIcon tone={c.result.startsWith('PASS') ? 'good' : c.result.startsWith('FAIL') ? 'bad' : 'rest'} />
                        {c.result}
                      </span>
                    </TableCell>
                    <TableCell className="text-[13px] text-muted-foreground">{c.test}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <Empty>TC ID가 붙은 테스트가 아직 없어요</Empty>
          )}
        </CardContent>
      </Card>
    </Section>
  )
}

const reqTone = (state: string): Tone =>
  state === '검증됨' ? 'good' : state.startsWith('구현됨') ? 'partial' : 'rest'

function ReqsSection({ data }: { data: Dashboard }) {
  const r = data.reqs
  const p = reqProgress(r.items)
  const segments: Segment[] = p.byState.map(([state, n]) => ({
    key: state,
    label: state,
    value: n,
    tone: reqTone(state),
  }))
  return (
    <Section title="요구사항 진행" aside={p.total ? `검증됨 ${p.verified} / ${p.total}` : undefined}>
      {r.status === 'none' ? (
        <Empty>docs/prd.md가 없어요 — 팀 레포에서 /plan-topic으로 요구사항을 만들면 보여요</Empty>
      ) : r.items.length === 0 ? (
        <Empty>prd.md에 REQ가 없어요</Empty>
      ) : (
        <Card>
          <CardContent className="space-y-5">
            <Meter label="요구사항 상태" height={12} segments={segments} />
            <Legend segments={segments} />
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-20">ID</TableHead>
                  <TableHead>요구사항</TableHead>
                  <TableHead className="w-16">Issue</TableHead>
                  <TableHead className="w-32">상태</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {r.items.map((i) => (
                  <TableRow key={i.id}>
                    <TableCell>{i.id}</TableCell>
                    <TableCell>
                      {i.title}
                      <span className="ml-2 text-[13px] text-muted-foreground">{i.priority}</span>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{i.issue}</TableCell>
                    <TableCell>
                      <span className="flex items-center gap-1.5">
                        <ToneIcon tone={reqTone(i.state)} />
                        <span className={i.state === '검증됨' ? undefined : 'text-muted-foreground'}>{i.state}</span>
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </Section>
  )
}

export function GithubSection({ gh, now }: { gh: GithubStatus | null; now: Date }) {
  if (!gh) {
    return (
      <Section title="GitHub">
        <Empty>불러오는 중…</Empty>
      </Section>
    )
  }
  if (gh.status !== 'ok') {
    return (
      <Section title="GitHub" aside={gh.repo ?? undefined}>
        {gh.status === 'error' ? (
          <ErrorLine message={gh.message ?? 'GitHub 현황을 불러오지 못했어요'} />
        ) : (
          <Empty>{gh.message} (docs/contracts/dashboard.md)</Empty>
        )}
      </Section>
    )
  }
  const owner = new Map(gh.claims.map((c) => [c.issue, c.owner]))
  const count = (f: (i: GithubStatus['issues'][number]) => boolean) => gh.issues.filter(f).length
  const issueSegments: Segment[] = [
    { key: 'c', label: '선점됨', value: count((i) => owner.has(i.number)), tone: 'good' },
    { key: 'a', label: '배정만', value: count((i) => !owner.has(i.number) && i.assignees.length > 0), tone: 'rest' },
    { key: 'u', label: '미배정', value: count((i) => !owner.has(i.number) && i.assignees.length === 0), tone: 'rest' },
  ]
  const fetched = gh.fetched_at ? new Date(gh.fetched_at).toLocaleTimeString('ko-KR') : ''
  return (
    <Section title="GitHub" aside={`${gh.repo} · ${fetched} 기준`}>
      <div className="grid gap-10 lg:grid-cols-2">
        <div className="space-y-3">
          <h3 className="text-[15px] font-semibold">열린 PR {gh.pulls.length}개</h3>
          {gh.pulls.length === 0 ? (
            <Empty>열린 PR이 없어요</Empty>
          ) : (
            <Card>
              <CardContent>
                <ul className="divide-y divide-border">
                  {gh.pulls.map((p) => (
                    <PullRow key={p.number} pull={p} now={now} />
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-3">
          <h3 className="text-[15px] font-semibold">열린 Issue {gh.issues.length}개</h3>
          {gh.issues.length === 0 ? (
            <Empty>열린 Issue가 없어요</Empty>
          ) : (
            <Card>
              <CardContent className="space-y-4">
                <Meter label="Issue 담당 현황" segments={issueSegments} />
                <Legend segments={issueSegments} />
                <ul className="divide-y divide-border">
                  {gh.issues.map((i) => (
                    <li key={i.number} className="flex items-start gap-3 py-3 last:pb-0">
                      <ToneIcon tone={owner.has(i.number) ? 'good' : 'rest'} className="mt-0.5" />
                      <div className="min-w-0 flex-1">
                        <Link href={i.url}>
                          #{i.number} {i.title}
                        </Link>
                        <div className="text-[13px] text-muted-foreground">
                          {owner.has(i.number)
                            ? `선점 ${owner.get(i.number) ?? '알 수 없음'}`
                            : i.assignees.length
                              ? `담당 ${i.assignees.join(', ')} · 선점 안 됨`
                              : '미배정'}
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </Section>
  )
}

function ServerSection({ data }: { data: Dashboard }) {
  const s = data.server
  return (
    <Section title="서버·DB 상세" aside={`확인 ${new Date(data.generated_at).toLocaleTimeString('ko-KR')}`}>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm md:grid-cols-4">
        {[
          ['실행 버전', <code key="v">{short(s.version)}</code>],
          ['LLM', s.llm ?? '-'],
          ['DB', s.db === 'ok' ? '연결됨' : (s.db ?? '알 수 없음')],
          ['마이그레이션', data.migrations.map((m) => m.version).join(' · ') || '없음'],
        ].map(([k, v]) => (
          <div key={k as string} className="space-y-1">
            <dt className="text-[13px] text-muted-foreground">{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
    </Section>
  )
}
