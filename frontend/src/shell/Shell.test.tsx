import { Route, Routes } from 'react-router'
import { screen } from '@testing-library/react'
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
    expect(await screen.findByText(A_SESSION.user.email)).toBeInTheDocument()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })
})
