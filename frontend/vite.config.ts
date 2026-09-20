/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * The backend in development. ADR-168 point 3 makes same-origin a deployment
 * requirement rather than a preference: it is what keeps the session cookie at
 * `samesite="lax"` and keeps CORSMiddleware out of the backend entirely.
 *
 * In production FastAPI serves this app's build output, so there is one origin
 * by construction. In development there are two processes, so Vite proxies the
 * API instead — which gives the browser one origin and preserves the same
 * property. A `localhost:5173` page calling `localhost:8000` directly would be
 * cross-origin, and would need exactly the two controls ADR-168 exists to avoid.
 */
const BACKEND = 'http://127.0.0.1:8000'

/**
 * Every path the backend owns, listed rather than inferred.
 *
 * Derived from the registered routers, not written from memory — `/api` is the
 * odd one out, because the audience router alone mounts at
 * `/api/audience-groups` while every other router sits at a bare top-level
 * prefix. A wildcard rule would have been shorter and would have swallowed
 * Vite's own dev routes; an inferred list would have missed audience entirely.
 */
const API_PREFIXES = [
  '/api',
  '/approvals',
  '/auth',
  '/campaigns',
  '/content',
  '/decision',
  '/delivery',
  '/docs',
  '/insight',
  '/modules',
  '/openapi.json',
  '/overrides',
  '/provider',
  '/recipients',
  '/redoc',
  '/rendering',
  '/snapshots',
  '/ui',
]

/**
 * The path the client is served from.
 *
 * FastAPI mounts the built client under `/manager` because the Jinja UI still
 * owns `/` (see `backend/main.py`). Vite has to know, or the built index would
 * ask for `/assets/...` when the files are at `/manager/assets/...`.
 *
 * The dev server honours it too, so development and production have the same
 * shape of URL: http://localhost:5173/manager/ rather than http://localhost:5173/.
 *
 * **When `backend/app/frontend/router.py` is deleted, this becomes '/'** -- here,
 * in `main.tsx`'s router basename, and in `SPA_MOUNT` in `backend/main.py`.
 */
const BASE = '/manager/'

export default defineConfig({
  base: BASE,
  plugins: [react()],
  test: {
    // A browser-like DOM in Node. React Testing Library renders into it, so
    // a component test exercises the real render path rather than a mock.
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
  },
  server: {
    port: 5173,
    proxy: Object.fromEntries(
      API_PREFIXES.map((prefix) => [
        prefix,
        {
          target: BACKEND,
          // Keep the Host header. The session cookie is issued for the host the
          // browser thinks it is talking to, and rewriting it here would hand
          // the browser a cookie it will not send back.
          changeOrigin: false,
        },
      ]),
    ),
  },
})
