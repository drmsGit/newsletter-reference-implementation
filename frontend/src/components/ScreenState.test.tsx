import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import ScreenState from './ScreenState'
import { HttpError } from '../api/session'
import { renderWithProviders } from '../test-utils'

describe('screen states', () => {
  it('shows the children once the query has succeeded', () => {
    renderWithProviders(
      <ScreenState query={{ isPending: false, error: null }}>
        <p>the data</p>
      </ScreenState>,
    )
    expect(screen.getByText('the data')).toBeInTheDocument()
  })

  it('tells a refusal apart from a failure', () => {
    /**
     * **403 is an answer, not a breakage.**
     *
     * The backend refuses a permission the signed-in person does not hold.
     * Showing "something went wrong" would invite somebody to retry a request
     * that can never succeed, and would hide the one fact that explains it.
     */
    renderWithProviders(
      <ScreenState query={{ isPending: false, error: new HttpError(403) }}>
        <p>the data</p>
      </ScreenState>,
    )

    expect(screen.getByRole('alert')).toHaveTextContent(/do not have permission/i)
    expect(screen.queryByText(/server may be unavailable/i)).not.toBeInTheDocument()
  })

  it('reports an unexpected status as a failure', () => {
    renderWithProviders(
      <ScreenState query={{ isPending: false, error: new HttpError(500) }}>
        <p>the data</p>
      </ScreenState>,
    )
    expect(screen.getByRole('alert')).toHaveTextContent(/server may be unavailable/i)
  })
})
