// 상단 배너 테마 토글의 순수 로직. 저장·시스템 설정 폴백은 next-themes(0.4.x)가 한다:
// localStorage 읽기·쓰기를 try/catch로 감싸고, 못 읽으면 defaultTheme="system"으로 동작.
// 실제 브라우저 확인(저장소가 예외를 던질 때 포함)은 Issue #110 댓글에 기록.
export type Mode = 'light' | 'dark'

/** 지금 보이는 테마(resolvedTheme, 시스템 설정 반영)의 반대. 아직 모르면(첫 렌더) 다크로. */
export function nextMode(resolved: string | undefined): Mode {
  return resolved === 'dark' ? 'light' : 'dark'
}

/** 토글의 접근 가능한 이름 = 누르면 일어나는 일. */
export function toggleLabel(resolved: string | undefined): string {
  return nextMode(resolved) === 'dark' ? '다크 모드로 전환' : '라이트 모드로 전환'
}
