'use client'

import { useCallback, useEffect, useState } from 'react'
import { ExternalLinkIcon, RefreshCwIcon } from 'lucide-react'
import { ErrorLine } from '@/components/error-line'
import { PageHeader } from '@/components/page-header'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  formatUptime,
  getDashboard,
  getGithubStatus,
  runState,
  testedSameAsRunning,
  type Checks,
  type Dashboard,
  type GithubStatus,
} from './api'

// KDS: 섹션 제목은 카드 밖, 카드 안에 카드 없음, 정상 상태에는 태그 없음(예외만 강조), 빈 상태는 회색 한 줄
export function DashboardView() {
  const [data, setData] = useState<Dashboard | null>(null)
  const [gh, setGh] = useState<GithubStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  // 로컬 칸과 GitHub 칸을 따로 불러온다 — GitHub이 느리거나 실패해도 로컬 칸은 바로 보인다
  const load = useCallback(() => {
    void getDashboard()
      .then((d) => {
        setData(d)
        setError(null)
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
    void getGithubStatus()
      .then(setGh)
      .catch((e: Error) =>
        setGh({
          status: 'error',
          message: e.message,
          repo: null,
          fetched_at: null,
          issues: [],
          pulls: [],
          main_runs: [],
          claims: [],
        }),
      )
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const refresh = () => {
    setLoading(true)
    load()
  }

  return (
    <div className="mx-auto w-full max-w-[1200px] space-y-10 px-4 py-6">
      <PageHeader
        title="현황판"
        description="이 PC의 서버·DB·시험 결과와 요구사항·GitHub 진행 상황"
        actions={
          <Button variant="outline" size="sm" onClick={refresh} disabled={loading}>
            <RefreshCwIcon className={loading ? 'animate-spin' : undefined} /> 새로 고침
          </Button>
        }
      />
      {error && <ErrorLine message={`현황을 불러오지 못했어요: ${error}`} onRetry={refresh} />}
      {data && (
        <>
          <ServerSection data={data} />
          <TestsSection data={data} />
          <ReqsSection data={data} />
        </>
      )}
      {!data && !error && <p className="text-sm text-muted-foreground">불러오는 중…</p>}
      <GithubSection gh={gh} />
    </div>
  )
}

function Section({ title, children, aside }: { title: string; children: React.ReactNode; aside?: React.ReactNode }) {
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

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <dt className="text-[13px] text-muted-foreground">{label}</dt>
      <dd className="text-[15px]">{children}</dd>
    </div>
  )
}

const short = (sha?: string | null) => (sha ? sha.slice(0, 7) + (sha.endsWith('-dirty') ? '-dirty' : '') : '-')

function ServerSection({ data }: { data: Dashboard }) {
  const s = data.server
  return (
    <Section title="서버·DB" aside={`확인 ${new Date(data.generated_at).toLocaleTimeString('ko-KR')}`}>
      <Card>
        <CardContent>
          <dl className="grid grid-cols-2 gap-6 md:grid-cols-5">
            <Field label="실행 버전">
              <code className="text-sm">{short(s.version)}</code>
            </Field>
            <Field label="실행 시간">{formatUptime(s.uptime_seconds)}</Field>
            <Field label="LLM">{s.llm ?? '-'}</Field>
            <Field label="DB">
              {s.db === 'ok' ? '연결됨' : <Badge variant="destructive">{s.db ?? '알 수 없음'}</Badge>}
            </Field>
            <Field label="마이그레이션">{data.migrations.length}개 적용</Field>
          </dl>
          {data.migrations.length > 0 && (
            <p className="mt-4 text-[13px] text-muted-foreground">
              {data.migrations.map((m) => m.version).join(' · ')}
            </p>
          )}
        </CardContent>
      </Card>
    </Section>
  )
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
    <Section title="시험 결과" aside={`${t.ran_at ?? ''} · ${t.run_id}`}>
      <Card>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-3 text-[15px]">
            {t.overall === 'FAIL' ? (
              <Badge variant="destructive">FAIL</Badge>
            ) : (
              <span className="font-semibold">전체 {t.overall ?? '-'}</span>
            )}
            <span className="text-muted-foreground">
              커밋 <code className="text-sm">{short(t.sha)}</code>
            </span>
            {t.dirty && <Badge variant="outline">커밋 안 된 코드로 실행 — 제출 근거 아님</Badge>}
            {same === false && (
              <span className="text-[13px] text-destructive">실행 중인 버전과 시험한 커밋이 달라요</span>
            )}
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>묶음</TableHead>
                <TableHead>결과</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {t.suites.map((s) => (
                <TableRow key={s.name}>
                  <TableCell>{s.name}</TableCell>
                  <TableCell className={/실패 [1-9]|결과 없음/.test(s.result) ? 'text-destructive' : undefined}>
                    {s.result}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {t.tcs.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-28">TC</TableHead>
                  <TableHead className="w-24">결과</TableHead>
                  <TableHead>테스트</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {t.tcs.map((c) => (
                  <TableRow key={c.tc}>
                    <TableCell>{c.tc}</TableCell>
                    <TableCell className={c.result.startsWith('FAIL') ? 'text-destructive' : undefined}>
                      {c.result}
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

function ReqsSection({ data }: { data: Dashboard }) {
  const r = data.reqs
  const done = r.items.filter((i) => i.state === '검증됨').length
  return (
    <Section title="요구사항 진행" aside={r.items.length ? `검증됨 ${done} / ${r.items.length}` : undefined}>
      {r.status === 'none' ? (
        <Empty>docs/prd.md가 없어요 — 팀 레포에서 /plan-topic으로 요구사항을 만들면 보여요</Empty>
      ) : r.items.length === 0 ? (
        <Empty>prd.md에 REQ가 없어요</Empty>
      ) : (
        <Card>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-24">ID</TableHead>
                  <TableHead>요구사항</TableHead>
                  <TableHead className="w-20">우선순위</TableHead>
                  <TableHead className="w-20">Issue</TableHead>
                  <TableHead className="w-32">상태</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {r.items.map((i) => (
                  <TableRow key={i.id}>
                    <TableCell>{i.id}</TableCell>
                    <TableCell>{i.title}</TableCell>
                    <TableCell className="text-muted-foreground">{i.priority}</TableCell>
                    <TableCell className="text-muted-foreground">{i.issue}</TableCell>
                    <TableCell className={i.state === '검증됨' ? 'font-semibold' : 'text-muted-foreground'}>
                      {i.state}
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

const CHECKS: Record<Checks, string> = { pass: '통과', fail: '실패', pending: '진행 중', none: '검사 없음' }

function Link({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:underline">
      {children}
      <ExternalLinkIcon className="size-3 text-muted-foreground" aria-hidden />
    </a>
  )
}

function GithubSection({ gh }: { gh: GithubStatus | null }) {
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
  return (
    <Section
      title="GitHub"
      aside={`${gh.repo} · ${gh.fetched_at ? new Date(gh.fetched_at).toLocaleTimeString('ko-KR') : ''} 기준 (1분 캐시)`}
    >
      <div className="space-y-6">
        <div className="space-y-2">
          <h3 className="text-[15px] font-semibold">main 최근 실행</h3>
          {gh.main_runs.length === 0 ? (
            <Empty>main에서 실행된 워크플로가 없어요</Empty>
          ) : (
            <ul className="space-y-1 text-sm">
              {gh.main_runs.map((r) => {
                const st = runState(r.status, r.conclusion)
                return (
                  <li key={r.url} className="flex flex-wrap items-center gap-2">
                    {st === 'fail' ? (
                      <Badge variant="destructive">실패</Badge>
                    ) : (
                      <span className="w-14 text-muted-foreground">
                        {st === 'ok' ? '성공' : st === 'running' ? '진행 중' : r.conclusion}
                      </span>
                    )}
                    <Link href={r.url}>{r.name}</Link>
                    <code className="text-[13px] text-muted-foreground">{r.sha}</code>
                    <span className="text-[13px] text-muted-foreground">
                      {new Date(r.created_at).toLocaleString('ko-KR')}
                    </span>
                  </li>
                )
              })}
            </ul>
          )}
        </div>

        <div className="space-y-2">
          <h3 className="text-[15px] font-semibold">열린 PR {gh.pulls.length}개</h3>
          {gh.pulls.length === 0 ? (
            <Empty>열린 PR이 없어요</Empty>
          ) : (
            <Card>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-16">#</TableHead>
                      <TableHead>제목</TableHead>
                      <TableHead className="w-32">작성자</TableHead>
                      <TableHead className="w-24">CI</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {gh.pulls.map((p) => (
                      <TableRow key={p.number}>
                        <TableCell>{p.number}</TableCell>
                        <TableCell>
                          <Link href={p.url}>{p.title}</Link>
                          {p.draft && <span className="ml-2 text-[13px] text-muted-foreground">초안</span>}
                          <div className="text-[13px] text-muted-foreground">{p.branch}</div>
                        </TableCell>
                        <TableCell className="text-muted-foreground">{p.author}</TableCell>
                        <TableCell>
                          {p.checks === 'fail' ? (
                            <Badge variant="destructive">실패</Badge>
                          ) : (
                            <span className="text-muted-foreground">{CHECKS[p.checks]}</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-2">
          <h3 className="text-[15px] font-semibold">열린 Issue {gh.issues.length}개</h3>
          {gh.issues.length === 0 ? (
            <Empty>열린 Issue가 없어요</Empty>
          ) : (
            <Card>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-16">#</TableHead>
                      <TableHead>제목</TableHead>
                      <TableHead className="w-40">담당</TableHead>
                      <TableHead className="w-40">선점</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {gh.issues.map((i) => (
                      <TableRow key={i.number}>
                        <TableCell>{i.number}</TableCell>
                        <TableCell>
                          <Link href={i.url}>{i.title}</Link>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {i.assignees.join(', ') || '미배정'}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {owner.has(i.number) ? (owner.get(i.number) ?? '알 수 없음') : '-'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </Section>
  )
}
