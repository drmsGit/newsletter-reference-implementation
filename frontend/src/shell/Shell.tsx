import { useEffect, useState, type CSSProperties } from 'react'
import { LogOut, PanelLeft } from 'lucide-react'
import { Button } from 'react-aria-components'
import { Navigate, Outlet, useNavigate } from 'react-router'

import { useSession, useSignOut } from '../api/session'
import { PRODUCT_NAME } from '../branding'
import BrandSwitcher from './BrandSwitcher'
import Nav, { GoToShortcuts } from './Nav'
import { avatarHue, initials } from './avatar'
import { ShortcutsEntry, ShortcutsProvider } from '../shortcuts/Shortcuts'

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
  const [collapsed, setCollapsed] = useCollapsed()

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

  const user = session.data.user
  const who = user?.display_name || user?.email || ''

  return (
    <ShortcutsProvider>
    <GoToShortcuts />
    <div className="shell" data-nav={collapsed ? 'collapsed' : 'expanded'}>
      {/*
        Column 1 of every screen (docs/design/HANDOFF.md section 3): always
        there, collapsing to an icon rail. The toggle is the first control.
      */}
      <aside className="nav-col">
        <div className="nav-top">
          <span className="nav-name">{PRODUCT_NAME}</span>
          <Button
            className="btn-plain btn-icon nav-toggle"
            aria-label={collapsed ? 'Expand the navigation' : 'Collapse the navigation'}
            aria-expanded={!collapsed}
            onPress={() => setCollapsed(!collapsed)}
          >
            <PanelLeft size={16} strokeWidth={1.75} aria-hidden="true" />
          </Button>
        </div>
        {/*
          The working brand's logo, from its default brand profile, so a manager
          sees which brand they are in (task-356). Only the logo: the app keeps
          one palette and its fonts whatever the brand (ADR-194 point 12, as
          narrowed by the user).
        */}
        {session.data.brand?.logo && (
          <img
            className="shell__logo"
            src={session.data.brand.logo}
            alt={session.data.brand.logo_alt || `${session.data.brand.name} logo`}
          />
        )}
        <BrandSwitcher session={session.data} collapsed={collapsed} onExpand={() => setCollapsed(false)} />
        <Nav />
        <div className="nav-foot">
          {/*
            The signed-in person as their initials avatar (it replaces the email
            shown as text): the display name is its name, the email its hover
            text, the colour a function of the name (HANDOFF section 4).
          */}
          <span
            className="avatar"
            role="img"
            aria-label={who}
            title={user?.email ?? undefined}
            style={{ '--avatar-hue': avatarHue(who) } as CSSProperties}
          >
            {initials(who)}
          </span>
          <ShortcutsEntry />
          <Button
            className="btn-plain nav-foot-action"
            onPress={() =>
              signOut.mutate(undefined, {
                // Same lesson as signing in: clearing the cache changes state,
                // and state does not move a route.
                onSuccess: () => void navigate('/sign-in', { replace: true }),
              })
            }
            isDisabled={signOut.isPending}
          >
            <LogOut size={16} strokeWidth={1.75} aria-hidden="true" />
            <span className="nav-label">Sign out</span>
          </Button>
        </div>
      </aside>
      <main className="shell__main">
        <Outlet />
      </main>
    </div>
    </ShortcutsProvider>
  )
}

const COLLAPSED_KEY = 'nav-collapsed'

/** The navigation's collapse, remembered in this browser: a convenience only, so a
 * browser that refuses storage just starts expanded (or collapsed on a narrow screen). */
function useCollapsed(): [boolean, (value: boolean) => void] {
  const [collapsed, setState] = useState(() => {
    try {
      const stored = window.localStorage.getItem(COLLAPSED_KEY)
      if (stored !== null) return stored === '1'
    } catch {
      // storage refused: fall through
    }
    return typeof window.matchMedia === 'function' && window.matchMedia('(max-width: 800px)').matches
  })
  const set = (value: boolean) => {
    setState(value)
    try {
      window.localStorage.setItem(COLLAPSED_KEY, value ? '1' : '0')
    } catch {
      // storage refused: the choice lasts this page only
    }
  }
  return [collapsed, set]
}
