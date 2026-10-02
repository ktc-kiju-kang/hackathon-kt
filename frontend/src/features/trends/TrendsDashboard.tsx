'use client'

import { useEffect, useMemo, useState } from 'react'
import { CircleAlertIcon, TrendingDownIcon, TrendingUpIcon } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn } from '@/lib/utils'
import { type Topic, type TrendSeries, type TrendSummary, type TrendsMeta, TOPICS, getMeta, getSeries, getSummary } from './api'
import { INTENT_LABEL, TOPIC_LABEL, countryLabel, pct, signedPp } from './labels'
import { CHART_COLORS, type LinePoint, ShareLineChart, TopicChangeChart } from './TrendCharts'

const GLOBAL = 'GLOBAL' // Select 값용. API에는 country 생략(null)으로 보낸다
const PERIODS = [
  { value: '12', label: '최근 1년' },
  { value: '23', label: '전체 (2024-07~)' },
]

type Loaded = {
  key: string
  summary: TrendSummary
  topic: TrendSeries
  topicGlobal: TrendSeries
  work: TrendSeries
  workGlobal: TrendSeries
  intent: TrendSeries
}

// [{month, key, share}] → [{month, <name>: 백분율}] (여러 시계열을 month 기준으로 합친다)
function mergeSeries(parts: { name: string; series: TrendSeries; key: string }[]): LinePoint[] {
  const byMonth = new Map<string, LinePoint>()
  for (const { name, series, key } of parts) {
    for (const p of series.points) {
      if (p.key !== key) continue
      const row = byMonth.get(p.month) ?? { month: p.month }
      row[name] = Math.round(p.share * 1000) / 10
      byMonth.set(p.month, row)
    }
  }
  return [...byMonth.values()].sort((a, b) => a.month.localeCompare(b.month))
}

