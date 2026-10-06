import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import Recipients from './Recipients'
import RecipientDetail from './RecipientDetail'
import { jsonResponse, page, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const ANNA = {
  id: 7, external_id: 'crm-anna', email: 'anna@example.invalid', language: 'de', status: 'active',
  email_consent_status: 'opted_in', created_at: '2026-09-01T00:00:00Z', updated_at: '2026-09-01T00:00:00Z',
  addresses: [{ channel: 'email', value: 'anna@example.invalid', status: 'active', is_primary: true }],
  consent: [],
}

const ACTIVITY = {
  recipient_id: 7, external_id: 'crm-anna',
  preferences: [{ category_id: 3, category_name: 'Beach', score: 8.5 }],
  decisions: [{ id: 1, decision_slot_id: 4, content_record_id: 42, content_title: 'Lisbon in spring',
    content_version: 2, score: 9, reason: 'top_score', created_at: '2026-10-01T10:00:00Z' }],
  deliveries: [{ id: 5, send_instance_id: 11, send_instance_name: 'Spring edition', status: 'sent', channel: 'email',
    purpose: 'marketing', exclusion_reason: null, provider: 'mock', provider_message_id: 'm-1',
    sent_at: '2026-10-01T10:05:00Z', created_at: '2026-10-01T10:00:00Z', events: [] }],
  consent_grid: [
    { channel: 'email', purpose: 'marketing', status: 'opted_in', consenting: true, source: 'crm', recorded_at: '2026-09-01T00:00:00Z' },
    { channel: 'push', purpose: 'marketing', status: null, consenting: false, source: null, recorded_at: null },
  ],
  consent_history: [{ brand_id: 1, brand_name: 'Acme', channel: 'email', purpose: 'marketing', status: 'opted_in',
    source: 'crm', created_at: '2026-09-01T00:00:00Z' }],
}

const GROUPS = {
  email: [
    { group_id: 21, group_name: 'Germans', member: true, reasons: [{ kind: 'rule', label: 'Language de' }] },
    { group_id: 22, group_name: 'Spring sample', member: false,
      reasons: [{ kind: 'pinned', label: null }, { kind: 'excluded', label: 'Paused' }] },
  ],
  push: [
    { group_id: 21, group_name: 'Germans', member: false,
      reasons: [{ kind: 'rule', label: 'Language de' }, { kind: 'not_agreed', label: 'push' }] },
  ],
}

function server() {
  const asked: URLSearchParams[] = []
  const writes: Request[] = []
  const handlers = {
    'GET /recipients/': (request: Request) => {
      asked.push(new URL(request.url).searchParams)
      return jsonResponse(page([ANNA]))
    },
    'GET /recipients/7/activity': () => jsonResponse(ACTIVITY),
    'GET /recipients/7/audience-groups': (request: Request) => {
      const channel = new URL(request.url).searchParams.get('channel') as 'email' | 'push'
      asked.push(new URL(request.url).searchParams)
      return jsonResponse(page(GROUPS[channel]))
    },
    'GET /settings': () => jsonResponse({ channels: [{ name: 'email', available: true }, { name: 'push', available: true }] }),
  }
  const any = (request: Request) => {
    writes.push(request)
    return jsonResponse({}, 405)
  }
  return { asked, writes, handlers: { ...handlers, 'POST /recipients/': any, 'PUT /recipients/7': any } }
}

function open(route: string, handlers: Record<string, (r: Request) => Response>) {
  stubFetch(handlers as never)
  renderWithProviders(
    <Routes>
      <Route path="/recipients" element={<Recipients />} />
      <Route path="/recipients/:id" element={<RecipientDetail />} />
    </Routes>,
    { route },
  )
}

describe('the recipients list (task-292)', () => {
  it('finds a person by identifier or address on the server and opens them', async () => {
    const { handlers, asked } = server()
    open('/recipients', handlers)
    expect(await screen.findByText('crm-anna')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText(/Find a recipient/), { target: { value: 'anna' } })
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))
    await waitFor(() => expect(asked.at(-1)?.get('q')).toBe('anna'))
    fireEvent.click(await screen.findByText('crm-anna'))
    expect(await screen.findByRole('heading', { name: 'crm-anna' })).toBeInTheDocument()
  })
})

describe('one person: why did they get this (task-292)', () => {
  const section = (name: string) => screen.findByRole('region', { name })

  it('says it is read-only, and why', async () => {
    open('/recipients/7', server().handlers)
    expect(await screen.findByText(/Read-only/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Save|Edit|Delete|Unsubscribe/ })).not.toBeInTheDocument()
  })

  it('shows this brand\'s consent per channel, a cell never asked reading as not asked', async () => {
    open('/recipients/7', server().handlers)
    const consent = await section('Consent')
    const rows = within(consent).getAllByRole('row').map((r) => r.textContent)
    expect(rows.some((r) => r?.startsWith('emailmarketingopted_in'))).toBe(true)
    expect(rows.some((r) => r?.startsWith('pushmarketingNot asked'))).toBe(true)
  })

  it('shows the audience groups per channel with the reason, as of now', async () => {
    const { handlers, asked } = server()
    open('/recipients/7', handlers)
    const groups = await section('Audience groups')
    expect(await within(groups).findByRole('link', { name: 'Germans' })).toHaveAttribute('href', '/audiences/21')
    const rows = within(groups).getAllByRole('row').map((r) => r.textContent)
    expect(rows).toContain('GermansInMatched rule “Language de”')
    expect(rows).toContain('Spring sampleOutAdded by hand · Removed by exclusion “Paused”')
    expect(within(groups).getByText(/As of now/)).toBeInTheDocument()

    fireEvent.click(within(groups).getByRole('button', { name: /email/ }))
    fireEvent.click(await screen.findByRole('option', { name: 'push' }))
    await waitFor(() => expect(asked.at(-1)?.get('channel')).toBe('push'))
    expect(await within(groups).findByText('Matched rule “Language de” · Not agreed to push')).toBeInTheDocument()
  })

  it('lists what was sent, the decisions behind it and their interests, each linked', async () => {
    open('/recipients/7', server().handlers)
    const deliveries = await section('Deliveries')
    expect(within(deliveries).getByRole('link', { name: 'Spring edition' })).toHaveAttribute('href', '/deliveries/11')
    expect(within(deliveries).getByText('sent')).toBeInTheDocument()
    const decisions = await section('Decisions')
    expect(within(decisions).getByRole('link', { name: 'Lisbon in spring' })).toHaveAttribute('href', '/content/42')
    expect(within(decisions).getByText('top_score')).toBeInTheDocument()
    expect(within(await section('Interests')).getByText('Beach')).toBeInTheDocument()
    expect(within(await section('Consent history')).getByText('Acme')).toBeInTheDocument()
  })
})
