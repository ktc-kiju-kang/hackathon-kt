import type { GithubStatus } from './api'
import { CHECKS, Link, ToneIcon } from './charts'
import { elapsedMs, formatElapsed, formatKst } from './prAge'

/** "열린 PR" 목록의 한 줄. REQ-02(24시간 넘은 PR 강조)가 이 줄 위에 얹힌다. */
export function PullRow({ pull: p, now }: { pull: GithubStatus['pulls'][number]; now: Date }) {
  const c = CHECKS[p.checks]
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
          열린 지 {formatElapsed(elapsedMs(p.opened_at, now))} · 업데이트 {formatKst(p.updated_at)}
        </div>
      </div>
      <span className={p.checks === 'fail' ? 'text-sm text-destructive' : 'text-sm text-muted-foreground'}>
        CI {c.label}
      </span>
    </li>
  )
}
