import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, setCsrfToken } from './client'
import type { components } from './schema'

export type SessionContext = components['schemas']['SessionContext']

/** An HTTP failure that kept its status code, so callers can tell 401 apart. */
export class HttpError extends Error {
  constructor(readonly status: number) {
    super(`Request failed with status ${status}`)
  }
}

/**
 * Turn a non-2xx response into a thrown `HttpError`.
 *
 * TanStack Query decides success or failure by whether the function throws, but
 * `fetch` does not throw on a 401 or a 500 -- it resolves with a response that
 * says so. Every call therefore has to make that judgement, and this is the one
 * place that does.
 *
 * It reads `response.ok` rather than the destructured `error` field because
 * routes that declare no error responses type that field as `never`, which
 * narrows the whole result away. `response` is present on every result whatever
 * the schema says.
 */
function throwIfFailed(result: { response: Response }): void {
  if (!result.response.ok) throw new HttpError(result.response.status)
}

/**
 * The cache key for the session.
 *
 * TanStack Query caches by key. Anything asking for `['session']` gets the same
 * cached answer rather than a second request, which is why the shell, the guard
 * and the brand switcher can each call `useSession()` without three round
 * trips.
 */
export const sessionQueryKey = ['session'] as const

async function fetchSession(): Promise<SessionContext> {
  const result = await api.GET('/auth/session')
  throwIfFailed(result)
  const data = result.data as SessionContext

  /**
   * **This line is the reload fix being consumed.**
   *
   * The CSRF token used to be handed over once, in the sign-in response. A
   * browser that reloaded the page still had its session cookie -- the browser
   * keeps that -- but had lost the token, and `httponly` meant it could not
   * derive a new one. Every write then failed until the user signed out and in
   * again. See ADR-168's addendum of 2026-09-20.
   *
   * The shell calls this route on every load anyway, to learn who is signed in
   * and which brand they are working in. Carrying the token on the same
   * response costs no extra request.
   */
  setCsrfToken(data.csrf_token)
  return data
}

/**
 * Who is signed in, which brand they are working in, and which brands they may
 * switch to.
 *
 * `retry: false` because the interesting failure here is 401, which means "not
 * signed in" rather than "something went wrong". Retrying a 401 delays the
 * sign-in screen for no benefit.
 */
export function useSession() {
  return useQuery({
    queryKey: sessionQueryKey,
    queryFn: fetchSession,
    retry: false,
  })
}

/**
 * Step one of signing in: ask for a code.
 *
 * **Answers 202 for every address** -- known, unknown, deactivated, or one whose
 * mail send failed. That is ADR-151 §2, and it is why the screen must not say
 * anything that implies the address was recognised. A UI that said "check your
 * inbox" for a real address and "no such account" for an unknown one would hand
 * an attacker a list of who has an account, which is exactly the property the
 * backend spends a uniform response to protect.
 */
export function useRequestCode() {
  return useMutation({
    mutationFn: async (email: string) => {
      const result = await api.POST('/auth/session/request', { body: { email } })
      throwIfFailed(result)
    },
  })
}

/** Step two: exchange the code for a session cookie. */
export function useVerifyCode() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: { email: string; code: string }) => {
      const result = await api.POST('/auth/session/verify', { body: input })
      throwIfFailed(result)
      return result.data as components['schemas']['SessionVerified']
    },
    onSuccess: (data) => {
      // Usable immediately, before the session query has refetched.
      setCsrfToken(data.csrf_token)
      // Then refetch, because verify does not report the working brand.
      void queryClient.invalidateQueries({ queryKey: sessionQueryKey })
    },
  })
}

/**
 * Change the working brand.
 *
 * **`invalidateQueries()` with no arguments is the point, not laziness.**
 *
 * ADR-172 resolves the working brand once per request and carries it into every
 * query the backend runs. So after a switch, *every* cached answer in this
 * client describes the wrong brand -- campaigns, content, audiences, all of it.
 * Calling `invalidateQueries()` with no key filter marks the whole cache stale
 * and refetches what is on screen.
 *
 * This single requirement is why ADR-173 point 2 chose a cache library at all.
 * Hand-rolled, the equivalent is remembering to clear sixteen screens' state in
 * one handler, with nothing failing when somebody forgets -- and the failure
 * mode is the worst available one: a screen showing another brand's rows under
 * the name of the brand you just switched to.
 *
 * The route answers 204 whether or not the switch was accepted, so there is
 * nothing to read from the response. Re-reading the session is how the client
 * learns where it ended up, which is what the backend's own description says.
 */
export function useSwitchBrand() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (brandId: number) => {
      throwIfFailed(
        await api.POST('/auth/session/brand', { body: { brand_id: brandId } }),
      )
    },
    onSuccess: () => queryClient.invalidateQueries(),
  })
}

/** Sign out. Needs the CSRF header like any other write; the client adds it. */
export function useSignOut() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      throwIfFailed(await api.POST('/auth/session'))
    },
    onSuccess: () => {
      setCsrfToken('')
      queryClient.clear()
    },
  })
}
