import { useState } from 'react'
import { fireEvent, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Link, Route, Routes, useParams } from 'react-router'

import DetailOutlet from './DetailOutlet'
import { renderWithProviders } from '../test-utils'

/** A details pane with state of its own, as a typed draft is. */
function Pane() {
  const { id } = useParams()
  const [typed, setTyped] = useState('')
  return (
    <>
      <p>open {id}</p>
      <input aria-label="Draft" value={typed} onChange={(e) => setTyped(e.target.value)} />
    </>
  )
}

function Split() {
  return (
    <>
      <Link to="/items/2">Second</Link>
      <Link to="/items/1?q=search">Same, searched</Link>
      <DetailOutlet />
    </>
  )
}

describe('the details column beside a list (task-372)', () => {
  it('starts afresh for another item, and keeps its state when only the query changes', async () => {
    renderWithProviders(
      <Routes>
        <Route element={<Split />}>
          <Route path="/items/:id" element={<Pane />} />
        </Route>
      </Routes>,
      { route: '/items/1' },
    )
    fireEvent.change(screen.getByLabelText('Draft'), { target: { value: 'half typed' } })
    fireEvent.click(screen.getByRole('link', { name: 'Same, searched' }))
    expect(screen.getByLabelText('Draft')).toHaveValue('half typed')
    fireEvent.click(screen.getByRole('link', { name: 'Second' }))
    expect(await screen.findByText('open 2')).toBeInTheDocument()
    expect(screen.getByLabelText('Draft')).toHaveValue('')
  })
})
