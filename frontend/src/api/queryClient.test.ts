import { describe, expect, it } from 'vitest'

import { HttpError } from './session'
import { createQueryClient, retryOnceUnlessAnswered } from './queryClient'

/**
 * A read the server refused is not retried (task-333).
 *
 * Every query retried once on any error, so a 403, 404 or 409 was asked twice:
 * repeating it cannot change the answer, the error showed later, and logs saw
 * doubled denials. Decided 2026-10-09 (interview review, Client Q1): retry only
 * a network failure or a server error.
 */
describe('which failed reads are retried', () => {
  it.each([401, 403, 404, 409, 422, 429])('never a %i — the server answered', (status) => {
    expect(retryOnceUnlessAnswered(0, new HttpError(status))).toBe(false)
  })

  it.each([500, 502, 503])('once for a %i', (status) => {
    expect(retryOnceUnlessAnswered(0, new HttpError(status))).toBe(true)
    expect(retryOnceUnlessAnswered(1, new HttpError(status))).toBe(false)
  })

  it('once when the network failed', () => {
    expect(retryOnceUnlessAnswered(0, new TypeError('Failed to fetch'))).toBe(true)
    expect(retryOnceUnlessAnswered(1, new TypeError('Failed to fetch'))).toBe(false)
  })
})

describe('the application query client', () => {
  async function calls(error: Error) {
    let count = 0
    const client = createQueryClient()
    await client
      .fetchQuery({
        queryKey: ['t', Math.random()],
        queryFn: () => {
          count += 1
          throw error
        },
        retryDelay: 0,
      })
      .catch(() => undefined)
    return count
  }

  it('asks a refused read once', async () => {
    expect(await calls(new HttpError(403))).toBe(1)
  })

  it('asks a server error twice', async () => {
    expect(await calls(new HttpError(500))).toBe(2)
  })
})
