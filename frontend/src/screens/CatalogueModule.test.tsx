import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import VariantEditor from './VariantEditor'
import { jsonResponse, page, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const T = (n: number) => `2026-10-03T10:00:${String(n).padStart(2, '0')}.000000Z`

const MANIFESTS = [
  {
    name: 'hero', channel: 'email', label: 'Hero', description: '', cms: true,
    variables: [
      { name: 'headline_hero', required: true, label: 'Headline', envelope: false, type: 'text' },
      { name: 'button_label_hero', required: true, label: 'Button', envelope: false, type: 'text' },
    ],
  },
]

/**
 * A server that keeps state and checks both versions the way the real one
 * does: the record's for catalogue edits (task-257), the module's for override
 * writes (task-256), each refusing a stale one with 409.
 */
function server(options: { slot?: boolean; unbound?: boolean; unpublished?: boolean; override?: object } = {}) {
  let clock = 1
  const state = {
    record: {
      id: 42, title: 'Lisbon in spring', description: null, status: 'active', updated_at: T(1),
      content: { headline_hero: 'Lisbon', button_label_hero: 'Go' },
      latest_version_number: 1, unpublished_changes: options.unpublished ?? false,
    },
    module: {
      id: 12, position: 1, module_type: 'hero',
      content_record_id: options.slot || options.unbound ? null : 42,
      decision_slot_id: options.slot ? 5 : null,
      module_data: {}, known: true, overrideable: !options.slot && !options.unbound,
      active_override: options.override ?? null, updated_at: T(1),
    } as Record<string, unknown>,
  }
  const writes: Request[] = []
  const stale = (request: Request, current: string) =>
    request.headers.get('If-Match') !== null && request.headers.get('If-Match') !== current
  const handlers = {
    'GET /campaigns/1/composition': () => jsonResponse({
      campaign: { id: 1, name: 'Spring' },
      variants: [{
        variant: { id: 3, name: 'Variant A', channel: 'email', status: 'draft', updated_at: T(1) },
        module_limit: null, can_add_module: true, has_envelope: false, accepted_module_types: ['hero'],
        modules: [state.module], envelope_modules: [], decision_slots: [],
      }],
    }),
    'GET /modules': () => jsonResponse(MANIFESTS),
    'GET /content/42': () => jsonResponse(state.record),
    'GET /content/42/unsent-campaigns': () =>
      jsonResponse({ count: 2, campaigns: [{ id: 1, name: 'Spring' }, { id: 9, name: 'Summer' }] }),
    'GET /content/': () => jsonResponse(page([{ id: 42, title: 'Lisbon in spring', content: {}, status: 'active' }])),
    'PATCH /content/42': async (request: Request) => {
      writes.push(request.clone())
      if (stale(request, state.record.updated_at)) return jsonResponse({ detail: 'changed' }, 409)
      const body = await request.json()
      Object.assign(state.record, {
        content: { ...state.record.content, ...body.content }, updated_at: T(++clock), unpublished_changes: true,
      })
      return jsonResponse(state.record)
    },
    'PUT /overrides/modules/12': async (request: Request) => {
      writes.push(request.clone())
      if (stale(request, state.module.updated_at as string)) return jsonResponse({ detail: 'changed' }, 409)
      const body = await request.json()
      const fields = body.field_overrides
      state.module.active_override = Object.keys(fields).length
        ? { id: 70, field_overrides: fields, overridden_by: 'me', reason: body.reason }
        : null
      state.module.updated_at = T(++clock)
      return jsonResponse({ module_id: 12, module_updated_at: state.module.updated_at, override: state.module.active_override })
    },
    'PUT /campaigns/modules/12': async (request: Request) => {
      writes.push(request.clone())
      if (stale(request, state.module.updated_at as string)) return jsonResponse({ detail: 'changed' }, 409)
      Object.assign(state.module, await request.json(), { updated_at: T(++clock), overrideable: true })
      return jsonResponse(state.module)
    },
    'POST /content/versions': () => {
      Object.assign(state.record, { latest_version_number: 2, unpublished_changes: false })
      return jsonResponse({ id: 1, content_record_id: 42, version_number: 2 })
    },
  }
  return { state, writes, handlers }
}

function open(handlers: Record<string, (request: Request) => Response | Promise<Response>>) {
  const fetchMock = stubFetch(handlers as never)
  renderWithProviders(
    <Routes>
      <Route path="/campaigns/:id/variants/:variantId" element={<VariantEditor />} />
    </Routes>,
    { route: '/campaigns/1/variants/3' },
  )
  return fetchMock
}

async function edit(label: RegExp, value: string) {
  const input = await screen.findByLabelText(label)
  fireEvent.change(input, { target: { value } })
  fireEvent.blur(input)
}

describe('a catalogue field', () => {
  it('shows the record and edits the record, stating its version and its channel', async () => {
    const { handlers, writes } = server()
    open(handlers)
    expect(await screen.findByLabelText(/^Headline/)).toHaveValue('Lisbon')
    await edit(/^Headline/, 'Lisbon, again')
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(new URL(writes[0].url).pathname).toBe('/content/42')
    expect(writes[0].headers.get('If-Match')).toBe(T(1))
    expect(await writes[0].json()).toEqual({ content: { headline_hero: 'Lisbon, again' }, groups: ['email'] })
  })

  it('shows how many unsent campaigns the record reaches, and which on request', async () => {
    open(server().handlers)
    expect(await screen.findByText(/used by 2 unsent campaigns/)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Summer' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Show which' }))
    expect(screen.getByRole('link', { name: 'Summer' })).toHaveAttribute('href', '/campaigns/9')
  })

  it('says when a send would not carry the edit yet, and publishes', async () => {
    const { handlers } = server({ unpublished: true })
    const fetchMock = open(handlers)
    expect(await screen.findByRole('status')).toHaveTextContent('sends still use version 1')
    fireEvent.click(screen.getByRole('button', { name: 'Publish' }))
    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([r]) => (r as Request).method === 'POST')).toBe(true),
    )
    await waitFor(() => expect(screen.queryByText(/sends still use/)).not.toBeInTheDocument())
  })
})

