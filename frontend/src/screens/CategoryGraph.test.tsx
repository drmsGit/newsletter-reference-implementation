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

describe('the category graph (task-359; tidied 2026-10-17, as Obsidian draws one)', () => {
  it('puts main categories inside and the rest outside, small dots that grow with picks', () => {
    const place = layout(GRAPH.nodes)
    const distance = (id: number) => Math.hypot(place.get(id)!.x - 600, place.get(id)!.y - 300)
    expect(distance(1)).toBeCloseTo(160, 0)
    expect(distance(3)).toBeCloseTo(160, 0)
    expect(distance(2)).toBeGreaterThan(200)
    expect(place.get(1)!.r).toBe(10)   // the most picked
    expect(place.get(3)!.r).toBe(4)    // never picked
  })

  it('draws each category as a button that says its figures and trend in words', async () => {
    open()
    const beach = await screen.findByRole('button', { name: /^Beach: 2 records, picked 3 times, signal 10 \(rising\)/ })
    expect(beach).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('button', { name: /^Family: .*\(falling\)/ })).toBeInTheDocument()
  })

  it('shows no names or symbols until a dot is hovered, then its name, its links and its neighbours', async () => {
    open()
    const beach = await screen.findByRole('button', { name: /^Beach:/ })
    const drawing = beach.closest('svg')!
    expect(drawing.querySelectorAll('text')).toHaveLength(0)
    expect(drawing.textContent).not.toMatch(/[▲▼]/)
    fireEvent.mouseEnter(beach)
    expect([...drawing.querySelectorAll('text')].map((t) => t.textContent)).toEqual(['Beach'])
    expect(drawing.querySelector('.graph-edge')).toHaveClass('graph-edge--lit')
    expect(screen.getByRole('button', { name: /^Family:/ })).not.toHaveClass('graph-node--faded')
    expect(screen.getByRole('button', { name: /^City:/ })).toHaveClass('graph-node--faded')
    fireEvent.mouseLeave(beach)
    expect(drawing.querySelectorAll('text')).toHaveLength(0)
  })

  it('does on keyboard focus what it does on hover', async () => {
    open()
    const family = await screen.findByRole('button', { name: /^Family:/ })
    fireEvent.focus(family)
    expect([...family.closest('svg')!.querySelectorAll('text')].map((t) => t.textContent)).toEqual(['Family'])
  })

  it("shows a chosen category's details below the drawing, every figure in a table", async () => {
    open()
    fireEvent.keyDown(await screen.findByRole('button', { name: /^Beach:/ }), { key: 'Enter' })
    const details = await screen.findByRole('region', { name: 'Beach' })
    const figures = await within(details).findByRole('grid', { name: 'Figures of Beach' })
    expect(within(figures).getByText('rising')).toBeInTheDocument()
    expect(within(within(details).getByRole('grid', { name: 'Relations of Beach' })).getByText('Family')).toBeInTheDocument()
    const records = within(details).getByRole('grid', { name: 'Records in Beach' })
    expect(within(records).getByText('Lisbon beaches')).toBeInTheDocument()
    expect(within(records).getByText('25 %')).toBeInTheDocument()
    // Below the drawing, not beside it.
    expect(screen.queryByRole('complementary')).not.toBeInTheDocument()
    expect(details.compareDocumentPosition(screen.getByRole('group', { name: 'Category graph' }))
      & Node.DOCUMENT_POSITION_PRECEDING).toBeTruthy()
  })

  it('keeps no list of every category', async () => {
    open()
    await screen.findByRole('button', { name: /^Beach:/ })
    expect(screen.queryByRole('grid', { name: 'Categories in the graph' })).not.toBeInTheDocument()
  })
})