export function TrendsDashboard() {
  const [meta, setMeta] = useState<TrendsMeta | null>(null)
  const [country, setCountry] = useState('KR')
  const [months, setMonths] = useState('12')
  const [topic, setTopic] = useState<Topic>('Practical Guidance')
  const [scope, setScope] = useState<'all' | 'work'>('all')
  const [data, setData] = useState<Loaded | null>(null)
  const [error, setError] = useState<{ key: string; message: string } | null>(null)

  const apiCountry = country === GLOBAL ? null : country
  const key = `${country}|${months}` // topic 변경은 이미 받은 시계열로 다시 그리기만 한다

  useEffect(() => {
    getMeta()
      .then(setMeta)
      .catch(() => setError({ key: 'meta', message: '데이터 목록을 불러오지 못했습니다' }))
  }, [])

  useEffect(() => {
    let cancelled = false // 늦게 도착한 이전 선택의 응답이 최신 결과를 덮지 않게
    Promise.all([
      getSummary(apiCountry, Number(months)),
      getSeries({ dimension: 'topic', country: apiCountry }),
      getSeries({ dimension: 'topic' }),
      getSeries({ dimension: 'work_related', country: apiCountry }),
      getSeries({ dimension: 'work_related' }),
      getSeries({ dimension: 'ask_do_express', country: apiCountry, work_related: 1 }),
    ])
      .then(([summary, topicS, topicGlobal, work, workGlobal, intent]) => {
        if (!cancelled) setData({ key, summary, topic: topicS, topicGlobal, work, workGlobal, intent })
      })
      .catch(() => {
        if (!cancelled) setError({ key, message: '트렌드 데이터를 불러오지 못했습니다. 잠시 후 다시 시도하세요.' })
      })
    return () => {
      cancelled = true
    }
  }, [key, apiCountry, months])

  const current = data?.key === key ? data : null // 다른 선택의 데이터는 보여주지 않는다
  const loading = !current && error?.key !== key
  const name = countryLabel(apiCountry)
  const compareGlobal = apiCountry !== null

  const charts = useMemo(() => {
    if (!current) return null
    // config 키는 CSS 변수 이름(--color-<key>)이 되므로 영문만 쓴다
    const lineConfig = {
      own: { label: name, color: 'var(--series-1)' },
      ...(compareGlobal ? { global: { label: '전 세계', color: 'var(--series-2)' } } : {}),
    }
    const pair = (own: TrendSeries, global: TrendSeries, k: string) =>
      mergeSeries([
        { name: 'own', series: own, key: k },
        ...(compareGlobal ? [{ name: 'global', series: global, key: k }] : []),
      ])
    const intents = (['asking', 'doing', 'expressing'] as const).map((i, n) => ({
      i,
      label: INTENT_LABEL[i],
      color: `var(--series-${n + 1})`,
    }))
    return {
      topic: pair(current.topic, current.topicGlobal, topic),
      lineConfig,
      work: pair(current.work, current.workGlobal, '1'),
      intent: mergeSeries(intents.map(({ i }) => ({ name: i, series: current.intent, key: i }))),
      intentConfig: Object.fromEntries(intents.map(({ i, label, color }) => [i, { label, color }])),
    }
  }, [current, name, compareGlobal, topic])

  const summary = current?.summary
  const rows = summary ? (scope === 'all' ? summary.topics : summary.work_topics) : []

  return (
    <div className={cn('mx-auto w-full max-w-6xl space-y-4 p-4 md:p-6', CHART_COLORS)}>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">AI 활용 트렌드</h1>
          <p className="text-sm text-muted-foreground">
            개인 ChatGPT 사용 통계(OpenAI Signals)로 본 국가별 AI 활용 변화
          </p>
        </div>
        <div className="flex gap-2">
          <Select value={country} onValueChange={setCountry}>
            <SelectTrigger className="w-40" aria-label="국가">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={GLOBAL}>전 세계</SelectItem>
              {(meta?.countries ?? ['KR'])
                .map((c) => ({ c, label: countryLabel(c) }))
                .sort((a, b) => (a.c === 'KR' ? -1 : b.c === 'KR' ? 1 : a.label.localeCompare(b.label, 'ko')))
                .map(({ c, label }) => (
                  <SelectItem key={c} value={c}>
                    {label}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
          <Select value={months} onValueChange={setMonths}>
            <SelectTrigger className="w-40" aria-label="비교 기간">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PERIODS.map((p) => (
                <SelectItem key={p.value} value={p.value}>
                  {p.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {error && (error.key === key || error.key === 'meta') && (
        <Card className="border-destructive/50">
          <CardContent className="flex items-center gap-2 text-sm text-destructive">
            <CircleAlertIcon className="size-4" /> {error.message}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {loading || !summary ? (
          Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-28" />)
        ) : (
          <>
            <StatTile
              label="업무 관련 메시지 비중"
              value={pct(summary.work_share.to)}
              detail={`${pct(summary.work_share.from)}에서 ${signedPp(summary.work_share.change_pp)}`}
              trend={summary.work_share.change_pp}
            />
            <StatTile
              label="가장 많이 늘어난 주제"
              value={TOPIC_LABEL[summary.topics[0].topic]}
              detail={`${pct(summary.topics[0].to_share)} (${signedPp(summary.topics[0].change_pp)})`}
              trend={summary.topics[0].change_pp}
            />
            <StatTile
              label="가장 많이 줄어든 주제"
              value={TOPIC_LABEL[summary.topics.at(-1)!.topic]}
              detail={`${pct(summary.topics.at(-1)!.to_share)} (${signedPp(summary.topics.at(-1)!.change_pp)})`}
              trend={summary.topics.at(-1)!.change_pp}
            />
            {summary.usage_rank ? (
              <StatTile
                label="인구 대비 사용량 순위"
                value={`${summary.usage_rank.rank}위`}
                detail={
                  summary.usage_rank.previous_rank
                    ? `${summary.usage_rank.previous_quarter} ${summary.usage_rank.previous_rank}위에서 ${summary.usage_rank.quarter} 기준`
                    : `${summary.usage_rank.quarter} 기준`
                }
                trend={
                  summary.usage_rank.previous_rank ? summary.usage_rank.previous_rank - summary.usage_rank.rank : 0
                }
              />
            ) : (
              <StatTile
                label="업무 메시지 중 작업 요청"
                value={pct(summary.work_intent.find((w) => w.intent === 'doing')!.to_share)}
                detail={signedPp(summary.work_intent.find((w) => w.intent === 'doing')!.change_pp)}
                trend={summary.work_intent.find((w) => w.intent === 'doing')!.change_pp}
              />
            )}
          </>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-start justify-between gap-2">
            <div className="space-y-1.5">
              <CardTitle>주제별 비중 변화</CardTitle>
              <CardDescription>
                {summary ? `${summary.period.from} → ${summary.period.to}, ${name}` : ' '}
              </CardDescription>
            </div>
            <Tabs value={scope} onValueChange={(v) => setScope(v as 'all' | 'work')}>
              <TabsList>
                <TabsTrigger value="all">전체</TabsTrigger>
                <TabsTrigger value="work">업무</TabsTrigger>
              </TabsList>
            </Tabs>
          </CardHeader>
          <CardContent>{loading || !summary ? <Skeleton className="h-72" /> : <TopicChangeChart rows={rows} />}</CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-start justify-between gap-2">
            <div className="space-y-1.5">
              <CardTitle>주제 비중 추이</CardTitle>
              <CardDescription>전체 메시지 중 {TOPIC_LABEL[topic]} 비중 (월별)</CardDescription>
            </div>
            <Select value={topic} onValueChange={(v) => setTopic(v as Topic)}>
              <SelectTrigger className="w-36" aria-label="주제">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TOPICS.map((t) => (
                  <SelectItem key={t} value={t}>
                    {TOPIC_LABEL[t]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </CardHeader>
          <CardContent>
            {loading || !charts ? (
              <Skeleton className="h-64" />
            ) : (
              <ShareLineChart data={charts.topic} config={charts.lineConfig} />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>업무 관련 메시지 비중</CardTitle>
            <CardDescription>전체 메시지 중 업무와 관련된 메시지 (월별)</CardDescription>
          </CardHeader>
          <CardContent>
            {loading || !charts ? (
              <Skeleton className="h-64" />
            ) : (
              <ShareLineChart data={charts.work} config={charts.lineConfig} />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>업무 메시지의 요청 방식</CardTitle>
            <CardDescription>{name} 업무 메시지 중 질문 · 작업 요청 · 표현 비중 (월별)</CardDescription>
          </CardHeader>
          <CardContent>
            {loading || !charts ? (
              <Skeleton className="h-64" />
            ) : (
              <ShareLineChart data={charts.intent} config={charts.intentConfig} />
            )}
          </CardContent>
        </Card>
      </div>

      <p className="text-xs text-muted-foreground">
        Data:{' '}
        <a href={meta?.source.url ?? 'https://openai.com/signals/data-download/'} className="underline" target="_blank" rel="noreferrer">
          OpenAI Signals v2.0
        </a>{' '}
        (CC BY 4.0). 개인 계정(Free·Go·Plus·Pro) 메시지 표본 기준이며 기업 계정은 포함되지 않습니다. 차등 프라이버시 노이즈가 적용된 값입니다.
      </p>
    </div>
  )
}

function StatTile({ label, value, detail, trend }: { label: string; value: string; detail: string; trend: number }) {
  const Icon = trend >= 0 ? TrendingUpIcon : TrendingDownIcon
  return (
    <Card>
      <CardHeader className="pb-0">
        <CardDescription>{label}</CardDescription>
        <CardTitle className="text-2xl">{value}</CardTitle>
      </CardHeader>
      <CardContent className="flex items-center gap-1 text-sm text-muted-foreground">
        {trend !== 0 && <Icon className="size-4" aria-hidden />}
        <span>{detail}</span>
      </CardContent>
    </Card>
  )
}
