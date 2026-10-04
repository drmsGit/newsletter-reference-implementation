import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import CampaignDetail from './CampaignDetail'
import Campaigns from './Campaigns'
import { jsonResponse, page, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const STAMP = '2026-10-02T09:00:00Z'

function module(id: number, position: number, extra: object = {}) {
  return {
    id,
    position,
    module_type: 'single_stack',
    content_record_id: null,
    decision_slot_id: null,
    module_data: {},
    known: true,
    overrideable: false,
    active_override: null,
    ...extra,
  }
}

const COMPOSITION = {
  campaign: { id: 1, name: 'Spring', status: 'draft', created_at: STAMP, updated_at: STAMP },
  variants: [
    {
      variant: {
        id: 3, campaign_id: 1, channel: 'email', name: 'Variant A', status: 'draft',
        created_at: STAMP, updated_at: STAMP,
      },
      module_limit: 10,
      can_add_module: true,
      has_envelope: true,
      accepted_module_types: ['single_stack', 'cta'],
      envelope_modules: [
        module(9, 0, { module_type: 'header', module_data: { subject: 'Spring is here' } }),
      ],
      modules: [
        module(10, 1, {
          content_record_id: 42, content_record_title: 'Lisbon in spring', overrideable: true,
          active_override: { id: 1, field_overrides: { headline_medium: 'Short' }, overridden_by: 'sam', reason: null },
        }),
        module(11, 2, { decision_slot_id: 5 }),
        module(12, 3, { module_type: 'cta', module_data: { button_label: 'Book' } }),
      ],
      decision_slots: [
        {
          id: 5, name: 'Top pick', decision_type: 'content_recommendation',
          decision_strategy: 'top_score', variant_id: 3, variant_name: 'Variant A',
          campaign_id: 1, campaign_name: 'Spring', resolution_count: 8,
          unique_content_count: 3, last_resolution_at: null,
        },
      ],
    },
  ],
}

function renderDetail() {
  return renderWithProviders(
    <Routes>
      <Route path="/campaigns/:id" element={<CampaignDetail />} />
    </Routes>,
    { route: '/campaigns/1' },
  )
}

describe('the campaign list', () => {
  it('opens a campaign from its row', async () => {
    stubFetch({
      'GET /campaigns/': () => jsonResponse(page([COMPOSITION.campaign])),
      'GET /campaigns/1/composition': () => jsonResponse(COMPOSITION),
    })
    renderWithProviders(
      <Routes>
        <Route path="/campaigns" element={<Campaigns />} />
        <Route path="/campaigns/:id" element={<CampaignDetail />} />
      </Routes>,
      { route: '/campaigns' },
    )
    fireEvent.click(await screen.findByText('Spring'))
    expect(await screen.findByRole('heading', { name: 'Variant A' })).toBeInTheDocument()
  })
})

describe('a campaign in detail', () => {
  it("shows each module's source, the envelope and the limit as the server gives them", async () => {
    stubFetch({ 'GET /campaigns/1/composition': () => jsonResponse(COMPOSITION) })
    renderDetail()

    expect(await screen.findByText('Spring is here')).toBeInTheDocument()
    // The record's title, not its id (2026-10-04).
    expect(screen.getByRole('link', { name: 'Lisbon in spring' })).toHaveAttribute('href', '/content/42')
    expect(screen.getByRole('link', { name: 'Slot: Top pick' })).toHaveAttribute('href', '/decision-slots/5')
    expect(screen.getByRole('link', { name: 'Top pick' })).toHaveAttribute('href', '/decision-slots/5')
    expect(screen.getByText('Typed in the module')).toBeInTheDocument()
    // The fields, not just that there is an override (task-262).
    expect(screen.getByText('headline_medium by sam')).toBeInTheDocument()
    expect(screen.getByText('3 of 10')).toBeInTheDocument()
  })

  it('duplicates with an empty body, so the server picks the mode, then re-reads', async () => {
    /**
     * The default content mode is a server rule (keep inside the own campaign,
     * layout elsewhere). A body naming a mode would be the client deciding it.
     */
    let reads = 0
    const fetchMock = stubFetch({
      'GET /campaigns/1/composition': () => {
        reads += 1
        return jsonResponse(COMPOSITION)
      },
      'POST /campaigns/variants/3/duplicate': () =>
        jsonResponse({
          variant_id: 13, source_variant_id: 3, campaign_id: 1, source_campaign_id: 1,
          content_mode: 'keep', modules: 4, decision_slots: 1, url_carriers: [],
          overrides_carried: 1, overrides_not_carried: 0,
        }, 201),
    })
    renderDetail()

    fireEvent.click(await screen.findByRole('button', { name: 'Duplicate this variant' }))

    expect(await screen.findByRole('status')).toHaveTextContent(/same content/i)
    // task-113: the person duplicating is told they now author the carried override.
    expect(screen.getByRole('status')).toHaveTextContent(/1 override\(s\) came across/)
    const post = fetchMock.mock.calls
      .map(([input]) => input as Request)
      .find((r) => r.method === 'POST')!
    expect(await post.clone().json()).toEqual({})
    await waitFor(() => expect(reads).toBe(2))
  })

  it('says so when the person may not create variants', async () => {
    stubFetch({
      'GET /campaigns/1/composition': () => jsonResponse(COMPOSITION),
      'POST /campaigns/variants/3/duplicate': () => jsonResponse({ detail: 'no' }, 403),
    })
    renderDetail()

    fireEvent.click(await screen.findByRole('button', { name: 'Duplicate this variant' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/permission/i)
  })
})

// task-255: the two ways in, and the way to the editor.
const CHANNELS = { channels: [{ name: 'email', available: true }, { name: 'push', available: false }] }

describe('creating', () => {
  it('creates a campaign on an available channel and opens its first variant in the editor', async () => {
    const fetchMock = stubFetch({
      'GET /campaigns/': () => jsonResponse(page([])),
      'GET /settings': () => jsonResponse(CHANNELS),
      'POST /campaigns/': () => jsonResponse({ id: 7, name: 'Autumn', variants: [{ id: 21 }] }),
    })
    renderWithProviders(
      <Routes>
        <Route path="/campaigns" element={<Campaigns />} />
        <Route path="/campaigns/:id/variants/:variantId" element={<p>editor 7/21</p>} />
      </Routes>,
      { route: '/campaigns' },
    )
    fireEvent.change(await screen.findByLabelText(/^New campaign/), { target: { value: 'Autumn' } })
    // Only the switched-on channel is offered.
    await waitFor(() => expect(screen.getByRole('button', { name: /email/ })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Create campaign' }))
    expect(await screen.findByText('editor 7/21')).toBeInTheDocument()
    const post = fetchMock.mock.calls.map(([r]) => r as Request).find((r) => r.method === 'POST')!
    expect(await post.clone().json()).toEqual({
      name: 'Autumn', channel: 'email', status: 'draft', initial_variant_name: 'Variant A',
    })
  })

  it('creates a blank variant below the variants and opens it in the editor', async () => {
    const fetchMock = stubFetch({
      'GET /campaigns/1/composition': () => jsonResponse(COMPOSITION),
      'GET /settings': () => jsonResponse(CHANNELS),
      'POST /campaigns/1/variants': () => jsonResponse({ id: 22 }),
    })
    renderWithProviders(
      <Routes>
        <Route path="/campaigns/:id" element={<CampaignDetail />} />
        <Route path="/campaigns/:id/variants/:variantId" element={<p>editor 1/22</p>} />
      </Routes>,
      { route: '/campaigns/1' },
    )
    expect(await screen.findByRole('link', { name: 'Edit Variant A' })).toHaveAttribute(
      'href', '/campaigns/1/variants/3',
    )
    fireEvent.change(screen.getByLabelText(/^New blank variant/), { target: { value: 'Plain' } })
    await waitFor(() => expect(screen.getByRole('button', { name: /email/ })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Create blank variant' }))
    expect(await screen.findByText('editor 1/22')).toBeInTheDocument()
    const post = fetchMock.mock.calls.map(([r]) => r as Request).find((r) => r.method === 'POST')!
    expect(await post.clone().json()).toEqual({ name: 'Plain', channel: 'email', status: 'draft' })
  })
})
