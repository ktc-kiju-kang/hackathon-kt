import { useEffect, useState } from 'react'
import { api, type Health } from './api/client'

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.health().then(setHealth).catch((e: Error) => setError(e.message))
  }, [])

  return (
    <main className="container">
      <header>
        <h1>KT 해커톤</h1>
        <p className="subtitle">프로젝트 주제 확정 전 기본 화면입니다.</p>
      </header>

      <section className="card">
        <h2>API 상태</h2>
        {error && <p className="error">연결 실패: {error}</p>}
        {!error && !health && <p>확인 중…</p>}
        {health && (
          <p>
            <span className={`badge badge-${health.status}`}>{health.status}</span>{' '}
            {new Date(health.time).toLocaleString('ko-KR')}
          </p>
        )}
      </section>
    </main>
  )
}
