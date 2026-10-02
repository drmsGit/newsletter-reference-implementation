import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import CampaignDetail from './CampaignDetail'
import Campaigns from './Campaigns'
import { jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

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
          content_record_id: 42, overrideable: true,
          active_override: { id: 1, field_overrides: {}, overridden_by: 'sam', reason: null },
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
      'GET /campaigns/': () => jsonResponse([COMPOSITION.campaign]),
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
    expect(screen.getByRole('link', { name: 'Record #42' })).toHaveAttribute('href', '/content/42')
    expect(screen.getByText('Slot: Top pick')).toBeInTheDocument()
    expect(screen.getByText('Typed in the module')).toBeInTheDocument()
    expect(screen.getByText('Overridden by sam')).toBeInTheDocument()
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
        }, 201),
    })
    renderDetail()

    fireEvent.click(await screen.findByRole('button', { name: 'Duplicate this variant' }))

    expect(await screen.findByRole('status')).toHaveTextContent(/same content/i)
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
