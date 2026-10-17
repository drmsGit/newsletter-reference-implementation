import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import DecisionSlotDetail from './DecisionSlotDetail'
import DecisionSlots, { DecisionSlotsSplit, NoSlotOpen } from './DecisionSlots'
import { jsonResponse, page, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const LISTED = {
  id: 5,
  name: 'Top pick',
  decision_type: 'content_recommendation',
  decision_strategy: 'recipient_top_score',
  variant_id: 3,
  variant_name: 'Variant A',
  campaign_id: 1,
  campaign_name: 'Spring',
  resolution_count: 4,
  unique_content_count: 2,
  last_resolution_at: null,
}

const STATS = {
  slot: {
    id: 5,
    variant_id: 3,
    name: 'Top pick',
    decision_type: 'content_recommendation',
    decision_strategy: 'recipient_top_score',
    candidate_filter: { category_ids: [7] },
    strategy_config: { preference_score_weight: 10 },
    max_results: 1,
    created_at: '2026-10-01T09:00:00Z',
    updated_at: '2026-10-01T09:00:00Z',
  },
  variant_id: 3,
  variant_name: 'Variant A',
  campaign_id: 1,
  campaign_name: 'Spring',
  summary: {
    resolution_count: 4,
    unique_recipient_count: 4,
    unique_content_count: 2,
    avg_score: 7.5,
    min_score: 5,
    max_score: 9,
    last_resolution_at: '2026-10-02T09:00:00Z',
  },
  // The same record at two versions: two rows sharing a content_id.
  top_content: [
    { content_id: 42, title: 'Lisbon', version_number: 2, selection_count: 2, share: 50 },
    { content_id: 42, title: 'Lisbon', version_number: 1, selection_count: 1, share: 25 },
    { content_id: 43, title: 'Porto', version_number: 1, selection_count: 1, share: 25 },
  ],
  latest: [
    {
      id: 900, recipient_id: 17, content_record_id: 42, content_title: 'Lisbon',
      content_version: 2, score: 9, reason: 'strongest signal', created_at: '2026-10-02T09:00:00Z',
    },
  ],
  reasons: [{ reason: 'strongest signal', count: 3 }],
}

const CANDIDATES = { slot_id: 5, candidate_count: 12, category_ids: [7], requires_recipient: true }

function renderDetail() {
  return renderWithProviders(
    <Routes>
      <Route path="/decision-slots/:id" element={<DecisionSlotDetail />} />
      <Route path="/content/:id" element={<p>content screen</p>} />
    </Routes>,
    { route: '/decision-slots/5' },
  )
}

describe('the decision slot list', () => {
  it('shows each slot with its campaign and what it has picked, and opens it', async () => {
    stubFetch({ 'GET /campaigns/decision-slots': () => jsonResponse(page([LISTED])) })
    renderWithProviders(
      <Routes>
        <Route path="/decision-slots" element={<DecisionSlots />} />
        <Route path="/decision-slots/:id" element={<p>slot screen</p>} />
      </Routes>,
      { route: '/decision-slots' },
    )
    expect(await screen.findByText('Spring')).toBeInTheDocument()
    expect(screen.getByText('recipient_top_score')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Top pick'))
    expect(await screen.findByText('slot screen')).toBeInTheDocument()
  })
})

describe('the slots beside the open one (task-372)', () => {
  it('opens a slot beside the list, on the same page, and marks it as the one open', async () => {
    const fetchMock = stubFetch({
      'GET /campaigns/decision-slots': () => jsonResponse(page([LISTED])),
      'GET /campaigns/decision-slots/5/stats': () => jsonResponse(STATS),
      'GET /campaigns/decision-slots/5/candidates': () => jsonResponse(CANDIDATES),
    })
    renderWithProviders(
      <Routes>
        <Route element={<DecisionSlotsSplit />}>
          <Route path="/decision-slots" element={<NoSlotOpen />} />
          <Route path="/decision-slots/:id" element={<DecisionSlotDetail />} />
        </Route>
      </Routes>,
      { route: '/decision-slots?offset=50' },
    )
    expect(screen.getByText('Select a slot to see what it picks.')).toBeInTheDocument()
    fireEvent.click(await screen.findByText('Top pick'))
    expect(await screen.findByRole('heading', { name: 'Top pick', level: 2 })).toBeInTheDocument()
    const row = within(screen.getByRole('grid', { name: 'Decision slots' })).getByRole('row', { name: /Top pick/ })
    expect(row).toHaveAttribute('aria-selected', 'true')
    const reads = fetchMock.mock.calls
      .map(([r]) => new URL((r as Request).url))
      .filter((u) => u.pathname === '/campaigns/decision-slots')
    expect(reads.every((u) => u.searchParams.get('offset') === '50')).toBe(true)
  })
})

describe('a decision slot in detail', () => {
  it('shows its setup, what it chooses from and what it picked', async () => {
    stubFetch({
      'GET /campaigns/decision-slots/5/stats': () => jsonResponse(STATS),
      'GET /campaigns/decision-slots/5/candidates': () => jsonResponse(CANDIDATES),
    })
    renderDetail()

    expect(await screen.findByRole('heading', { name: 'Top pick' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Spring' })).toHaveAttribute('href', '/campaigns/1')
    expect(
      await screen.findByText(
        '12 active content records in categories #7. This strategy picks per recipient, so one person may be offered fewer.',
      ),
    ).toBeInTheDocument()
    expect(screen.getByText('preference_score_weight')).toBeInTheDocument()
    expect(screen.getByText('50%')).toBeInTheDocument()
    expect(screen.getByText('strongest signal — 3')).toBeInTheDocument()
    expect(screen.getByText('#17')).toBeInTheDocument()
  })

  it('never executes the slot to show it', async () => {
    // stubFetch throws on any unstubbed route, so a POST to .../execute
    // would fail the screen; the assertion makes the absence explicit.
    const fetch = stubFetch({
      'GET /campaigns/decision-slots/5/stats': () => jsonResponse(STATS),
      'GET /campaigns/decision-slots/5/candidates': () => jsonResponse(CANDIDATES),
    })
    renderDetail()
    await screen.findByText(/12 active content records/)
    const methods = fetch.mock.calls.map(([r]) => (r as Request).method)
    expect(methods.every((m) => m === 'GET')).toBe(true)
  })

  it('opens a picked record from the top content', async () => {
    stubFetch({
      'GET /campaigns/decision-slots/5/stats': () => jsonResponse(STATS),
      'GET /campaigns/decision-slots/5/candidates': () => jsonResponse(CANDIDATES),
    })
    renderDetail()
    fireEvent.click(await screen.findByText('Porto'))
    expect(await screen.findByText('content screen')).toBeInTheDocument()
  })

  it('says when the slot is not in this brand', async () => {
    stubFetch({
      'GET /campaigns/decision-slots/5/stats': () => jsonResponse({ detail: 'Decision slot 5 not found' }, 404),
      'GET /campaigns/decision-slots/5/candidates': () => jsonResponse({ detail: 'nf' }, 404),
    })
    renderDetail()
    expect(await screen.findByText(/not found|does not exist/i)).toBeInTheDocument()
  })
})
