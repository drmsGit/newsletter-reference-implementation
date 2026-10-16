import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import SendVariant from './SendVariant'
import { jsonResponse, page, renderWithProviders, stubFetch, A_BRAND_PROFILE } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const T = '2026-10-13T09:00:00Z'

function composition(channel = 'email') {
  return {
    campaign: { id: 1, name: 'Spring', status: 'draft', created_at: T, updated_at: T },
    variants: [{
      variant: { id: 3, campaign_id: 1, channel, name: 'Variant A', status: 'draft', created_at: T, updated_at: T },
      module_limit: null, can_add_module: true, has_envelope: true, brand_profile: A_BRAND_PROFILE,
      accepted_module_types: [], envelope_modules: [], modules: [], decision_slots: [],
    }],
  }
}

const PROVIDERS = [
  { name: 'mock', label: 'mock (nothing is sent)', channels: ['email', 'push'], click_content_attribution: false,
    needs_from_address: false, default_from_address: null },
  { name: 'resend', label: 'resend (real)', channels: ['email'], click_content_attribution: true,
    needs_from_address: true, default_from_address: 'news@example.org' },
]

function now(extra: object = {}) {
  return {
    send_instance_id: 9, status: 'draft', recipients: 3, cap: 200, provider: 'mock',
    provider_label: 'mock (nothing is sent)', reaches_real_inboxes: false, from_address: null, scheduled_at: null,
    ...extra,
  }
}

function server(options: { channel?: string; now?: object; open?: object[] } = {}) {
  const writes: Request[] = []
  const handlers = {
    'GET /campaigns/1/composition': () => jsonResponse(composition(options.channel)),
    'GET /settings': () => jsonResponse({ delivery_providers: PROVIDERS }),
    'GET /snapshots/variants/3/preview': () =>
      jsonResponse(options.channel === 'push'
        ? { channel: 'push', subject: null, preheader: null, html: null, fields: { title: 'Hi there' } }
        : { channel: 'email', subject: 'Spring is here', preheader: 'Peek', html: '<p>Hello</p>', fields: null }),
    'GET /delivery/send-instances': () => jsonResponse(page(options.open ?? [])),
    'GET /api/audience-groups/': () => jsonResponse(page([{ id: 5, name: 'Newsletter', created_at: T }])),
    'GET /api/audience-groups/5/preview': () =>
      jsonResponse({ resolved_count: 10, reachable_count: 8, dropped_by_stage: {}, items: [], total: 0 }),
    'POST /delivery/variants/3/send-instances': (request: Request) => {
      writes.push(request.clone())
      return jsonResponse({ id: 9, snapshot_id: 7, name: 'Spring', status: 'draft' }, 201)
    },
    'POST /delivery/variants/3/test': (request: Request) => {
      writes.push(request.clone())
      return jsonResponse({ success: true, to: 'me@example.org', provider: 'mock' })
    },
    'GET /delivery/send-instances/9/recipients-now': () => jsonResponse(now(options.now)),
    'POST /delivery/send-instances/9/send': (request: Request) => {
      writes.push(request.clone())
      return jsonResponse({ status: 'sent' })
    },
  }
  return { handlers, writes }
}

function open(handlers: object, query = '') {
  stubFetch(handlers as never)
  renderWithProviders(
    <Routes>
      <Route path="/campaigns/:id/variants/:variantId/send" element={<SendVariant />} />
    </Routes>,
    { route: `/campaigns/1/variants/3/send${query}` },
  )
}

async function choose(label: RegExp, option: string, nth = 0) {
  fireEvent.click((await screen.findAllByRole('button', { name: label }))[nth])
  fireEvent.click(await screen.findByRole('option', { name: option }))
}

