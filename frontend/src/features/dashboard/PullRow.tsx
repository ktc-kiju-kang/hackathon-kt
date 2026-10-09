import { TriangleAlertIcon } from 'lucide-react'
import type { GithubStatus } from './api'
import { CHECKS, Link, ToneIcon } from './charts'
import { elapsedMs, formatElapsed, formatKst, isStale } from './prAge'

/** "열린 PR" 목록의 한 줄. 24시간 넘게 열린 PR은 경고 아이콘 + 문구로 구별한다 (REQ-02, 색만으로 구별하지 않음). */
export function PullRow({ pull: p, now }: { pull: GithubStatus['pulls'][number]; now: Date }) {
  const c = CHECKS[p.checks]
  const age = elapsedMs(p.opened_at, now)
  return (
    <li className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
      <ToneIcon tone={c.tone} running={c.running} className="mt-0.5" />
      <div className="min-w-0 flex-1">
        <Link href={p.url}>
          <span className="truncate">
            #{p.number} {p.title}
          </span>
        </Link>
        <div className="text-[13px] text-muted-foreground">
          {p.author} · {p.branch}
          {p.draft && ' · 초안'}
        </div>
        <div className="text-[13px] text-muted-foreground tabular-nums">
          열린 지 {formatElapsed(age)} · 업데이트 {formatKst(p.updated_at)}
        </div>
        {isStale(age) && (
          <div className="mt-0.5 flex items-center gap-1.5 text-[13px] font-medium text-foreground">
            <TriangleAlertIcon className="size-4 shrink-0 text-[var(--chart-2)]" aria-hidden />
            24시간 넘음
          </div>
        )}
      </div>
      <span className={p.checks === 'fail' ? 'text-sm text-destructive' : 'text-sm text-muted-foreground'}>
        CI {c.label}
      </span>
    </li>
  )
}
