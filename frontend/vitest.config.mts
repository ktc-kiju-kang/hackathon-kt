import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitest/config'

// 단위 테스트 설정. 화면(React) 테스트가 아니라 순수 로직(lib·features의 api.ts 등)을 node 환경에서 돌린다.
export default defineConfig({
  resolve: {
    // tsconfig 의 "@/*" 별칭과 같게
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
})
