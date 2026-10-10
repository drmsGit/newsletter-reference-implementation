import { QueryClient } from '@tanstack/react-query'

import { HttpError } from './session'

/**
 * Whether a failed read is asked again (task-333).
 *
 * Once, and only when asking again could change the answer: the network
 * failed, or the server had an error of its own (5xx). An answer the server
 * gave on purpose (401, 403, 404, 409, 422, any 4xx) is final; asking twice
 * only delayed the error and doubled every denial in the logs. Decided in the
 * 2026-10-09 interview review (Client Q1).
 */
export function retryOnceUnlessAnswered(failureCount: number, error: unknown): boolean {
  if (error instanceof HttpError && error.status < 500) return false
  return failureCount < 1
}

/**
 * One query client for the application.
 *
 * ADR-173 point 2 chose TanStack Query on a single requirement rather than on
 * ergonomics: ADR-172 resolves the working brand into every query, so changing
 * the working brand must invalidate everything this client has cached. That is
 * `queryClient.invalidateQueries()` in one place, and sixteen chances to forget
 * it if each screen caches for itself.
 */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // The server is the authority on everything here and a manager may have
        // two tabs open. Refetching on focus is the cheap way to stop a stale
        // tab showing a campaign somebody else has since changed.
        refetchOnWindowFocus: true,
        retry: retryOnceUnlessAnswered,
      },
    },
  })
}
