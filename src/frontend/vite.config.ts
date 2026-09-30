import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The API, as started by `uv run uvicorn app.main:app --port 8000`.
const API_TARGET = 'http://127.0.0.1:8000'

// Proxying /api in dev *and* in preview is what keeps the browser on one origin, so the
// session cookie stays a plain same-site cookie: no CORS, no SameSite=None, no third-party
// cookie rules. `preview` needs it too because the browser tests run against the built app.
const proxy = { '/api': { target: API_TARGET, changeOrigin: true } }

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173, proxy },
  preview: { port: 4173, proxy },
})
