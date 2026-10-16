import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import CategoryGraph, { layout } from './CategoryGraph'
import { jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const node = (id: number, name: string, type: string, extra = {}) => ({
  id, name, type, selected_count: 0, content_count: 2, update_count: 0, event_count: 0, total_delta: 0, avg_delta: 0,
  parent_count: 0, child_count: 0, ...extra,
})
const GRAPH = {
  brand_id: 1,
  nodes: [
    node(1, 'Beach', 'main', { selected_count: 3, total_delta: 10, avg_delta: 2 }),
    node(2, 'Family', 'sub', { avg_delta: -1 }),
    node(3, 'City', 'main'),
  ],
  edges: [{ source: 1, target: 2, type: 'relation', cooccurrence_count: 1, event_count: 0, total_delta: 0, strength: 2 }],
}
const FIGURES = { deliveries: 10, picked: 0, clicks: 3, unique_clickers: 2, clicks_in_deliveries: 12, click_share: 0.25 }
const DETAIL = {
  category: { id: 1, name: 'Beach', type: 'main' },
  parents: [], children: [{ id: 2, name: 'Family', type: 'sub', relation_id: 9 }],
  assigned_content: [{ content_id: 42, title: 'Lisbon beaches', score: 9, figures: FIGURES }],
  top_recipients: [], impact: { update_count: 4, total_delta: 10, avg_delta: 2 },
}

function open() {
  stubFetch({
    'GET /insight/category-graph': () => jsonResponse(GRAPH),
    'GET /insight/categories/1': () => jsonResponse(DETAIL),
  } as never)
  renderWithProviders(<CategoryGraph />)
}

describe('the category graph (task-359)', () => {
  it('puts main categories inside and the rest outside, bigger for more picks and signal', () => {
    const place = layout(GRAPH.nodes)
    const distance = (id: number) => Math.hypot(place.get(id)!.x - 450, place.get(id)!.y - 310)
    expect(distance(1)).toBeCloseTo(150, 0)
    expect(distance(3)).toBeCloseTo(150, 0)
    expect(distance(2)).toBeGreaterThan(200)
    expect(place.get(1)!.r).toBe(16 + 3 * 4 + 10 * 0.4)
    expect(place.get(3)!.r).toBe(16)
  })

  it('draws each category as a button that says its figures and trend in words', async () => {
    open()
    const beach = await screen.findByRole('button', { name: /^Beach: 2 records, picked 3 times, signal 10 \(rising\)/ })
    expect(beach).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('button', { name: /^Family: .*\(falling\)/ })).toBeInTheDocument()
  })

  it("opens a category's records and their figures from the drawing by keyboard", async () => {
    open()
    fireEvent.keyDown(await screen.findByRole('button', { name: /^Beach:/ }), { key: 'Enter' })
    const panel = await screen.findByRole('complementary', { name: 'Selected category' })
    const records = await within(panel).findByRole('grid', { name: 'Records in Beach' })
    expect(within(records).getByText('Lisbon beaches')).toBeInTheDocument()
    expect(within(records).getByText('25 %')).toBeInTheDocument()
    expect(within(panel).getByText('Family')).toBeInTheDocument()
  })

  it('lists the same figures in a table', async () => {
    open()
    const table = await screen.findByRole('grid', { name: 'Categories in the graph' })
    const beach = within(table).getByText('Beach').closest('[role="row"]') as HTMLElement
    expect(within(beach).getByText('rising')).toBeInTheDocument()
  })
})
