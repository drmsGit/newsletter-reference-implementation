import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import App from './App'
import './index.css'

/**
 * One query client for the application.
 *
 * ADR-173 point 2 chose TanStack Query on a single requirement rather than on
 * ergonomics: ADR-172 resolves the working brand into every query, so changing
 * the working brand must invalidate everything this client has cached. That is
 * `queryClient.invalidateQueries()` in one place, and sixteen chances to forget
 * it if each screen caches for itself.
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // The server is the authority on everything here and a manager may have
      // two tabs open. Refetching on focus is the cheap way to stop a stale
      // tab showing a campaign somebody else has since changed.
      refetchOnWindowFocus: true,
      retry: 1,
    },
  },
})

const root = document.getElementById('root')
if (!root) throw new Error('index.html is missing #root')

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
