import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'

import App from './App'

/**
 * A smoke test, and it is honest about being one.
 *
 * It asserts that the router, the component tree and the test harness agree
 * enough to produce a DOM. That is worth having on the first commit -- a
 * toolchain that cannot render anything fails here rather than on the first
 * real screen -- and it is worth replacing once there is a screen with
 * behaviour to assert.
 */
it('renders the application shell', () => {
  render(
    <MemoryRouter>
      <App />
    </MemoryRouter>,
  )

  expect(screen.getByRole('heading', { name: 'Newsletter Manager' })).toBeInTheDocument()
})
