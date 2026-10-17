import { screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { AutosaveField } from './EditorFields'
import { renderWithProviders } from '../test-utils'

function field(size: string | null) {
  renderWithProviders(
    <AutosaveField field={{ name: 'body', label: 'Body', type: 'richtext', size }} value="" onSave={vi.fn()} error={undefined} />,
  )
  return screen.getByRole('textbox', { name: 'Body' })
}

describe("a text field's height (task-392 item 21)", () => {
  it('opens a long body taller than the others', () => {
    expect(field('long')).toHaveAttribute('rows', '10')
  })

  it.each([['medium'], ['small'], [null]])('keeps a %s field at four rows', (size) => {
    expect(field(size)).toHaveAttribute('rows', '4')
  })
})
