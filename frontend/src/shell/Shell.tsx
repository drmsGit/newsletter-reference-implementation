import { useEffect } from 'react'
import { Button } from 'react-aria-components'
import { Navigate, Outlet, useNavigate } from 'react-router'

import { useSession, useSignOut } from '../api/session'
import { PRODUCT_NAME } from '../branding'
import BrandSwitcher from './BrandSwitcher'

/**
 * The frame every signed-in screen sits inside.
 *
 * `useSession()` here does not cause a second request. TanStack Query caches by
 * key, and `RequireSession` has already asked for `['session']` -- both callers
 * read the same cached answer. That is the behaviour a hand-rolled fetch in
 * each component would not have.
 */
export default function Shell() {
  const session = useSession()
  const signOut = useSignOut()
  const navigate = useNavigate()

  // index.html carries a static title for the first paint; this is the real one.
  useEffect(() => {
    document.title = PRODUCT_NAME
  }, [])

  /**
   * **Never render nothing.**
   *
   * This returned `null` until 2026-09-20, and signing out produced a blank
   * white page: the session was gone, so `data` was undefined, so this rendered
   * nothing at all -- and a component returning nothing is indistinguishable
   * from a crash. Signing out now navigates (below), and this is the backstop
   * for every other way the session can vanish, such as it expiring while the
   * tab sat open.
   */
  if (!session.data) return <Navigate to="/sign-in" replace />

  return (
    <div className="shell">
      <header className="shell__bar">
        <span className="shell__brand">{PRODUCT_NAME}</span>
        <BrandSwitcher session={session.data} />
        <span className="shell__user">{session.data.user?.email}</span>
        <Button
          onPress={() =>
            signOut.mutate(undefined, {
              // Same lesson as signing in: clearing the cache changes state,
              // and state does not move a route.
              onSuccess: () => void navigate('/sign-in', { replace: true }),
            })
          }
          isDisabled={signOut.isPending}
        >
          Sign out
        </Button>
      </header>
      <main className="shell__main">
        <Outlet />
      </main>
    </div>
  )
}
