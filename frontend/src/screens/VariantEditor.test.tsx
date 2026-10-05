import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import VariantEditor from './VariantEditor'
import { jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const MANIFESTS = [
  {
    name: 'header', channel: 'email', label: 'Header', description: '', cms: false, carries_envelope: true,
    variables: [
      { name: 'subject', required: true, label: 'Subject', envelope: true, type: 'text' },
      { name: 'preheader', required: false, label: 'Preheader', envelope: true, type: 'text' },
    ],
  },
  {
    name: 'cta', channel: 'email', label: 'Call to action', description: '', cms: false,
    variables: [
      { name: 'label', required: true, label: 'Button label', envelope: false, type: 'text' },
      { name: 'url', required: true, label: 'Link', envelope: false, type: 'url' },
    ],
  },
  {
    name: 'editorial', channel: 'email', label: 'Editorial', description: '', cms: false,
    variables: [{ name: 'text', required: true, label: 'Text', envelope: false, type: 'richtext' }],
  },
  {
    name: 'hero', channel: 'email', label: 'Hero', description: '', cms: true,
    variables: [{ name: 'headline_hero', required: true, envelope: false, type: 'text' }],
  },
]

const T = (n: number) => `2026-10-03T10:00:0${n}.000000Z`

/**
 * A server that keeps state and checks If-Match the way the real one does
 * (task-110): a write stating an old version is refused with 409. That is what
 * makes "two quick saves never refuse each other" a real assertion rather than
 * one the stub satisfies by agreeing with everything.
 */
function server(overrides: { canAdd?: boolean } = {}) {
  let clock = 1
  const state = {
    variant: { id: 3, campaign_id: 1, channel: 'email', name: 'Variant A', subject: 'Spring', preheader: 'Peek',
      status: 'draft', created_at: T(0), updated_at: T(1) },
    modules: [
      { id: 11, position: 1, module_type: 'cta', content_record_id: null, decision_slot_id: null,
        module_data: { label: 'Go', url: 'https://example.invalid' }, known: true, overrideable: false,
        active_override: null, updated_at: T(1) },
      { id: 12, position: 2, module_type: 'hero', content_record_id: 42, content_record_title: 'Lisbon', decision_slot_id: null,
        module_data: {}, known: true, overrideable: true, active_override: null, updated_at: T(1) },
    ],
  }
  const puts: Request[] = []
  const composition = () => ({
    campaign: { id: 1, name: 'Spring', status: 'draft', created_at: T(0), updated_at: T(0) },
    variants: [{
      variant: state.variant, module_limit: null, can_add_module: overrides.canAdd ?? true,
      has_envelope: true, accepted_module_types: ['cta', 'editorial', 'hero'],
      modules: [...state.modules].sort((a, b) => a.position - b.position),
      envelope_modules: [], decision_slots: [],
    }],
  })
  const stale = (request: Request, current: string) =>
    request.headers.get('If-Match') !== null && request.headers.get('If-Match') !== current
  const handlers = {
    'GET /campaigns/1/composition': () => jsonResponse(composition()),
    'GET /modules': () => jsonResponse(MANIFESTS),
    'PUT /campaigns/modules/11': async (request: Request) => {
      puts.push(request.clone())
      const module = state.modules[0]
      if (stale(request, module.updated_at)) return jsonResponse({ detail: 'changed' }, 409)
      const body = await request.json()
      Object.assign(module, { module_data: body.module_data, updated_at: T(++clock) })
      return jsonResponse({ ...module, variant_id: 3, created_at: T(0) })
    },
    'PUT /campaigns/variants/3': async (request: Request) => {
      puts.push(request.clone())
      if (stale(request, state.variant.updated_at)) return jsonResponse({ detail: 'changed' }, 409)
      Object.assign(state.variant, await request.json(), { updated_at: T(++clock) })
      return jsonResponse(state.variant)
    },
  }
  return { state, puts, handlers }
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

function sent(fetchMock: ReturnType<typeof stubFetch>, method: string) {
  return fetchMock.mock.calls.map(([r]) => r as Request).filter((r) => r.method === method)
}

async function edit(label: string, value: string) {
  const input = await screen.findByLabelText(new RegExp(`^${label}`))
  fireEvent.change(input, { target: { value } })
  fireEvent.blur(input)
}

describe('the variant editor', () => {
  it('shows the envelope, the module stack, and the first module\'s fields', async () => {
    open(server().handlers)
    expect(await screen.findByLabelText(/^Subject/)).toHaveValue('Spring')
    const stack = screen.getByRole('list')
    expect(within(stack).getByRole('button', { name: /^Call to action ·/ })).toBeInTheDocument()
    expect(within(stack).getByRole("button", { name: /Hero · “Lisbon”/ })).toBeInTheDocument()
    expect(screen.getByLabelText(/^Button label/)).toHaveValue('Go')
  })

  it('saves a field on blur with the version it read, and only when it changed', async () => {
    const { handlers, puts } = server()
    open(handlers)
    const input = await screen.findByLabelText(/^Button label/)
    fireEvent.blur(input)
    await edit('Button label', 'Go now')
    await waitFor(() => expect(puts).toHaveLength(1))
    expect(puts[0].headers.get('If-Match')).toBe(T(1))
    expect(await puts[0].json()).toEqual({
      module_type: 'cta', content_record_id: null, decision_slot_id: null,
      module_data: { label: 'Go now', url: 'https://example.invalid' },
    })
  })

  it('never refuses two quick saves against each other', async () => {
    const { handlers, puts, state } = server()
    open(handlers)
    const label = await screen.findByLabelText(/^Button label/)
    const link = screen.getByLabelText(/^Link/)
    // Both blurs fire before the first save has answered: nothing is awaited
    // between them, so the second save is made while the first is in flight.
    fireEvent.change(label, { target: { value: 'Go now' } })
    fireEvent.blur(label)
    fireEvent.change(link, { target: { value: 'https://example.invalid/new' } })
    fireEvent.blur(link)
    await waitFor(() => expect(puts).toHaveLength(2))
    expect(puts.map((r) => r.headers.get('If-Match'))).toEqual([T(1), T(2)])
    await waitFor(() =>
      expect(state.modules[0].module_data).toEqual({ label: 'Go now', url: 'https://example.invalid/new' }),
    )
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('takes the envelope fields from the module the server says carries it (task-221)', async () => {
    // A second module declaring an envelope field must not reach the envelope
    // area: the client asks which module carries it instead of scanning.
    const { handlers } = server()
    open({
      ...handlers,
      'GET /modules': () => jsonResponse([
        ...MANIFESTS,
        { name: 'stray', channel: 'email', label: 'Stray', description: '', cms: false, carries_envelope: false,
          variables: [{ name: 'stray_subject', required: false, label: 'Stray subject', envelope: true, type: 'text' }] },
      ]),
    })
    const envelope = await screen.findByRole('region', { name: 'Envelope' })
    expect(within(envelope).getByLabelText(/^Subject/)).toBeInTheDocument()
    expect(within(envelope).queryByLabelText('Stray subject')).not.toBeInTheDocument()
  })

  it('shows a stale save in place and loads the other version on request', async () => {
    const { handlers, state } = server()
    open(handlers)
    await screen.findByLabelText(/^Button label/)
    // Somebody else saved the module after this screen read it.
    Object.assign(state.modules[0], { module_data: { label: 'Theirs', url: 'x' }, updated_at: T(9) })
    await edit('Button label', 'Mine')
    expect(await screen.findByRole('alert')).toHaveTextContent(/changed the module after you loaded it/)
    fireEvent.click(screen.getByRole('button', { name: 'Load their version' }))
    await waitFor(() => expect(screen.getByLabelText(/^Button label/)).toHaveValue('Theirs'))
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('drops the refused text even when their change was to another field', async () => {
    // The case the record page got wrong (task-279): this field's stored value
    // did not change, so a field that resets only when its value changes kept
    // the refused text on screen, looking saved.
    const { handlers, state } = server()
    open(handlers)
    const before = (await screen.findByLabelText(/^Button label/) as HTMLInputElement).value
    Object.assign(state.modules[0], {
      module_data: { ...state.modules[0].module_data, url: 'https://theirs.test' }, updated_at: T(9),
    })
    await edit('Button label', 'Mine')
    expect(await screen.findByRole('alert')).toHaveTextContent(/changed the module after you loaded it/)
    fireEvent.click(screen.getByRole('button', { name: 'Load their version' }))
    await waitFor(() => expect(screen.getByLabelText(/^Button label/)).toHaveValue(before))
  })

  it('drops a refused subject when their change was to the preheader', async () => {
    const { handlers, state } = server()
    open(handlers)
    await screen.findByLabelText(/^Subject/)
    Object.assign(state.variant, { preheader: 'Theirs', updated_at: T(9) })
    await edit('Subject', 'Mine')
    expect(await screen.findByRole('alert')).toHaveTextContent(/changed the variant after you loaded it/)
    fireEvent.click(screen.getByRole('button', { name: 'Load their version' }))
    await waitFor(() => expect(screen.getByLabelText(/^Subject/)).toHaveValue('Spring'))
  })

  it('shows a refused field on that field', async () => {
    const { handlers } = server()
    open({
      ...handlers,
      'PUT /campaigns/modules/11': () =>
        jsonResponse({ detail: [{ loc: ['body', 'module_data', 'url'], msg: 'must be text', type: 'value_error' }] }, 422),
    })
    await edit('Link', 'https://example.invalid/x')
    const field = (await screen.findByLabelText(/^Link/)).closest('.field') as HTMLElement
    expect(await within(field).findByRole('alert')).toHaveTextContent('must be text')
  })

  it('saves the envelope through the variant, sending all three of its fields', async () => {
    const { handlers, puts } = server()
    open(handlers)
    await edit('Subject', 'Summer')
    await waitFor(() => expect(puts).toHaveLength(1))
    expect(puts[0].headers.get('If-Match')).toBe(T(1))
    expect(await puts[0].json()).toEqual({ name: 'Variant A', subject: 'Summer', preheader: 'Peek' })
  })

})

describe('the module stack', () => {
  it('moves a module with its button and with Alt+Arrow, stating its version', async () => {
    const { handlers } = server()
    const fetchMock = open({
      ...handlers,
      'POST /campaigns/modules/11/move': () => jsonResponse({}),
    })
    fireEvent.click(await screen.findByRole('button', { name: 'Move Call to action down' }))
    await waitFor(() => expect(sent(fetchMock, 'POST')).toHaveLength(1))
    fireEvent.keyDown(screen.getByRole('button', { name: /^Call to action ·/ }), { key: 'ArrowDown', altKey: true })
    await waitFor(() => expect(sent(fetchMock, 'POST')).toHaveLength(2))
    for (const request of sent(fetchMock, 'POST')) {
      expect(new URL(request.url).search).toBe('?direction=down')
      expect(request.headers.get('If-Match')).toBe(T(1))
    }
  })

  it('asks once before removing, and Keep sends nothing', async () => {
    const { handlers } = server()
    const fetchMock = open({ ...handlers, 'DELETE /campaigns/modules/11': () => jsonResponse({}) })
    fireEvent.click(await screen.findByRole('button', { name: 'Remove Call to action' }))
    fireEvent.click(screen.getByRole('button', { name: 'Keep' }))
    expect(sent(fetchMock, 'DELETE')).toHaveLength(0)
    fireEvent.click(screen.getByRole('button', { name: 'Remove Call to action' }))
    fireEvent.click(screen.getByRole('button', { name: 'Remove Call to action' }))
    await waitFor(() => expect(sent(fetchMock, 'DELETE')).toHaveLength(1))
    expect(sent(fetchMock, 'DELETE')[0].headers.get('If-Match')).toBe(T(1))
  })

  it('adds a module of a type the channel accepts', async () => {
    const { handlers } = server()
    const fetchMock = open({
      ...handlers,
      'POST /campaigns/variants/3/modules': () => jsonResponse({ id: 13 }),
    })
    fireEvent.click(await screen.findByRole('button', { name: 'Add' }))
    await waitFor(() => expect(sent(fetchMock, 'POST')).toHaveLength(1))
    expect(await sent(fetchMock, 'POST')[0].json()).toEqual({ module_type: 'cta' })
  })

  it('offers no add when the channel is full', async () => {
    open(server({ canAdd: false }).handlers)
    await screen.findByLabelText(/^Subject/)
    expect(screen.queryByRole('button', { name: 'Add' })).not.toBeInTheDocument()
  })
})

// `act` is imported for React's sake in some environments; keep the linter quiet.
void act
