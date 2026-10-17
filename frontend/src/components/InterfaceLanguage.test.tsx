import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Button, Menu, MenuItem, MenuTrigger, Popover } from 'react-aria-components'

import InterfaceLanguage from './InterfaceLanguage'

afterEach(() => vi.restoreAllMocks())

describe('the interface language (task-392 item 18)', () => {
  it("gives React Aria's own words in English, whatever the browser's language", async () => {
    vi.spyOn(navigator, 'language', 'get').mockReturnValue('de-DE')
    vi.spyOn(navigator, 'languages', 'get').mockReturnValue(['de-DE'])
    render(
      <InterfaceLanguage>
        <MenuTrigger>
          <Button>Open</Button>
          <Popover>
            <Menu aria-label="Things">
              <MenuItem>One</MenuItem>
            </Menu>
          </Popover>
        </MenuTrigger>
      </InterfaceLanguage>,
    )
    // React Aria reads the browser's language when it loads and again on this
    // event, which its mounted components listen for.
    act(() => void window.dispatchEvent(new Event('languagechange')))
    fireEvent.click(screen.getByRole('button', { name: 'Open' }))
    // The popover's hidden close button, React Aria's word: "Schließen" in German.
    expect((await screen.findAllByRole('button', { name: 'Dismiss', hidden: true })).length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: 'Schließen', hidden: true })).not.toBeInTheDocument()
  })
})
