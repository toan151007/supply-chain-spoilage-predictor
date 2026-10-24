import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Dev server runs on port 3000 (see AGENTS.md) and proxies every /api call
// to the FastAPI backend, so the browser sees a single origin and CORS is
// never involved during development.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
