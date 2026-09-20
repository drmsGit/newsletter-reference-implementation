import type { ReactNode } from 'react'

import { HttpError } from '../api/session'

/**
 * The three states every screen in this client has, in one place.
 *
 * ADR-170's Negative books "data loading, pending and error states" as the cost
 * of choosing a plain React application -- written by hand, per screen. This is
 * that cost paid once instead of seven times, which also makes the three states
 * consistent rather than however each screen's author felt that day.
 */
export default function ScreenState({
  query,
  children,
}: {
  query: { isPending: boolean; error: unknown }
  children: ReactNode
}) {
  if (query.isPending) return <p className="muted">Loading…</p>

  if (query.error) {
    const status = query.error instanceof HttpError ? query.error.status : undefined

    /**
     * 403 is told apart from everything else deliberately.
     *
     * The backend refuses a permission the signed-in person does not hold, and
     * that is not a failure -- it is an answer. Showing "something went wrong"
     * would invite somebody to retry a request that will never succeed, and
     * would hide the one fact that explains it.
     */
    if (status === 403) {
      return (
        <p role="alert">
          You do not have permission to see this. Ask an administrator if you
          think you should.
        </p>
      )
    }
    if (status === 404) return <p role="alert">That record does not exist.</p>

    return <p role="alert">Could not load this. The server may be unavailable.</p>
  }

  return <>{children}</>
}
