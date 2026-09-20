import type { ReactNode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { currentCsrfToken, setCsrfToken } from './client'
import { useSession, useSwitchBrand } from './session'
import { A_SESSION, jsonResponse, makeQueryClient } from '../test-utils'

function wrapper(client: ReturnType<typeof makeQueryClient>) {
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
}

beforeEach(() => setCsrfToken(''))
afterEach(() => vi.unstubAllGlobals())

describe('reading the session', () => {
  it('takes the CSRF token from the response, which is what survives a reload', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(A_SESSION)))
    const client = makeQueryClient()

    const { result } = renderHook(() => useSession(), { wrapper: wrapper(client) })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    // Before ADR-168's 2026-09-20 addendum the only source was the sign-in
    // response, so a reloaded page had a session it could not write with.
    expect(currentCsrfToken()).toBe('a-csrf-token')
  })

  it('surfaces a 401 as an HttpError carrying the status', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'Authentication required' }, 401)),
    )
    const client = makeQueryClient()

    const { result } = renderHook(() => useSession(), { wrapper: wrapper(client) })
    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toMatchObject({ status: 401 })
  })
})

describe('switching the working brand', () => {
  /**
   * **This is the assertion ADR-173 point 2's whole justification rests on.**
   *
   * TanStack Query was chosen over a hand-rolled fetch for one reason: ADR-172
   * carries the working brand into every query the backend runs, so after a
   * switch every cached answer describes the wrong brand. If this stops calling
   * `invalidateQueries`, the app shows one brand's rows under another brand's
   * name -- and nothing else in the suite would notice.
   */
  it('invalidates the entire cache, not just the session', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })))
    const client = makeQueryClient()
    const invalidate = vi.spyOn(client, 'invalidateQueries')

    const { result } = renderHook(() => useSwitchBrand(), { wrapper: wrapper(client) })
    result.current.mutate(2)
    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(invalidate).toHaveBeenCalledTimes(1)
    // No argument means every key. A filter here would be a list somebody has
    // to maintain as screens are added, and forgetting one is silent.
    expect(invalidate).toHaveBeenCalledWith()
  })
})
