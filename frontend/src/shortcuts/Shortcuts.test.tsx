import { act, fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import { SearchBox } from '../components/RecipientSearch'
import Nav, { GoToShortcuts } from '../shell/Nav'
import { renderWithProviders } from '../test-utils'
import { ShortcutsProvider } from './Shortcuts'

afterEach(() => vi.useRealTimers())

function press(key: string, target: Element = document.body) {
  fireEvent.keyDown(target, { key })
}

function app(route = '/campaigns') {
  return renderWithProviders(
    <ShortcutsProvider>
      <GoToShortcuts />
      <Routes>
        <Route path="/campaigns" element={<><h1>Campaigns screen</h1><SearchBox label="Find a campaign" /></>} />
        <Route path="/monitoring" element={<h1>Monitoring screen</h1>} />
      </Routes>
    </ShortcutsProvider>,
    { route },
  )
}

describe('keyboard shortcuts (task-266)', () => {
  it('? opens an overview of the shortcuts that apply here, grouped', async () => {
    app()
    press('?')
    const overview = await screen.findByRole('dialog', { name: 'Keyboard shortcuts' })
    const goTo = within(overview).getByRole('region', { name: 'Go to' })
    expect(within(goTo).getByText('Monitoring')).toBeInTheDocument()
    const here = within(overview).getByRole('region', { name: 'This screen' })
    expect(within(here).getByText('Find a campaign')).toBeInTheDocument()
  })

  it('g then a letter goes to that screen', async () => {
    app()
    press('g')
    press('m')
    expect(await screen.findByRole('heading', { name: 'Monitoring screen' })).toBeInTheDocument()
  })

  it('the second key must follow within a second', async () => {
    vi.useFakeTimers()
    app()
    press('g')
    act(() => vi.advanceTimersByTime(1500))
    press('m')
    expect(screen.getByRole('heading', { name: 'Campaigns screen' })).toBeInTheDocument()
  })

  it('/ jumps to the search', () => {
    app()
    press('/')
    expect(screen.getByLabelText('Find a campaign')).toHaveFocus()
  })

  it('never fires while typing in a field', () => {
    app()
    const search = screen.getByLabelText('Find a campaign')
    press('g', search)
    press('m', search)
    press('?', search)
    expect(screen.getByRole('heading', { name: 'Campaigns screen' })).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it("a screen's shortcuts leave the overview when the screen does", async () => {
    app()
    press('g')
    press('m')
    await screen.findByRole('heading', { name: 'Monitoring screen' })
    press('?')
    const overview = await screen.findByRole('dialog', { name: 'Keyboard shortcuts' })
    expect(within(overview).queryByText('Find a campaign')).not.toBeInTheDocument()
  })
})

describe('hints on the elements while Alt or Ctrl is held (2026-10-04)', () => {
  function withNav() {
    return renderWithProviders(
      <ShortcutsProvider>
        <GoToShortcuts />
        <Nav />
        <Routes>
          <Route path="/campaigns" element={<SearchBox label="Find a campaign" />} />
        </Routes>
      </ShortcutsProvider>,
      { route: '/campaigns' },
    )
  }

  const hints = () => [...document.querySelectorAll('.shortcut-hint')].map((h) => h.textContent)

  it('shows each element its keys while Alt is held, and hides them on release', () => {
    withNav()
    expect(hints()).toEqual([])
    fireEvent.keyDown(window, { key: 'Alt' })
    expect(hints()).toEqual(expect.arrayContaining(['gc', 'gm', '/']))
    // Badges are for eyes: the field keeps its name for a screen reader.
    expect(screen.getByRole('textbox', { name: 'Find a campaign' })).toBeInTheDocument()
    fireEvent.keyUp(window, { key: 'Alt' })
    expect(hints()).toEqual([])
  })

  it('Ctrl shows them too, and any other key or leaving the window hides them', () => {
    withNav()
    fireEvent.keyDown(window, { key: 'Control' })
    expect(hints().length).toBeGreaterThan(0)
    fireEvent.keyDown(window, { key: 'c', ctrlKey: true })
    expect(hints()).toEqual([])
    fireEvent.keyDown(window, { key: 'Control' })
    fireEvent.blur(window)
    expect(hints()).toEqual([])
  })
})
