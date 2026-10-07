'use client'

import Link from 'next/link'
import { ChartColumnIcon, ExternalLinkIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import type { Evidence } from './api'

// product도 쓴다 (architecture.md 예외: frontend product → radar)
const SIGNALS_URL = 'https://openai.com/signals/data-download/'

const METRIC_LABEL: Record<Evidence['metric'], string> = {
  topic_share: '대화 주제 비중',
  work_topic_share: '업무 대화 주제 비중',
  work_share: '업무 목적 대화 비중',
  work_intent: '업무 의도 비중',
  usage_rank: '사용량 순위',
}

const formatValue = (e: Evidence, v: number | null) =>
  v === null ? '—' : e.metric === 'usage_rank' ? `${v}위` : `${(v * 100).toFixed(1)}%`

/** "N개 출처" 칩. 누르면 옆 패널에서 지표 값과 원본 링크를 본다. */
export function EvidenceSheet({
  evidence,
  sources = [],
  title,
}: {
  evidence: Evidence[]
  sources?: string[] // 그룹사 공개 자료 URL
  title: string
}) {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm">
          <ChartColumnIcon /> {evidence.length}개 출처
        </Button>
      </SheetTrigger>
      <SheetContent className="w-full overflow-y-auto sm:max-w-md">
        <SheetHeader>
          <SheetTitle>데이터 근거</SheetTitle>
          <SheetDescription>{title}</SheetDescription>
        </SheetHeader>
        <div className="space-y-6 px-4 pb-6 text-sm">
          <ol className="space-y-4">
            {evidence.map((e, i) => (
              <li key={`${i}-${e.metric}-${e.key}-${e.country}`} className="space-y-1">
                <p className="font-medium">{e.label}</p>
                <dl className="grid grid-cols-[5rem_1fr] gap-x-2 gap-y-0.5 text-xs text-muted-foreground">
                  <dt>지표</dt>
                  <dd>
                    {METRIC_LABEL[e.metric]}
                    {e.key && ` · ${e.key}`}
                  </dd>
                  <dt>국가</dt>
                  <dd>{e.country ?? '전 세계'}</dd>
                  <dt>기간</dt>
                  <dd className="tabular-nums">
                    {e.from} → {e.to}
                  </dd>
                  <dt>값</dt>
                  <dd className="tabular-nums">
                    {formatValue(e, e.from_value)} → {formatValue(e, e.to_value)}
                    {e.change_pp !== null && ` (${e.change_pp > 0 ? '+' : ''}${e.change_pp.toFixed(1)}%p)`}
                  </dd>
                </dl>
              </li>
            ))}
          </ol>

          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">원본</p>
            <ul className="space-y-1">
              <li>
                <a href={SIGNALS_URL} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 underline">
                  OpenAI Signals v2.0 (CC BY 4.0) <ExternalLinkIcon className="size-3.5" />
                </a>
              </li>
              <li>
                <Link href="/trends" className="underline">
                  AI 활용 트렌드 화면에서 보기
                </Link>
              </li>
              {sources.map((url, i) => (
                <li key={`${i}-${url}`}>
                  <a href={url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 underline">
                    그룹사 공개 자료 · {url.replace(/^https?:\/\//, '').replace(/\/$/, '')}
                    <ExternalLinkIcon className="size-3.5" />
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
