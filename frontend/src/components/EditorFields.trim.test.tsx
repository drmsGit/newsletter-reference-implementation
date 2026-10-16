import { fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'

import { AutosaveField } from './EditorFields'

/** A store that trims what it keeps, as the envelope and content saves do. */
function Trimming({ start = '' }: { start?: string }) {
  const [value, setValue] = useState(start)
  return (
    <AutosaveField
      field={{ name: 'subject', label: 'Subject', type: 'text' }}
      value={value}
      onSave={(next) => setValue(next.trim())}
      error={undefined}
    />
  )
}

/** A store where somebody else's text arrives instead of ours. */
function Overwritten() {
  const [value, setValue] = useState('Spring')
  return (
    <AutosaveField
      field={{ name: 'subject', label: 'Subject', type: 'text' }}
      value={value}
      onSave={() => setValue('Autumn, by a colleague')}
      error={undefined}
    />
  )
}

describe('a field whose store trims (task-385)', () => {
  it('takes its own trimmed text back without a conflict', () => {
    render(<Trimming />)
    const input = screen.getByLabelText('Subject')
    fireEvent.change(input, { target: { value: '  here is your news ' } })
    fireEvent.blur(input)
    expect(screen.queryByText(/Somebody else changed this/)).not.toBeInTheDocument()
    expect(input).toHaveValue('here is your news')
  })

  it('still shows a real change by somebody else', () => {
    render(<Overwritten />)
    const input = screen.getByLabelText('Subject')
    fireEvent.change(input, { target: { value: 'Summer' } })
    fireEvent.blur(input)
    expect(screen.getByText(/Somebody else changed this/)).toBeInTheDocument()
  })
})
