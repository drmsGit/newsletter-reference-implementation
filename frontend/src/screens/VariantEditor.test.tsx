import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import VariantEditor from './VariantEditor'
import { jsonResponse, renderWithProviders, stubFetch, A_BRAND_PROFILE } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const MANIFESTS = [
  {
    name: 'envelope', channel: 'email', label: 'Envelope (subject and preheader)', description: '', cms: false, carries_envelope: true,
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
  {
    name: 'column', channel: 'email', label: 'Column', description: '', cms: true, pairs: true,
    variables: [{ name: 'headline_medium', required: true, envelope: false, type: 'text' }],
  },
]

const T = (n: number) => `2026-10-03T10:00:0${n}.000000Z`

/**
 * A server that keeps state and checks If-Match the way the real one does
 * (task-110): a write stating an old version is refused with 409. That is what
 * makes "two quick saves never refuse each other" a real assertion rather than
 * one the stub satisfies by agreeing with everything.
 */
function server(overrides: { canAdd?: boolean; accepted?: string[] } = {}) {
  let clock = 1
  const state = {
    variant: { id: 3, campaign_id: 1, channel: 'email', name: 'Variant A',
      envelope: { subject: 'Spring', preheader: 'Peek' } as Record<string, string>,
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
      has_envelope: true, brand_profile: A_BRAND_PROFILE, accepted_module_types: overrides.accepted ?? ['cta', 'editorial', 'hero'],
      modules: [...state.modules].sort((a, b) => a.position - b.position),
      envelope_modules: [], decision_slots: [],
    }],
  })
  const stale = (request: Request, current: string) =>
    request.headers.get('If-Match') !== null && request.headers.get('If-Match') !== current
  const handlers = {
    'GET /campaigns/1/composition': () => jsonResponse(composition()),
    'GET /modules': () => jsonResponse(MANIFESTS),
    'GET /campaigns/variants/3/suggestions': () => jsonResponse([]),
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
      const body = await request.json()
      // As the server does: a sent envelope replaces the stored one, blanks dropped (task-48).
      const envelope = body.envelope === undefined ? state.variant.envelope
        : Object.fromEntries(Object.entries(body.envelope as Record<string, string | null>).filter(([, v]) => v))
      Object.assign(state.variant, { name: body.name, envelope, updated_at: T(++clock) })
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
    Object.assign(state.variant, { envelope: { ...state.variant.envelope, preheader: 'Theirs' }, updated_at: T(9) })
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

  it('saves the envelope through the variant, sending the whole envelope', async () => {
    const { handlers, puts } = server()
    open(handlers)
    await edit('Subject', 'Summer')
    await waitFor(() => expect(puts).toHaveLength(1))
    expect(puts[0].headers.get('If-Match')).toBe(T(1))
    expect(await puts[0].json()).toEqual({ name: 'Variant A', envelope: { subject: 'Summer', preheader: 'Peek' } })
  })

  it('shows whatever envelope fields the channel declares, by their names (task-48)', async () => {
    const { handlers, state } = server()
    state.variant.envelope = { sender_name: 'Ana from Travel' }
    open({
      ...handlers,
      'GET /modules': () => jsonResponse([
        ...MANIFESTS.filter((m) => m.name !== 'envelope'),
        { name: 'envelope', channel: 'email', label: 'Envelope (subject and preheader)', description: '', cms: false, carries_envelope: true,
          variables: [{ name: 'sender_name', required: false, label: 'Sender name', envelope: true, type: 'text' }] },
      ]),
    })
    const envelope = await screen.findByRole('region', { name: 'Envelope' })
    expect(await within(envelope).findByLabelText(/^Sender name/)).toHaveValue('Ana from Travel')
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

  it('adds two columns side by side as two Column modules (ADR-198 point 4)', async () => {
    const { handlers } = server({ accepted: ['column', 'cta'] })
    let next = 13
    const fetchMock = open({
      ...handlers,
      'POST /campaigns/variants/3/modules': () => jsonResponse({ id: next++ }),
    })
    fireEvent.click(await screen.findByRole('button', { name: /Add a module/ }))
    fireEvent.click(await screen.findByRole('option', { name: 'Two columns' }))
    fireEvent.click(screen.getByRole('button', { name: 'Add' }))
    await waitFor(() => expect(sent(fetchMock, 'POST')).toHaveLength(2))
    for (const request of sent(fetchMock, 'POST')) expect(await request.json()).toEqual({ module_type: 'column' })
  })

  it('offers no add when the channel is full', async () => {
    open(server({ canAdd: false }).handlers)
    await screen.findByLabelText(/^Subject/)
    expect(screen.queryByRole('button', { name: 'Add' })).not.toBeInTheDocument()
  })
})

describe('the brand profile', () => {
  const CALM = { id: 2, name: 'Calm', language: 'en', kind: 'marketing', is_default: false,
    complete: true, missing: [], updated_at: T(1) }
  const DEFAULT = { ...CALM, id: 1, name: 'Default', is_default: true }

  function withProfiles(profile: Record<string, unknown> = {}) {
    const { state, puts, handlers } = server()
    const composed = handlers['GET /campaigns/1/composition']
    return {
      state, puts,
      handlers: {
        ...handlers,
        // The composition as the server reports it, with the profile in use.
        'GET /campaigns/1/composition': async () => {
          const body = await composed().json()
          body.variants[0].brand_profile = { ...A_BRAND_PROFILE, ...profile }
          return jsonResponse(body)
        },
        'GET /brand-profiles/': () => jsonResponse({ items: [DEFAULT, CALM], total: 2, limit: 200, offset: 0 }),
        'GET /brand-profiles/structure': () => jsonResponse([
          { name: 'imprint_url', type: 'url', label: 'Imprint URL', group: 'Legal details',
            multiline: false, core: true, required_for: ['marketing'] },
        ]),
      },
    }
  }

  it('saves a chosen profile on the variant, with the version it read', async () => {
    const { puts, handlers } = withProfiles()
    open(handlers)
    fireEvent.click(await screen.findByRole('button', { name: /Default \(default\) · en/ }))
    fireEvent.click(await screen.findByRole('option', { name: 'Calm · en' }))
    await waitFor(() => expect(puts).toHaveLength(1))
    expect(puts[0].headers.get('If-Match')).toBe(T(1))
    expect(await puts[0].json()).toMatchObject({ name: 'Variant A', brand_profile_id: 2 })
  })

  it('says plainly when the profile sends without the opt-in check', async () => {
    open(withProfiles({ kind: 'transactional', name: 'Receipts' }).handlers)
    expect(await screen.findByText('Sent without opt-in check.')).toBeInTheDocument()
  })

  it('says why the profile changed, and what it still lacks, in words', async () => {
    open(withProfiles({ notice: 'Its brand profile "Summer" was deleted, so it now uses the default "Default".',
      missing: ['imprint_url'] }).handlers)
    expect(await screen.findByText(/Its brand profile "Summer" was deleted/)).toBeInTheDocument()
    expect(await screen.findByText(/This profile is incomplete: Imprint URL\./)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Fill it in' })).toHaveAttribute('href', '/settings/brand-profiles/1')
  })
})

// `act` is imported for React's sake in some environments; keep the linter quiet.
void act

const RUN = {
  run_id: 70, status: 'ok', created_at: T(0), provider: 'mock', model: 'mock-1', prompt_version: 2,
  input_tokens: 100, output_tokens: 20, reply: '', message: null, pending_action_id: null,
  notices: ['Only two options came back.'],
  options: [{ subject: 'Lisbon awaits', preheader: 'Three days of sun' }, { subject: 'Pack light', preheader: '' }],
}

describe('AI subject and preheader suggestions (task-367)', () => {
  it('shows the newest run, and "Use this" saves subject and preheader together, naming the run', async () => {
    const { handlers, puts } = server()
    open({ ...handlers, 'GET /campaigns/variants/3/suggestions': () => jsonResponse([RUN, { ...RUN, run_id: 60 }]) })
    const list = await screen.findByRole('list', { name: 'Suggested subjects' })
    expect(screen.getByText('Only two options came back.')).toBeInTheDocument()
    expect(screen.getByText(/120 tokens/)).toBeInTheDocument()
    fireEvent.click(within(list).getByRole('button', { name: 'Use "Lisbon awaits"' }))
    await waitFor(() => expect(puts).toHaveLength(1))
    expect(puts[0].headers.get('If-Match')).toBe(T(1))
    expect(await puts[0].json()).toEqual({
      name: 'Variant A', envelope: { subject: 'Lisbon awaits', preheader: 'Three days of sun' }, applied_suggestion_run_id: 70,
    })
  })

  it('asks once while the model works, then shows what it answered', async () => {
    const { handlers } = server()
    let runs: unknown[] = []
    let answer: (r: Response) => void = () => {}
    const fetchMock = open({
      ...handlers,
      'GET /campaigns/variants/3/suggestions': () => jsonResponse(runs),
      'POST /campaigns/variants/3/suggest-subject': () => new Promise<Response>((resolve) => (answer = resolve)),
    })
    fireEvent.click(await screen.findByRole('button', { name: 'Suggest with AI' }))
    const busy = await screen.findByRole('button', { name: 'Asking the model…' })
    expect(busy).toBeDisabled()
    fireEvent.click(busy)
    expect(sent(fetchMock, 'POST')).toHaveLength(1)
    runs = [RUN]
    await act(async () => answer(jsonResponse({ outcome: 'inline', message: null, ai_run_id: 70, pending_action_id: null })))
    expect(await screen.findByText('Lisbon awaits')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Suggest with AI' })).toBeEnabled()
  })

  it('says why a request was refused, in words', async () => {
    const { handlers } = server()
    open({
      ...handlers,
      'POST /campaigns/variants/3/suggest-subject': () =>
        jsonResponse({ detail: { reason: 'nothing_to_work_from', message: 'Add some content first.' } }, 409),
    })
    fireEvent.click(await screen.findByRole('button', { name: 'Suggest with AI' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Add some content first.')
  })

  it('sends a held request to Approvals', async () => {
    const { handlers } = server()
    open({
      ...handlers,
      'POST /campaigns/variants/3/suggest-subject': () =>
        jsonResponse({ outcome: 'held', message: null, ai_run_id: 70, pending_action_id: 9 }),
    })
    fireEvent.click(await screen.findByRole('button', { name: 'Suggest with AI' }))
    expect(await screen.findByRole('link', { name: 'Open it in Approvals' })).toHaveAttribute('href', '/approvals/9')
  })

  it('offers no "Use this" on a run waiting for approval', async () => {
    const { handlers } = server()
    open({ ...handlers, 'GET /campaigns/variants/3/suggestions': () => jsonResponse([{ ...RUN, pending_action_id: 9 }]) })
    const list = await screen.findByRole('list', { name: 'Suggested subjects' })
    expect(within(list).queryByRole('button')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open it in Approvals' })).toHaveAttribute('href', '/approvals/9')
  })

  it('shows what the model said when no option could be read', async () => {
    const { handlers } = server()
    open({
      ...handlers,
      'GET /campaigns/variants/3/suggestions': () =>
        jsonResponse([{ ...RUN, options: [], notices: [], reply: 'I would have to invent the details.' }]),
    })
    expect(await screen.findByText('I would have to invent the details.')).toBeInTheDocument()
  })
})
