'use client'

import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { RefreshCwIcon } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { getHealth, type Health } from './api'

export function HealthCard() {
  const [health, setHealth] = useState<Health | null>(null)
  const [loading, setLoading] = useState(true)

  // setState는 비동기 콜백에서만 호출 (effect 본문에서 동기 호출 금지 규칙)
  const load = useCallback(
    () =>
      getHealth()
        .then(setHealth)
        .catch((e: Error) => {
          setHealth(null)
          toast.error(`API 연결 실패: ${e.message}`)
        })
        .finally(() => setLoading(false)),
    [],
  )

  const refresh = () => {
    setLoading(true)
    void load()
  }

  useEffect(() => {
    void load()
  }, [load])

  return (
    <Card>
      <CardHeader>
        <CardTitle>API 상태</CardTitle>
        <CardDescription>NEXT_PUBLIC_API_BASE_URL이 비어 있으면 mock 응답을 사용합니다.</CardDescription>
      </CardHeader>
      <CardContent className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-sm">
          {health ? (
            <>
              <Badge variant={health.status === 'ok' ? 'default' : 'secondary'}>
                {health.status}
              </Badge>
              {health.db && (
                <Badge variant={health.db === 'ok' ? 'outline' : 'destructive'}>DB {health.db}</Badge>
              )}
              <span className="text-muted-foreground">
                {new Date(health.time).toLocaleString('ko-KR')}
              </span>
            </>
          ) : (
            <span className="text-muted-foreground">{loading ? '확인 중…' : '응답 없음'}</span>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={refresh} disabled={loading}>
          <RefreshCwIcon className={loading ? 'animate-spin' : ''} />
          다시 확인
        </Button>
      </CardContent>
    </Card>
  )
}
