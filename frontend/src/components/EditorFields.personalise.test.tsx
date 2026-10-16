import { fireEvent, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AutosaveField } from './EditorFields'
import { jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const ENTRIES = {
  items: [{ id: 1, name: 'salutation_formal', label: 'Salutation formal', languages: {}, updated_at: '2026-10-16T09:00:00Z' }],
  may_manage: true,
}

function field(props: { type?: string; personalise?: boolean; value?: string }) {
  stubFetch({ 'GET /expressions': () => jsonResponse(ENTRIES) } as never)
  const onSave = vi.fn()
  renderWithProviders(
    <AutosaveField
      field={{ name: 'subject', label: 'Subject', type: props.type ?? 'text' }}
      value={props.value ?? ''}
      onSave={onSave}
      personalise={props.personalise ?? true}
      error={undefined}
    />,
  )
  return onSave
}

describe('Personalise… (task-365; ADR-199)', () => {
  it('puts the chosen entry in at the caret and saves at once', async () => {
    const onSave = field({ value: 'Dear  news' })
    const input = screen.getByLabelText('Subject') as HTMLInputElement
    input.setSelectionRange(5, 5)
    fireEvent.select(input)
    fireEvent.click(await screen.findByRole('button', { name: 'Personalise…' }))
    fireEvent.click(await screen.findByRole('menuitem', { name: /Salutation formal/ }))
    expect(onSave).toHaveBeenCalledWith('Dear {{salutation_formal}} news')
  })

  it('appends when the field was never focused', async () => {
    const onSave = field({ value: 'Hello' })
    fireEvent.click(await screen.findByRole('button', { name: 'Personalise…' }))
    fireEvent.click(await screen.findByRole('menuitem', { name: /Salutation formal/ }))
    expect(onSave).toHaveBeenCalledWith('Hello{{salutation_formal}}')
  })

  // Beside a control field that is offered it: once its button is there, the
  // entries have loaded, so a missing button is a real "not offered".
  it.each([
    ['on a link', { type: 'url' }],
    ['where it was not asked for', { asked: false }],
  ])('is not offered %s', async (_name, props: { type?: string; asked?: boolean }) => {
    stubFetch({ 'GET /expressions': () => jsonResponse(ENTRIES) } as never)
    renderWithProviders(
      <>
        <AutosaveField field={{ name: 'subject', label: 'Subject', type: 'text' }} value="" onSave={vi.fn()}
          personalise error={undefined} />
        {props.asked === false ? (
          <AutosaveField field={{ name: 'other', label: 'Other', type: 'text' }} value="" onSave={vi.fn()}
            error={undefined} />
        ) : (
          <AutosaveField field={{ name: 'other', label: 'Other', type: props.type ?? 'text' }} value=""
            onSave={vi.fn()} personalise error={undefined} />
        )}
      </>,
    )
    await screen.findByRole('button', { name: 'Personalise…' })
    expect(screen.getAllByRole('button', { name: 'Personalise…' })).toHaveLength(1)
  })
})