describe('overriding', () => {
  it('converts one field, keeps the catalogue value in view, and writes with the module version', async () => {
    const { handlers, writes } = server()
    open(handlers)
    fireEvent.click(await screen.findByRole('button', { name: 'Override Headline here' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(writes[0].headers.get('If-Match')).toBe(T(1))
    expect(await writes[0].json()).toEqual({ field_overrides: { headline_hero: 'Lisbon' }, reason: null })
    const overridden = await screen.findByLabelText(/Headline — overridden here/)
    expect(within(overridden.closest('.overridden') as HTMLElement).getByText('Catalogue: Lisbon'))
      .toBeInTheDocument()
    // The other field is still the catalogue's.
    expect(screen.getByLabelText(/^Button/)).toHaveValue('Go')
  })

  it('saves an overridden field into the override, keeping the others', async () => {
    const { handlers, writes } = server({
      override: { id: 70, field_overrides: { headline_hero: 'Short', button_label_hero: 'Book' }, reason: null },
    })
    open(handlers)
    await edit(/Headline — overridden here/, 'Shorter')
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(new URL(writes[0].url).pathname).toBe('/overrides/modules/12')
    expect(await writes[0].json()).toEqual({
      field_overrides: { headline_hero: 'Shorter', button_label_hero: 'Book' }, reason: null,
    })
  })

  it('resets one field, and every field only after asking', async () => {
    const { handlers, writes } = server({
      override: { id: 70, field_overrides: { headline_hero: 'Short', button_label_hero: 'Book' }, reason: null },
    })
    open(handlers)
    fireEvent.click((await screen.findAllByRole('button', { name: 'Back to the catalogue value' }))[0])
    await waitFor(() => expect(writes).toHaveLength(1))
    expect((await writes[0].json()).field_overrides).toEqual({ button_label_hero: 'Book' })

    fireEvent.click(await screen.findByRole('button', { name: 'Reset all overrides on this module' }))
    fireEvent.click(screen.getByRole('button', { name: 'Keep them' }))
    expect(writes).toHaveLength(1)
    fireEvent.click(screen.getByRole('button', { name: 'Reset all overrides on this module' }))
    fireEvent.click(screen.getByRole('button', { name: 'Reset every override here' }))
    await waitFor(() => expect(writes).toHaveLength(2))
    expect((await writes[1].json()).field_overrides).toEqual({})
  })

  it('takes a reason from the presets', async () => {
    const { handlers, writes } = server({
      override: { id: 70, field_overrides: { headline_hero: 'Short' }, reason: null },
    })
    open(handlers)
    fireEvent.click(await screen.findByRole('button', { name: /No reason given/ }))
    fireEvent.click(await screen.findByRole('option', { name: 'Shorter for this send' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toEqual({
      field_overrides: { headline_hero: 'Short' }, reason: 'Shorter for this send',
    })
  })

  it('is never offered on a module bound to a decision slot', async () => {
    open(server({ slot: true }).handlers)
    expect(await screen.findByText(/A slot is never overridden/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Override .* here/ })).not.toBeInTheDocument()
  })
})

describe('binding', () => {
  it('binds an unbound catalogue module to a record found by title', async () => {
    const { handlers, writes } = server({ unbound: true })
    open(handlers)
    fireEvent.change(await screen.findByLabelText('Find a content record by title'), { target: { value: 'Lis' } })
    fireEvent.click(await screen.findByRole('button', { name: 'Use “Lisbon in spring”' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(writes[0].headers.get('If-Match')).toBe(T(1))
    expect((await writes[0].json()).content_record_id).toBe(42)
    expect(await screen.findByLabelText(/^Headline/)).toHaveValue('Lisbon')
  })
})
