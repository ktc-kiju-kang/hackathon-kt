import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// GitHub Pages(https://kiju-kang.github.io/hackathon-kt/)에 배포되므로 빌드 시 base 경로 지정
export default defineConfig(({ command }) => ({
  plugins: [react(), tailwindcss()],
  base: command === 'build' ? '/hackathon-kt/' : '/',
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
}))
