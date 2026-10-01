import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { RefreshCwIcon } from 'lucide-react'
import { api, type Health } from '@/api/client'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Toaster } from '@/components/ui/sonner'

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [loading, setLoading] = useState(false)

  const check = useCallback(async () => {
    setLoading(true)
    try {
      setHealth(await api.health())
    } catch (e) {
      setHealth(null)
      toast.error(`API 연결 실패: ${(e as Error).message}`)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void check()
  }, [check])

  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">KT 해커톤</h1>
        <p className="mt-2 text-muted-foreground">프로젝트 주제 확정 전 기본 화면입니다.</p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>API 상태</CardTitle>
          <CardDescription>
            VITE_API_BASE_URL이 비어 있으면 mock 응답을 사용합니다.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-sm">
            {health ? (
              <>
                <Badge variant={health.status === 'ok' ? 'default' : 'secondary'}>
                  {health.status}
                </Badge>
                <span className="text-muted-foreground">
                  {new Date(health.time).toLocaleString('ko-KR')}
                </span>
              </>
            ) : (
              <span className="text-muted-foreground">{loading ? '확인 중…' : '응답 없음'}</span>
            )}
          </div>
          <Button variant="outline" size="sm" onClick={check} disabled={loading}>
            <RefreshCwIcon className={loading ? 'animate-spin' : ''} />
            다시 확인
          </Button>
        </CardContent>
      </Card>

      <Toaster richColors />
    </main>
  )
}
