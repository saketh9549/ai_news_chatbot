import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/chat': 'http://127.0.0.1:5000',
      '/sources': 'http://127.0.0.1:5000',
      '/ingest': 'http://127.0.0.1:5000',
      '/articles': 'http://127.0.0.1:5000',
      '/health': 'http://127.0.0.1:5000',
    },
  },
})
