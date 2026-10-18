import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import CampaignDetail from './CampaignDetail'
import { CampaignsSplit, NoCampaignOpen } from './Campaigns'
import { keys } from '../api/resources'
import { jsonResponse, makeQueryClient, page, renderWithProviders, stubFetch, A_BRAND_PROFILE } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const STAMP = '2026-10-02T09:00:00Z'

function module(id: number, position: number, extra: object = {}) {
  return {
    id,
    position,
    module_type: 'img_left',
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
      has_envelope: true, brand_profile: A_BRAND_PROFILE,
      accepted_module_types: ['img_left', 'cta'],
      envelope_modules: [
        module(9, 0, { module_type: 'envelope', module_data: { subject: 'Spring is here' } }),
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

// task-58: nothing has gone out, so there is no results section.
const NO_RESULTS = {
  campaign: null, variants: [], unsubscribes_counted_since: '2026-10-12T00:00:00Z', unsubscribes_partial: false,
}

function figures(extra: object = {}) {
  return {
    recipients: 10, sent: 8, delivered: 7, failed: 1, excluded: 1, excluded_by_stage: { consent: 1 },
    bounced: 1, complaints: 0, clicks_total: 5, unique_clickers: 3, click_rate: 0.375, unsubscribes: 2,
    ...extra,
  }
}

function renderDetail() {
  return renderWithProviders(
    <Routes>
      <Route path="/campaigns/:id" element={<CampaignDetail />} />
    </Routes>,
    { route: '/campaigns/1' },
  )
}

function renderSplit(route = '/campaigns', client = makeQueryClient()) {
  return renderWithProviders(
    <Routes>
      <Route element={<CampaignsSplit />}>
        <Route path="/campaigns" element={<NoCampaignOpen />} />
        <Route path="/campaigns/:id" element={<CampaignDetail />} />
      </Route>
      <Route path="/campaigns/:id/variants/:variantId" element={<p>editor 7/21</p>} />
    </Routes>,
    { route, client },
  )
}

describe('the campaign list', () => {
  it('opens a campaign beside the list, keeping the search, and marks it as the one open', async () => {
    const fetchMock = stubFetch({
      'GET /campaigns/': () => jsonResponse(page([COMPOSITION.campaign])),
      'GET /campaigns/1/results': () => jsonResponse(NO_RESULTS),
      'GET /campaigns/1/composition': () => jsonResponse(COMPOSITION),
    })
    renderSplit('/campaigns?q=spr')
    expect(screen.getByText('Select a campaign to see it.')).toBeInTheDocument()
    fireEvent.click(await screen.findByText('Spring'))
    expect(await screen.findByRole('heading', { name: 'Variant A' })).toBeInTheDocument()
    // The list stays beside the campaign, narrowed as it was.
    const row = within(screen.getByRole('grid', { name: 'Campaigns' })).getByRole('row', { name: /Spring/ })
    expect(row).toHaveAttribute('aria-selected', 'true')
    const reads = fetchMock.mock.calls.map(([r]) => new URL((r as Request).url))
    expect(reads.filter((u) => u.pathname === '/campaigns/').every((u) => u.searchParams.get('q') === 'spr')).toBe(true)
  })
  it('starts the next campaign with an empty blank-variant name', async () => {
    const other = { ...COMPOSITION, campaign: { ...COMPOSITION.campaign, id: 2, name: 'Autumn' } }
    // Cached, as a campaign already visited is: a loading screen would unmount
    // the form and hide the carry-over (Codex doc-33's point about approvals).
    const client = makeQueryClient()
    client.setQueryData(keys.composition(2), other)
    stubFetch({
      'GET /campaigns/': () => jsonResponse(page([COMPOSITION.campaign, other.campaign])),
      'GET /settings': () => jsonResponse(CHANNELS),
      'GET /campaigns/1/results': () => jsonResponse(NO_RESULTS),
      'GET /campaigns/2/results': () => jsonResponse(NO_RESULTS),
      'GET /campaigns/1/composition': () => jsonResponse(COMPOSITION),
      'GET /campaigns/2/composition': () => jsonResponse(other),
    })
    renderSplit('/campaigns/1', client)
    await screen.findByRole('heading', { name: 'Spring', level: 2 })
    const blank = () => screen.getByRole('region', { name: 'New blank variant' })
    fireEvent.change(within(blank()).getByLabelText(/^Name/), { target: { value: 'Plain' } })
    fireEvent.click(within(screen.getByRole('grid', { name: 'Campaigns' })).getByText('Autumn'))
    await screen.findByRole('heading', { name: 'Autumn', level: 2 })
    expect(within(blank()).getByLabelText(/^Name/)).toHaveValue('')
  })
})

describe('a campaign in detail', () => {
  it('sums a variant up, the envelope and the limit as the server gives them, with no module table', async () => {
    stubFetch({
      'GET /campaigns/1/composition': () => jsonResponse(COMPOSITION),
      'GET /campaigns/1/results': () => jsonResponse(NO_RESULTS),
    })
    renderDetail()

    expect(await screen.findByText('Spring is here')).toBeInTheDocument()
    expect(screen.getByText('3 of 10')).toBeInTheDocument()
    // A summary is enough on the campaign (2026-10-18): the modules are the editor's.
    expect(screen.queryByRole('grid', { name: 'Modules of Variant A' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Top pick' })).toHaveAttribute('href', '/decision-slots/5')
  })

  it('offers Edit, Preview and Send, and previews the variant in its sheet', async () => {
    stubFetch({
      'GET /campaigns/1/composition': () => jsonResponse(COMPOSITION),
      'GET /campaigns/1/results': () => jsonResponse(NO_RESULTS),
      'GET /modules': () => jsonResponse([]),
      'GET /rendering/variants/3': () =>
        jsonResponse({ variant_id: 3, channel: 'email', role: 'html', artifact_body: '<p>Hi</p>', fields: {}, modules: [] }),
    })
    renderDetail()
    const card = (await screen.findByRole('heading', { name: 'Variant A' })).closest('section')!
    const actions = [...card.querySelectorAll('.group-actions .btnrow > *')].map((a) => a.textContent)
    expect(actions).toEqual(['Edit Variant A', 'Preview', 'Send Variant A…', 'Suggest an audience…', 'Duplicate this variant'])
    fireEvent.click(within(card).getByRole('button', { name: 'Preview' }))
    const sheet = await screen.findByRole('dialog', { name: 'Preview of Variant A' })
    expect(await within(sheet).findByTitle('Rendered email: Variant A')).toBeInTheDocument()
  })

  it("suggests an audience per variant, in the variant's language, after asking, and opens it", async () => {
    // ADR-188 addendum 2026-10-18: a variant's topics in its language, not the campaign's.
    const writes: Request[] = []
    stubFetch({
      'GET /campaigns/1/composition': () => jsonResponse(COMPOSITION),
      'GET /campaigns/1/results': () => jsonResponse(NO_RESULTS),
      'POST /api/audience-groups/suggested': (r) => (writes.push(r.clone()), jsonResponse({ id: 21, name: 'Suggested' }, 201)),
    })
    renderWithProviders(
      <Routes>
        <Route path="/campaigns/:id" element={<CampaignDetail />} />
        <Route path="/audiences/:id" element={<h1>Audience page</h1>} />
      </Routes>,
      { route: '/campaigns/1' },
    )
    const card = (await screen.findByRole('heading', { name: 'Variant A' })).closest('section')!
    expect(screen.getAllByRole('button', { name: /Suggest an audience/ })).toHaveLength(1)
    fireEvent.click(within(card).getByRole('button', { name: 'Suggest an audience…' }))
    const dialog = await screen.findByRole('dialog', { name: 'Suggest an audience for Variant A' })
    expect(dialog).toHaveTextContent(/each limited to readers whose language is en/)
    expect(writes).toHaveLength(0)
    fireEvent.click(within(dialog).getByRole('button', { name: 'Suggest' }))
    expect(await screen.findByRole('heading', { name: 'Audience page' })).toBeInTheDocument()
    expect(await writes[0].json()).toEqual({ variant_id: 3 })
  })

  it('duplicates with an empty body, so the server picks the mode, then re-reads', async () => {
    /**
     * The default content mode is a server rule (keep inside the own campaign,
     * layout elsewhere). A body naming a mode would be the client deciding it.
     */
    let reads = 0
    const fetchMock = stubFetch({
      'GET /campaigns/1/results': () => jsonResponse(NO_RESULTS),
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
      'GET /campaigns/1/results': () => jsonResponse(NO_RESULTS),
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
    renderSplit()
    // "New ..." opens a dialog (task-372, decision 22), in place of the inline form.
    fireEvent.click(await screen.findByRole('button', { name: 'New campaign' }))
    const dialog = await screen.findByRole('dialog', { name: 'New campaign' })
    fireEvent.change(within(dialog).getByLabelText(/^Name/), { target: { value: 'Autumn' } })
    // Only the switched-on channel is offered.
    await waitFor(() => expect(within(dialog).getByRole('button', { name: /email/ })).toBeInTheDocument())
    fireEvent.click(within(dialog).getByRole('button', { name: 'Create campaign' }))
    expect(await screen.findByText('editor 7/21')).toBeInTheDocument()
    const post = fetchMock.mock.calls.map(([r]) => r as Request).find((r) => r.method === 'POST')!
    expect(await post.clone().json()).toEqual({
      name: 'Autumn', channel: 'email', status: 'draft', initial_variant_name: 'Variant A',
    })
  })

  it('closes the dialog on Cancel without creating anything', async () => {
    const fetchMock = stubFetch({
      'GET /campaigns/': () => jsonResponse(page([])),
      'GET /settings': () => jsonResponse(CHANNELS),
    })
    renderSplit()
    fireEvent.click(await screen.findByRole('button', { name: 'New campaign' }))
    const dialog = await screen.findByRole('dialog', { name: 'New campaign' })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(fetchMock.mock.calls.some(([r]) => (r as Request).method === 'POST')).toBe(false)
  })

  it('creates a blank variant below the variants and opens it in the editor', async () => {
    const fetchMock = stubFetch({
      'GET /campaigns/1/results': () => jsonResponse(NO_RESULTS),
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
    const blank = screen.getByRole('region', { name: 'New blank variant' })
    fireEvent.change(within(blank).getByLabelText(/^Name/), { target: { value: 'Plain' } })
    await waitFor(() => expect(within(blank).getByRole('button', { name: /email/ })).toBeInTheDocument())
    fireEvent.click(within(blank).getByRole('button', { name: 'Create blank variant' }))
    expect(await screen.findByText('editor 1/22')).toBeInTheDocument()
    const post = fetchMock.mock.calls.map(([r]) => r as Request).find((r) => r.method === 'POST')!
    expect(await post.clone().json()).toEqual({ name: 'Plain', channel: 'email', status: 'draft' })
  })
})

describe('the results section (task-58)', () => {
  it('shows the whole campaign and each variant that sent, as the server counts them', async () => {
    stubFetch({
      'GET /campaigns/1/composition': () => jsonResponse(COMPOSITION),
      'GET /campaigns/1/results': () => jsonResponse({
        campaign: figures(),
        variants: [
          { id: 3, name: 'Variant A', channel: 'email', ...figures() },
          { id: 4, name: 'Push', channel: 'push', ...figures({ delivered: null, click_rate: null }) },
        ],
        unsubscribes_counted_since: '2026-10-12T00:00:00Z',
        unsubscribes_partial: true,
      }),
    })
    renderDetail()
    // Two tables (task-372, decision 15): delivery, then engagement, each with the whole campaign on top.
    const delivery = await screen.findByRole('grid', { name: 'Delivery by variant' })
    const rows = within(delivery).getAllByRole('row')
    expect(rows[1]).toHaveTextContent('Whole campaign')
    expect(rows[1]).toHaveClass('row-total')
    expect(rows[2]).not.toHaveClass('row-total')
    expect(within(rows[1]).getByText('consent 1')).toBeInTheDocument()
    expect(rows[2]).toHaveTextContent('Variant A (email)')
    // Push reports no deliveries.
    expect(within(rows[3]).getAllByText('—')).toHaveLength(1)
    const engagement = screen.getByRole('grid', { name: 'Engagement by variant' })
    const used = within(engagement).getAllByRole('row')
    expect(used[1]).toHaveTextContent('Whole campaign')
    expect(used[1]).toHaveTextContent('37.5 %')
    // With nothing delivered there is no rate.
    expect(within(used[3]).getAllByText('—')).toHaveLength(1)
    expect(screen.getByText(/Unsubscribes made before .* are not counted/)).toBeInTheDocument()
  })

  it('has no section while nothing has gone out', async () => {
    stubFetch({
      'GET /campaigns/1/composition': () => jsonResponse(COMPOSITION),
      'GET /campaigns/1/results': () => jsonResponse(NO_RESULTS),
    })
    renderDetail()
    expect(await screen.findByRole('heading', { name: 'Spring' })).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByText('Results')).not.toBeInTheDocument())
    expect(screen.queryByRole('grid', { name: 'Delivery by variant' })).not.toBeInTheDocument()
  })

  it('leaves out the partial note when every send is counted in full', async () => {
    stubFetch({
      'GET /campaigns/1/composition': () => jsonResponse(COMPOSITION),
      'GET /campaigns/1/results': () => jsonResponse({
        campaign: figures(), variants: [{ id: 3, name: 'Variant A', channel: 'email', ...figures() }],
        unsubscribes_counted_since: '2026-10-12T00:00:00Z', unsubscribes_partial: false,
      }),
    })
    renderDetail()
    await screen.findByRole('grid', { name: 'Delivery by variant' })
    expect(screen.getByText(/Opens are not counted\./)).toBeInTheDocument()
    expect(screen.queryByText(/Unsubscribes made before/)).not.toBeInTheDocument()
  })
})
