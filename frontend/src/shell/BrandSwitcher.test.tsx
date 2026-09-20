import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import BrandSwitcher from './BrandSwitcher'
import { A_SESSION, renderWithProviders } from '../test-utils'

describe('the brand switcher', () => {
  it('is absent entirely when the session is not switchable', () => {
    /**
     * ADR-150 point 4 promises a single-brand company "never has to think about
     * the switcher". Hidden rather than disabled, because a disabled control is
     * still a control somebody has to read and dismiss.
     */
    const oneBrand = {
      ...A_SESSION,
      brand: { ...A_SESSION.brand, switchable: false },
      brands: [{ id: 1, name: 'Acme' }],
    }

    renderWithProviders(<BrandSwitcher session={oneBrand} />)

    expect(screen.queryByLabelText('Brand')).not.toBeInTheDocument()
  })

  it('offers the brands the person may switch to', () => {
    renderWithProviders(<BrandSwitcher session={A_SESSION} />)

    expect(screen.getByLabelText('Brand')).toBeInTheDocument()
    expect(screen.getByRole('button')).toHaveTextContent('Acme')
  })
})
