import { screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import RequireSession from './RequireSession'
import { A_SESSION, jsonResponse, renderWithProviders } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

describe('the session guard', () => {
  it('renders its children when somebody is signed in', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(A_SESSION)))

    renderWithProviders(<RequireSession>
      <p>protected</p>
    </RequireSession>)

    expect(await screen.findByText('protected')).toBeInTheDocument()
  })

  it('does not render its children on a 401', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({}, 401)))

    renderWithProviders(<RequireSession>
      <p>protected</p>
    </RequireSession>)

    await waitFor(() => expect(screen.queryByText('protected')).not.toBeInTheDocument())
  })

  it('does not send somebody to sign in because the server broke', async () => {
    /**
     * A 500 is not "you are signed out". Redirecting on any failure would tell
     * the user the wrong thing about what went wrong, and would loop if the
     * sign-in screen also needed the server.
     */
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({}, 500)))

    renderWithProviders(<RequireSession>
      <p>protected</p>
    </RequireSession>)

    expect(await screen.findByRole('alert')).toHaveTextContent('Could not reach the server')
  })
})