describe('sending a variant (task-67; ADR-183 addendum 2026-10-13)', () => {
  it('shows what goes out without freezing anything', async () => {
    const { handlers, writes } = server()
    open(handlers)
    const frame = await screen.findByTitle('What goes out')
    expect(frame).toHaveAttribute('srcdoc', '<p>Hello</p>')
    expect(screen.getByText(/Spring is here/)).toBeInTheDocument()
    expect(writes).toHaveLength(0)
    expect(screen.queryByRole('button', { name: /Freeze/ })).not.toBeInTheDocument()
  })

  it('sends a test any time, before planning, through the chosen provider', async () => {
    const { handlers, writes } = server()
    open(handlers)
    fireEvent.change(await screen.findByLabelText('Test address'), { target: { value: 'me@example.org' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send a test' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(new URL(writes[0].url).pathname).toBe('/delivery/variants/3/test')
    expect(await writes[0].json()).toEqual({ to: 'me@example.org', provider: 'mock', from_address: null, recipient_id: null })
    expect(await screen.findByText('Test sent to me@example.org through mock.')).toBeInTheDocument()
  })

  it('a push has no test step, and shows its fields', async () => {
    open(server({ channel: 'push' }).handlers)
    expect(await screen.findByText('Hi there')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /Send a test/ })).not.toBeInTheDocument()
  })

  it('planning freezes and plans in one go, with what was chosen', async () => {
    const { handlers, writes } = server()
    open(handlers)
    await choose(/Audience/, 'Newsletter')
    expect(await screen.findByText('8 of 10 in this group can be reached on email now.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Plan the send' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(new URL(writes[0].url).pathname).toBe('/delivery/variants/3/send-instances')
    expect(await writes[0].json()).toEqual({
      name: 'Spring', audience_group_id: 5, provider: 'mock', from_address: null,
      scheduled_at: null, skip_without_resolution: false,
    })
    expect(await screen.findByRole('heading', { name: '4. Send' })).toBeInTheDocument()
  })

  it('says what is missing instead of doing nothing', async () => {
    const { handlers, writes } = server()
    open(handlers)
    fireEvent.click(await screen.findByRole('button', { name: 'Plan the send' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Still needed: an audience.')
    expect(writes).toHaveLength(0)
  })

  it('prefills a complete time to send at, and plans it', async () => {
    const { handlers, writes } = server()
    open(handlers)
    await choose(/Audience/, 'Newsletter')
    await choose(/When/, 'At a time')
    const at = (await screen.findByLabelText('Send at')) as HTMLInputElement
    expect(at.value).toMatch(/^\d{4}-\d{2}-\d{2}T09:00$/)
    fireEvent.click(screen.getByRole('button', { name: 'Plan the send' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    const body = await writes[0].json()
    expect(new Date(body.scheduled_at).getTime()).toBe(new Date(at.value).getTime())
  })

  it('asks for a sender only for a provider that uses one, and drops it again', async () => {
    const { handlers, writes } = server()
    open(handlers)
    await choose(/Audience/, 'Newsletter')
    await choose(/Provider/, 'resend (real)', 1)
    const senders = await screen.findAllByLabelText('Sender address')
    expect(senders[senders.length - 1]).toHaveValue('news@example.org')
    fireEvent.change(senders[senders.length - 1], { target: { value: 'typed@example.org' } })
    await choose(/Provider/, 'mock (nothing is sent)', 1)
    fireEvent.click(screen.getByRole('button', { name: 'Plan the send' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toMatchObject({ provider: 'mock', from_address: null })
  })

  it('lists planned sends of this variant to continue', async () => {
    open(server({ open: [
      { id: 9, name: 'Spring', status: 'draft', created_at: T },
      { id: 8, name: 'Last week', status: 'sent', created_at: T },
    ] }).handlers)
    expect(await screen.findByText(/Spring — planned/)).toBeInTheDocument()
    expect(screen.queryByText(/Last week/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))
    expect(await screen.findByRole('heading', { name: '4. Send' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: '3. Plan the send' })).not.toBeInTheDocument()
  })

  it('confirms with the count as of now, and fires', async () => {
    const { handlers, writes } = server()
    open(handlers, '?send=9')
    fireEvent.click(await screen.findByRole('button', { name: 'Send to 3' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(new URL(writes[0].url).pathname).toBe('/delivery/send-instances/9/send')
    expect(await screen.findByText('Sent.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: "The campaign's results" })).toHaveAttribute('href', '/campaigns/1')
  })

  it('spells out a real send', async () => {
    open(server({ now: { provider: 'resend', provider_label: 'resend (real)', reaches_real_inboxes: true,
      from_address: 'news@example.org' } }).handlers, '?send=9')
    expect(await screen.findByRole('button', { name: 'Send real email to 3 people' })).toBeInTheDocument()
    expect(screen.getByRole('note')).toHaveTextContent('Real email')
  })

  it('says when the count is above the cap', async () => {
    open(server({ now: { recipients: 300 } }).handlers, '?send=9')
    expect(await screen.findByText(/above the limit of 200/)).toBeInTheDocument()
  })
})
