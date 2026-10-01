'use client'

import { useState } from 'react'
import { Activity as ActivityIcon, TrendingDown, TrendingUp, Users, Wallet } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn } from '@/lib/utils'
import { ACTIVITIES, DEPARTMENTS, EMPLOYEES, STATS, type Period } from './data'

const ALL = 'all'
const PERIODS: { value: Period; label: string }[] = [
  { value: 'week', label: '주간' },
  { value: 'month', label: '월간' },
  { value: 'year', label: '연간' },
]

const active = EMPLOYEES.filter((e) => e.status !== '퇴사')
const payroll = active.reduce((sum, e) => sum + e.salary, 0)

const SUMMARY = [
  { label: '재직 인원', value: `${active.length}명`, delta: 4.2, icon: Users },
  { label: '월 인건비', value: `${Math.round(payroll / 12).toLocaleString()}만원`, delta: -1.3, icon: Wallet },
  { label: '오늘 활동', value: `${ACTIVITIES.length * 12}건`, delta: 12.8, icon: ActivityIcon },
]

function BarChart({ data }: { data: { label: string; value: number }[] }) {
  const max = Math.max(...data.map((d) => d.value))
  return (
    <div className="flex h-48 items-end gap-2" role="img" aria-label="막대 차트">
      {data.map((d) => (
        <div key={d.label} className="flex h-full flex-1 flex-col items-center justify-end gap-1">
          <span className="text-xs tabular-nums text-muted-foreground">{d.value}</span>
          <div className="w-full rounded-t bg-primary/80 transition-all" style={{ height: `${(d.value / max) * 100}%` }} />
          <span className="text-xs text-muted-foreground">{d.label}</span>
        </div>
      ))}
    </div>
  )
}

export function DashboardSample() {
  const [period, setPeriod] = useState<Period>('week')
  const [team, setTeam] = useState<string>(ALL)

  const activities = ACTIVITIES.filter((a) => team === ALL || a.team === team)

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        {SUMMARY.map(({ label, value, delta, icon: Icon }) => {
          const up = delta >= 0
          return (
            <Card key={label}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0">
                <CardDescription>{label}</CardDescription>
                <Icon className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tabular-nums">{value}</div>
                <p className={cn('mt-1 flex items-center gap-1 text-xs', up ? 'text-primary' : 'text-destructive')}>
                  {up ? <TrendingUp className="size-3" /> : <TrendingDown className="size-3" />}
                  전월 대비 {up ? '+' : ''}
                  {delta}%
                </p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>처리 건수 추이</CardTitle>
            <CardDescription>기간 탭으로 데이터를 전환합니다 (CSS 막대 차트)</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs value={period} onValueChange={(v) => setPeriod(v as Period)}>
              <TabsList>
                {PERIODS.map((p) => (
                  <TabsTrigger key={p.value} value={p.value}>
                    {p.label}
                  </TabsTrigger>
                ))}
              </TabsList>
              {PERIODS.map((p) => (
                <TabsContent key={p.value} value={p.value} className="pt-4">
                  <BarChart data={STATS[p.value]} />
                </TabsContent>
              ))}
            </Tabs>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-start justify-between gap-2 space-y-0">
            <div>
              <CardTitle>최근 활동</CardTitle>
              <CardDescription>팀별로 필터링</CardDescription>
            </div>
            <Select value={team} onValueChange={setTeam}>
              <SelectTrigger className="w-28" aria-label="팀 필터">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>전체 팀</SelectItem>
                {DEPARTMENTS.map((d) => (
                  <SelectItem key={d} value={d}>
                    {d}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </CardHeader>
          <CardContent>
            {activities.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">해당 팀의 활동이 없습니다.</p>
            ) : (
              <ul className="space-y-3">
                {activities.map((a) => (
                  <li key={a.id} className="flex items-start justify-between gap-2 text-sm">
                    <p>
                      <span className="font-medium">{a.who}</span>
                      님이 <span className="font-medium">{a.target}</span>을(를) {a.action}
                    </p>
                    <div className="flex shrink-0 flex-col items-end gap-1">
                      <Badge variant="secondary">{a.team}</Badge>
                      <span className="text-xs text-muted-foreground">{a.time}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
