import { Route, Routes } from 'react-router'
import { fireEvent, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import Shell from './Shell'
import { sessionQueryKey } from '../api/session'
import { A_SESSION, jsonResponse, makeQueryClient, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

describe('the shell', () => {
  it('never renders a blank page when the session is gone', async () => {
    /**
     * **The second bug found by driving the real app, and the same shape as the
     * first.** Signing out cleared the cache, so `session.data` became
     * undefined, so the shell returned `null` -- a white page with no
     * explanation, indistinguishable from a crash. A component that renders
     * nothing is never the right answer to "we do not know who you are".
     */
    stubFetch({
      'GET /auth/session': () => jsonResponse({ detail: 'Authentication required' }, 401),
    })

    renderWithProviders(
      <Routes>
        <Route path="/" element={<Shell />} />
        <Route path="/sign-in" element={<p>sign in</p>} />
      </Routes>,
    )

    expect(await screen.findByText('sign in')).toBeInTheDocument()
  })

  it("shows the working brand's logo from its default profile, and none without one", async () => {
    // As RequireSession leaves it: the session already read.
    const shellWith = (logo: string | null) => {
      const client = makeQueryClient()
      client.setQueryData(sessionQueryKey, {
        ...A_SESSION,
        brand: { ...A_SESSION.brand, logo, logo_alt: logo ? 'Acme shop' : null },
      })
      return renderWithProviders(
        <Routes>
          <Route path="/" element={<Shell />} />
        </Routes>,
        { client },
      )
    }
    stubFetch({ 'GET /auth/session': () => jsonResponse(A_SESSION) })
    const first = shellWith('https://cdn.example.test/acme.png')
    expect(await screen.findByRole('img', { name: 'Acme shop' })).toHaveAttribute(
      'src',
      'https://cdn.example.test/acme.png',
    )
    first.unmount()

    shellWith(null)
    // The person is their avatar now (task-372): the display name is its name, the email its hover text.
    const avatar = await screen.findByRole('img', { name: A_SESSION.user.display_name })
    expect(avatar).toHaveAttribute('title', A_SESSION.user.email)
    expect(screen.queryByRole('img', { name: 'Acme shop' })).not.toBeInTheDocument()
  })

  it('offers the shortcut overview from the navigation foot, above Sign out (task-392 item 19)', async () => {
    const client = makeQueryClient()
    client.setQueryData(sessionQueryKey, A_SESSION)
    stubFetch({ 'GET /auth/session': () => jsonResponse(A_SESSION) })
    renderWithProviders(
      <Routes>
        <Route path="/" element={<Shell />} />
      </Routes>,
      { client },
    )
    const entry = await screen.findByRole('button', { name: 'Keyboard shortcuts' })
    const signOut = screen.getByRole('button', { name: /Sign out/ })
    expect(entry.compareDocumentPosition(signOut) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    fireEvent.click(entry)
    expect(await screen.findByRole('dialog', { name: 'Keyboard shortcuts' })).toBeInTheDocument()
  })

  it('collapses to a rail that keeps every name, and remembers it', async () => {
    const client = makeQueryClient()
    client.setQueryData(sessionQueryKey, A_SESSION)
    stubFetch({ 'GET /auth/session': () => jsonResponse(A_SESSION) })
    window.localStorage.removeItem('nav-collapsed')
    const { unmount } = renderWithProviders(
      <Routes>
        <Route path="/" element={<Shell />} />
      </Routes>,
      { client },
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Collapse the navigation' }))
    // Hidden from sight, never removed: the links and Sign out keep their names in the rail.
    expect(screen.getByRole('link', { name: /Campaigns/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Sign out/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Keyboard shortcuts' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Brand: Acme/ })).toBeInTheDocument()
    expect(window.localStorage.getItem('nav-collapsed')).toBe('1')
    unmount()

    renderWithProviders(
      <Routes>
        <Route path="/" element={<Shell />} />
      </Routes>,
      { client },
    )
    expect(await screen.findByRole('button', { name: 'Expand the navigation' })).toBeInTheDocument()
    window.localStorage.removeItem('nav-collapsed')
  })
})
