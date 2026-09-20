import type { ReactNode } from 'react'
import { Navigate } from 'react-router'

import { HttpError, useSession } from '../api/session'

/**
 * Let the children render only if somebody is signed in.
 *
 * **The signal is a 401 from `GET /auth/session`**, verified against the running
 * backend rather than assumed. The client holds no opinion about whether it is
 * signed in: the session cookie is `httponly`, so JavaScript cannot see it, and
 * asking the server is the only honest way to find out. That is a feature --
 * a client that decided for itself would be guessing at an answer the server
 * owns, and would disagree the moment a session was revoked.
 *
 * Any other failure is left to surface rather than redirected, because sending
 * somebody to a sign-in screen because the server returned a 500 tells them the
 * wrong thing about what went wrong.
 */
export default function RequireSession({ children }: { children: ReactNode }) {
  const session = useSession()

  if (session.isPending) return <p>Loading…</p>

  if (session.error) {
    if (session.error instanceof HttpError && session.error.status === 401) {
      return <Navigate to="/sign-in" replace />
    }
    return <p role="alert">Could not reach the server.</p>
  }

  return <>{children}</>
}
