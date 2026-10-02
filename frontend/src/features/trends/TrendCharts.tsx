'use client'

import { Bar, BarChart, CartesianGrid, Cell, LabelList, Line, LineChart, ReferenceLine, XAxis, YAxis } from 'recharts'
import {
  type ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart'
import { cn } from '@/lib/utils'
import type { TopicChange } from './api'
import { TOPIC_LABEL, signedPp } from './labels'

// 차트 색: dataviz 검증 팔레트 (3색 categorical + 증가/감소 diverging). 이 기능 영역 안에서만 쓴다.
// 범주 3색 이하에서 CVD·정상 시야 분리가 검증됨. 색만으로 구분하지 않게 범례(이름)를 항상 함께 둔다.
export const CHART_COLORS = cn(
  '[--series-1:#2a78d6] [--series-2:#eb6834] [--series-3:#1baf7a] [--up:#2a78d6] [--down:#e34948]',
  'dark:[--series-1:#3987e5] dark:[--series-2:#d95926] dark:[--series-3:#199e70] dark:[--up:#3987e5] dark:[--down:#e66767]',
)

export type LinePoint = { month: string } & Record<string, number | string>

function percentFormatter(config: ChartConfig) {
  function PercentRow(value: unknown, name: unknown, item: { color?: string }) {
    return (
      <div className="flex w-full items-center gap-2">
        <span className="size-2.5 shrink-0 rounded-[2px]" style={{ background: item.color }} />
        <span className="flex-1 text-muted-foreground">{config[String(name)]?.label ?? String(name)}</span>
        <span className="font-mono font-medium tabular-nums text-foreground">{Number(value).toFixed(1)}%</span>
      </div>
    )
  }
  return PercentRow
}

export function ShareLineChart({
  data,
  config,
  className,
}: {
  data: LinePoint[]
  config: ChartConfig // key = 데이터 필드, label = 계열 이름, color = var(--series-N)
  className?: string
}) {
  const keys = Object.keys(config)
  return (
    <ChartContainer config={config} className={cn('aspect-auto h-64 w-full', className)}>
      <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} accessibilityLayer>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="month" tickLine={false} axisLine={false} minTickGap={32} tickMargin={8} />
        <YAxis tickLine={false} axisLine={false} width={40} tickFormatter={(v: number) => `${v}%`} />
        <ChartTooltip content={<ChartTooltipContent formatter={percentFormatter(config)} />} />
        <ChartLegend verticalAlign="top" content={<ChartLegendContent className="justify-end pt-0 pb-3" />} />
        {keys.map((key) => (
          <Line
            key={key}
            dataKey={key}
            type="monotone"
            stroke={`var(--color-${key})`}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ChartContainer>
  )
}

const changeConfig = { change_pp: { label: '변화' } } satisfies ChartConfig

export function TopicChangeChart({ rows }: { rows: TopicChange[] }) {
  const data = rows.map((r) => ({ ...r, label: TOPIC_LABEL[r.topic] }))
  return (
    <ChartContainer config={changeConfig} className="aspect-auto h-72 w-full">
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 56, bottom: 0, left: 0 }} accessibilityLayer>
        <CartesianGrid horizontal={false} />
        <XAxis type="number" tickLine={false} axisLine={false} tickFormatter={(v: number) => `${v}%p`} />
        <YAxis type="category" dataKey="label" tickLine={false} axisLine={false} width={80} />
        <ReferenceLine x={0} className="stroke-border" />
        <ChartTooltip
          cursor={false}
          content={
            <ChartTooltipContent
              hideIndicator
              formatter={(_value, _name, item) => {
                const r = item.payload as TopicChange & { label: string }
                return (
                  <div className="grid gap-1">
                    <span className="font-medium">{r.label}</span>
                    <span className="tabular-nums text-muted-foreground">
                      {(r.from_share * 100).toFixed(1)}% → {(r.to_share * 100).toFixed(1)}% ({signedPp(r.change_pp)})
                    </span>
                  </div>
                )
              }}
            />
          }
        />
        <Bar dataKey="change_pp" radius={4} barSize={16} isAnimationActive={false}>
          {data.map((r) => (
            <Cell key={r.topic} fill={r.change_pp >= 0 ? 'var(--up)' : 'var(--down)'} />
          ))}
          <LabelList
            dataKey="change_pp"
            position="right"
            className="fill-foreground"
            formatter={(v: unknown) => signedPp(Number(v))}
          />
        </Bar>
      </BarChart>
    </ChartContainer>
  )
}
