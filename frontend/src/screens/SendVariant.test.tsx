import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import SendVariant from './SendVariant'
import { jsonResponse, page, renderWithProviders, stubFetch, A_BRAND_PROFILE } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const T = '2026-10-12T09:00:00Z'

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

function server(options: { channel?: string; now?: object } = {}) {
  const writes: Request[] = []
  const handlers = {
    'GET /campaigns/1/composition': () => jsonResponse(composition(options.channel)),
    'GET /settings': () => jsonResponse({ delivery_providers: PROVIDERS }),
    'GET /api/audience-groups/': () => jsonResponse(page([{ id: 5, name: 'Newsletter', created_at: T }])),
    'GET /api/audience-groups/5/preview': () =>
      jsonResponse({ resolved_count: 10, reachable_count: 8, dropped_by_stage: {}, items: [], total: 0 }),
    'POST /snapshots/variants/3': (request: Request) => {
      writes.push(request.clone())
      return jsonResponse({ id: 7, variant_id: 3, recipient_id: null, created_at: T, render_context: {} })
    },
    'POST /delivery/snapshots/7/send-instances': (request: Request) => {
      writes.push(request.clone())
      return jsonResponse({ id: 9, snapshot_id: 7, name: 'Spring', status: 'draft' }, 201)
    },
    'POST /delivery/send-instances/9/test': (request: Request) => {
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

async function choose(label: RegExp, option: string) {
  fireEvent.click(await screen.findByRole('button', { name: label }))
  fireEvent.click(await screen.findByRole('option', { name: option }))
}

describe('sending a variant (task-67)', () => {
  it('freezes the variant and shows exactly what will go out', async () => {
    const { handlers, writes } = server()
    open(handlers)
    fireEvent.click(await screen.findByRole('button', { name: 'Freeze this version' }))
    const frame = await screen.findByTitle('The frozen email')
    expect(frame).toHaveAttribute('src', '/snapshots/7/html')
    expect(writes).toHaveLength(1)
    expect(await screen.findByRole('heading', { name: '2. Plan the send' })).toBeInTheDocument()
  })

  it('plans the send with what was chosen, and nothing for a provider that needs no sender', async () => {
    const { handlers, writes } = server()
    open(handlers, '?snapshot=7')
    await choose(/Audience/, 'Newsletter')
    expect(await screen.findByText('8 of 10 in this group can be reached on email now.')).toBeInTheDocument()
    expect(screen.queryByLabelText('Sender address')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Plan the send' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toEqual({
      name: 'Spring', audience_group_id: 5, provider: 'mock', from_address: null,
      scheduled_at: null, skip_without_resolution: false,
    })
    expect(await screen.findByRole('heading', { name: '4. Send' })).toBeInTheDocument()
  })

  it('asks for a sender only for a provider that uses one, prefilled', async () => {
    const { handlers, writes } = server()
    open(handlers, '?snapshot=7')
    await choose(/Audience/, 'Newsletter')
    await choose(/Provider/, 'resend (real)')
    expect(await screen.findByLabelText('Sender address')).toHaveValue('news@example.org')
    fireEvent.click(screen.getByRole('checkbox', { name: /no content record/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Plan the send' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toMatchObject({
      provider: 'resend', from_address: 'news@example.org', skip_without_resolution: true,
    })
  })

  it('drops the sender again when switched back to a provider that needs none', async () => {
    const { handlers, writes } = server()
    open(handlers, '?snapshot=7')
    await choose(/Audience/, 'Newsletter')
    await choose(/Provider/, 'resend (real)')
    fireEvent.change(await screen.findByLabelText('Sender address'), { target: { value: 'typed@example.org' } })
    await choose(/Provider/, 'mock (nothing is sent)')
    fireEvent.click(screen.getByRole('button', { name: 'Plan the send' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toMatchObject({ provider: 'mock', from_address: null })
  })

  it('sends a test of the frozen email to one address', async () => {
    const { handlers, writes } = server()
    open(handlers, '?snapshot=7&send=9')
    fireEvent.change(await screen.findByLabelText('Test address'), { target: { value: 'me@example.org' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send a test' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toEqual({ to: 'me@example.org', recipient_id: null })
    expect(await screen.findByText('Test sent to me@example.org through mock.')).toBeInTheDocument()
  })

  it('a push has no test step', async () => {
    open(server({ channel: 'push' }).handlers, '?snapshot=7&send=9')
    expect(await screen.findByRole('heading', { name: '4. Send' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: '3. Send a test' })).not.toBeInTheDocument()
  })

  it('confirms with the count as of now, and fires', async () => {
    const { handlers, writes } = server()
    open(handlers, '?snapshot=7&send=9')
    fireEvent.click(await screen.findByRole('button', { name: 'Send to 3' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(new URL(writes[0].url).pathname).toBe('/delivery/send-instances/9/send')
    expect(await screen.findByText('Sent: sent.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: "The campaign's results" })).toHaveAttribute('href', '/campaigns/1')
  })

  it('spells out a real send', async () => {
    open(server({ now: { provider: 'resend', provider_label: 'resend (real)', reaches_real_inboxes: true,
      from_address: 'news@example.org' } }).handlers, '?snapshot=7&send=9')
    expect(await screen.findByRole('button', { name: 'Send real email to 3 people' })).toBeInTheDocument()
    expect(screen.getByRole('note')).toHaveTextContent('Real email')
  })

  it('says when the count is above the cap', async () => {
    open(server({ now: { recipients: 300 } }).handlers, '?snapshot=7&send=9')
    expect(await screen.findByRole('alert')).toHaveTextContent('above the limit of 200')
  })
})
