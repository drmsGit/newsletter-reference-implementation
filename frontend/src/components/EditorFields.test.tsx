import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { AutosaveField } from './EditorFields'

/**
 * A background refresh must not replace what a manager is typing (task-329).
 *
 * The draft used to follow every change of the stored value, so a refetch on
 * window focus — or another manager's save arriving — wiped unsaved typing.
 * Decided with the user 2026-10-09: the typing stays, a notice shows their
 * value, and leaving the field does not save over theirs; the manager chooses
 * "Save mine" or "Use theirs". A field nobody typed in still follows.
 */
const TITLE = { name: 'title', label: 'Title', type: 'text' }

function field(value: string, onSave = vi.fn(), onLeave?: (draft: string, next: Element | null) => boolean) {
  const ui = (v: string) => (
    <>
      <AutosaveField field={TITLE} value={v} onSave={onSave} onLeave={onLeave} error={undefined} />
      <button type="button">elsewhere</button>
    </>
  )
  const view = render(ui(value))
  return { onSave, input: screen.getByLabelText('Title') as HTMLInputElement, rerender: (v: string) => view.rerender(ui(v)) }
}

const type = (input: HTMLInputElement, text: string) => {
  fireEvent.focus(input)
  fireEvent.change(input, { target: { value: text } })
}
const leave = (input: HTMLInputElement) => fireEvent.blur(input, { relatedTarget: screen.getByText('elsewhere') })

describe('AutosaveField and a background refresh (task-329)', () => {
  it('keeps unsaved typing when the stored value changes underneath it', () => {
    const { input, rerender, onSave } = field('Spring sale')
    type(input, 'My unsaved draft')
    rerender('Their new title')

    expect(input.value).toBe('My unsaved draft')
    expect(screen.getByRole('alert').textContent).toContain('Their new title')
    expect(onSave).not.toHaveBeenCalled()
  })

  it('does not save over theirs when the field is left; the manager chooses', () => {
    const { input, rerender, onSave } = field('Spring sale')
    type(input, 'My unsaved draft')
    rerender('Their new title')
    leave(input)
    expect(onSave).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Save mine' }))
    expect(onSave).toHaveBeenCalledExactlyOnceWith('My unsaved draft')
    expect(screen.queryByRole('alert')).toBeNull()      // chosen: no longer asked
    rerender('My unsaved draft')         // the save comes back
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('"Use theirs" takes their value and saves nothing', () => {
    const { input, rerender, onSave } = field('Spring sale')
    type(input, 'My unsaved draft')
    rerender('Their new title')
    fireEvent.click(screen.getByRole('button', { name: 'Use theirs' }))

    expect(input.value).toBe('Their new title')
    expect(screen.queryByRole('alert')).toBeNull()
    leave(input)
    expect(onSave).not.toHaveBeenCalled()
  })

  it('a field nobody typed in follows the stored value, and leaving it saves nothing stale', () => {
    const { input, rerender, onSave } = field('Spring sale')
    fireEvent.focus(input)
    rerender('Their new title')
    expect(input.value).toBe('Their new title')
    leave(input)
    expect(onSave).not.toHaveBeenCalled()
  })

  it('an ordinary edit still saves on leaving, and its own save brings no notice', () => {
    const { input, rerender, onSave } = field('Spring sale')
    type(input, 'Summer sale')
    leave(input)
    expect(onSave).toHaveBeenCalledExactlyOnceWith('Summer sale')
    rerender('Summer sale')
    expect(screen.queryByRole('alert')).toBeNull()
    type(input, 'Autumn sale')        // and the next edit starts from the saved value
    rerender('Their new title')
    expect(input.value).toBe('Autumn sale')
  })

  it('typing handed elsewhere (task-261) still goes there during a conflict', () => {
    const onLeave = vi.fn(() => true)
    const { input, rerender, onSave } = field('Spring sale', vi.fn(), onLeave)
    type(input, 'My unsaved draft')
    rerender('Their new title')
    leave(input)
    expect(onLeave).toHaveBeenCalledWith('My unsaved draft', screen.getByText('elsewhere'))
    expect(onSave).not.toHaveBeenCalled()
  })
})
