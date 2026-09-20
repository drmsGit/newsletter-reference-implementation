import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { api, currentCsrfToken, setCsrfToken } from './client'
import { jsonResponse } from '../test-utils'

describe('the CSRF header', () => {
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    fetchMock = vi.fn().mockResolvedValue(jsonResponse({}))
    vi.stubGlobal('fetch', fetchMock)
    setCsrfToken('a-csrf-token')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    setCsrfToken('')
  })

  it('is attached to writes', async () => {
    await api.POST('/auth/session/brand', { body: { brand_id: 2 } })

    const request = fetchMock.mock.calls[0][0] as Request
    expect(request.headers.get('X-CSRF-Token')).toBe('a-csrf-token')
  })

  it('is not attached to reads, matching enforce_api_csrf', async () => {
    await api.GET('/auth/session')

    const request = fetchMock.mock.calls[0][0] as Request
    expect(request.headers.get('X-CSRF-Token')).toBeNull()
  })

  it('sends requests to the page origin, never an absolute backend URL', async () => {
    await api.GET('/auth/session')

    const request = fetchMock.mock.calls[0][0] as Request
    // ADR-168 point 3: same-origin is a deployment requirement. An absolute URL
    // here would need samesite=none and a CORS policy.
    expect(new URL(request.url).origin).toBe(window.location.origin)
  })

  it('exposes the token it was given', () => {
    expect(currentCsrfToken()).toBe('a-csrf-token')
  })
})
