import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router'
import { render } from '@testing-library/react'
import { vi } from 'vitest'

/**
 * A fresh QueryClient per test.
 *
 * Retries are off because a test that retries a deliberate failure waits for
 * the retry before failing, which turns a clear assertion into a timeout.
 */
export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
}

export function renderWithProviders(
  ui: ReactNode,
  { client = makeQueryClient(), route = '/' } = {},
) {
  return {
    client,
    ...render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
      </QueryClientProvider>,
    ),
  }
}

/**
 * Stub `fetch` with one handler per route.
 *
 * **Deliberately keyed by method and path rather than answering everything the
 * same way.** A blanket mock made the sign-in tests pass while the screen was
 * broken: it answered `GET /auth/session` with a success too, so the screen
 * believed somebody was already signed in and redirected away, and the
 * assertions failed for a reason that had nothing to do with the bug. A mock
 * that cannot tell two routes apart is a mock that can lie about both.
 *
 * An unhandled route throws rather than returning a default, so a test that
 * quietly starts calling something new fails loudly.
 */
export function stubFetch(handlers: Record<string, () => Response>) {
  const mock = vi.fn(async (input: Request | string) => {
    const request = typeof input === 'string' ? new Request(input) : input
    const key = `${request.method} ${new URL(request.url).pathname}`
    const handler = handlers[key]
    if (!handler) throw new Error(`no stub for ${key}`)
    return handler()
  })
  vi.stubGlobal('fetch', mock)
  return mock
}

/** A JSON response, the way `fetch` would give one. */
export function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

export const A_SESSION = {
  user: { id: 1, email: 'manager@example.invalid', display_name: 'A Manager' },
  brand: { id: 1, key: 'acme', name: 'Acme', switchable: true },
  brands: [
    { id: 1, name: 'Acme' },
    { id: 2, name: 'Beta' },
  ],
  csrf_token: 'a-csrf-token',
}
