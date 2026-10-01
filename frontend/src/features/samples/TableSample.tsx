'use client'

import { useMemo, useState } from 'react'
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, Search } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { cn } from '@/lib/utils'
import { DEPARTMENTS, EMPLOYEES, STATUSES, type Employee, type Status } from './data'

const PAGE_SIZE = 10
const ALL = 'all'

type SortKey = 'name' | 'department' | 'role' | 'salary' | 'joinedAt'

const COLUMNS: { key: SortKey; label: string; className?: string }[] = [
  { key: 'name', label: '이름' },
  { key: 'department', label: '부서' },
  { key: 'role', label: '직급' },
  { key: 'salary', label: '연봉(만원)', className: 'text-right' },
  { key: 'joinedAt', label: '입사일' },
]

const STATUS_STYLE: Record<Status, string> = {
  재직: 'bg-primary/15 text-primary',
  휴직: 'bg-destructive/10 text-destructive',
  출장: 'bg-accent text-accent-foreground',
  퇴사: 'bg-muted text-muted-foreground',
}

export function TableSample() {
  const [query, setQuery] = useState('')
  const [dept, setDept] = useState<string>(ALL)
  const [status, setStatus] = useState<string>(ALL)
  const [sort, setSort] = useState<{ key: SortKey; dir: 'asc' | 'desc' }>({ key: 'name', dir: 'asc' })
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<Set<number>>(new Set())

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase()
    const filtered = EMPLOYEES.filter(
      (e) =>
        (dept === ALL || e.department === dept) &&
        (status === ALL || e.status === status) &&
        (!q || e.name.toLowerCase().includes(q) || e.email.toLowerCase().includes(q)),
    )
    const sign = sort.dir === 'asc' ? 1 : -1
    return [...filtered].sort((a, b) => {
      const x = a[sort.key]
      const y = b[sort.key]
      return (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y), 'ko')) * sign
    })
  }, [query, dept, status, sort])

  const pageCount = Math.max(1, Math.ceil(rows.length / PAGE_SIZE))
  const current = Math.min(page, pageCount)
  const visible = rows.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE)
  const allChecked = visible.length > 0 && visible.every((e) => selected.has(e.id))

  // 필터가 바뀌면 첫 페이지로 (effect 대신 핸들러에서 처리)
  const filterChange = (fn: () => void) => {
    fn()
    setPage(1)
  }

  const toggleSort = (key: SortKey) =>
    setSort((s) => (s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'asc' }))

  const toggleRow = (e: Employee, on: boolean) =>
    setSelected((prev) => {
      const next = new Set(prev)
      if (on) next.add(e.id)
      else next.delete(e.id)
      return next
    })

  const togglePage = (on: boolean) =>
    setSelected((prev) => {
      const next = new Set(prev)
      visible.forEach((e) => (on ? next.add(e.id) : next.delete(e.id)))
      return next
    })

  return (
    <Card>
      <CardHeader>
        <CardTitle>직원 목록</CardTitle>
        <CardDescription>검색·필터·정렬·페이지네이션·행 선택을 갖춘 테이블 샘플 (mock 50건)</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-52 flex-1">
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => filterChange(() => setQuery(e.target.value))}
              placeholder="이름·이메일 검색"
              aria-label="검색"
              className="pl-9"
            />
          </div>
          <Select value={dept} onValueChange={(v) => filterChange(() => setDept(v))}>
            <SelectTrigger className="w-32" aria-label="부서 필터">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>전체 부서</SelectItem>
              {DEPARTMENTS.map((d) => (
                <SelectItem key={d} value={d}>
                  {d}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={status} onValueChange={(v) => filterChange(() => setStatus(v))}>
            <SelectTrigger className="w-32" aria-label="상태 필터">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>전체 상태</SelectItem>
              {STATUSES.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-10">
                  <Checkbox checked={allChecked} onCheckedChange={(v) => togglePage(v === true)} aria-label="현재 페이지 전체 선택" />
                </TableHead>
                {COLUMNS.map((c) => {
                  const Icon = sort.key !== c.key ? ArrowUpDown : sort.dir === 'asc' ? ArrowUp : ArrowDown
                  return (
                    <TableHead key={c.key} className={c.className} aria-sort={sort.key === c.key ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none'}>
                      <Button variant="ghost" size="sm" className="-mx-2" onClick={() => toggleSort(c.key)}>
                        {c.label}
                        <Icon className={cn('size-3.5', sort.key !== c.key && 'opacity-40')} />
                      </Button>
                    </TableHead>
                  )
                })}
                <TableHead>상태</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={COLUMNS.length + 2} className="h-24 text-center text-muted-foreground">
                    조건에 맞는 직원이 없습니다.
                  </TableCell>
                </TableRow>
              ) : (
                visible.map((e) => (
                  <TableRow key={e.id} data-state={selected.has(e.id) ? 'selected' : undefined}>
                    <TableCell>
                      <Checkbox checked={selected.has(e.id)} onCheckedChange={(v) => toggleRow(e, v === true)} aria-label={`${e.name} 선택`} />
                    </TableCell>
                    <TableCell>
                      <div className="font-medium">{e.name}</div>
                      <div className="text-xs text-muted-foreground">{e.email}</div>
                    </TableCell>
                    <TableCell>{e.department}</TableCell>
                    <TableCell>{e.role}</TableCell>
                    <TableCell className="text-right tabular-nums">{e.salary.toLocaleString()}</TableCell>
                    <TableCell className="tabular-nums">{e.joinedAt}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={cn('border-0', STATUS_STYLE[e.status])}>
                        {e.status}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground">
          <span>
            총 {rows.length}건 중 {selected.size}건 선택
          </span>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" aria-label="이전 페이지" disabled={current <= 1} onClick={() => setPage(current - 1)}>
              <ChevronLeft />
            </Button>
            <span className="tabular-nums">
              {current} / {pageCount}
            </span>
            <Button variant="outline" size="icon" aria-label="다음 페이지" disabled={current >= pageCount} onClick={() => setPage(current + 1)}>
              <ChevronRight />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
