import { Route, Routes } from 'react-router'
import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import Shell from './Shell'
import { jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

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
})
