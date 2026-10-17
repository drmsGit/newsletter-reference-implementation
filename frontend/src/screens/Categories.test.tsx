import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import Categories from './Categories'
import CategoryDetail from './CategoryDetail'
import { jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const CATEGORIES = [
  { id: 1, name: 'Beach', type: 'main' },
  { id: 2, name: 'Family', type: 'sub' },
  { id: 3, name: 'City', type: 'main' },
]
const RELATIONS = [{ id: 9, parent_category_id: 1, child_category_id: 2, relation_type: 'parent_child', created_at: '2026-10-16T09:00:00Z' }]
const FIGURES = { deliveries: 10, picked: 0, clicks: 3, unique_clickers: 2, clicks_in_deliveries: 12, click_share: 0.25 }
const DETAIL = {
  category: { id: 2, name: 'Family', type: 'sub' },
  parents: [{ id: 1, name: 'Beach', type: 'main', relation_id: 9 }],
  children: [],
  assigned_content: [{ content_id: 42, title: 'Lisbon for families', score: 8, figures: FIGURES }],
  top_recipients: [],
  impact: { update_count: 4, total_delta: 6.5, avg_delta: 1.6 },
}

function server(options: { deleteBlocked?: boolean } = {}) {
  const writes: Request[] = []
  const handlers = {
    'GET /content/categories': () => jsonResponse(CATEGORIES),
    'GET /content/category-relations': () => jsonResponse(RELATIONS),
    'GET /insight/categories/2': () => jsonResponse(DETAIL),
    'POST /content/categories': (r: Request) => (writes.push(r.clone()), jsonResponse({ id: 7, name: 'Wellness', type: 'sub' })),
    'PATCH /content/categories/2': (r: Request) => (writes.push(r.clone()), jsonResponse({ id: 2, name: 'Families', type: 'sub' })),
    'POST /content/category-relations': (r: Request) => (writes.push(r.clone()), jsonResponse({ ...RELATIONS[0], id: 10 })),
    'DELETE /content/category-relations/9': (r: Request) => (writes.push(r.clone()), new Response(null, { status: 204 })),
    'DELETE /content/categories/2': (r: Request) => {
      writes.push(r.clone())
      const force = new URL(r.url).searchParams.get('force') === 'true'
      return options.deleteBlocked && !force
        ? jsonResponse({ detail: { message: 'has links', counts: { content_assignments: 1, category_relations: 1 } } }, 409)
        : jsonResponse({ status: 'deleted' })
    },
  }
  return { handlers, writes }
}

function open(route: string, options = {}) {
  const { handlers, writes } = server(options)
  stubFetch(handlers as never)
  renderWithProviders(
    <Routes>
      <Route path="/content/categories" element={<Categories />} />
      <Route path="/content/categories/:id" element={<CategoryDetail />} />
    </Routes>,
    { route },
  )
  return writes
}

describe('the category pages (task-359)', () => {
  it('lists every category with where it sits', async () => {
    open('/content/categories')
    const table = await screen.findByRole('grid', { name: 'Categories' })
    const family = within(table).getByText('Family').closest('[role="row"]') as HTMLElement
    expect(family).toHaveTextContent('Sub · under Beach')
    expect(family).toHaveTextContent('0 subcategories')
  })

  it('fills in where each sits when the links arrive after the categories (task-372)', async () => {
    const { handlers } = server()
    stubFetch({
      ...handlers,
      // The list caches each row's rendering: a row drawn before the links
      // came must still be redrawn with them.
      'GET /content/category-relations': () =>
        new Promise<Response>((resolve) => setTimeout(() => resolve(jsonResponse(RELATIONS)), 30)),
    } as never)
    renderWithProviders(
      <Routes>
        <Route path="/content/categories" element={<Categories />} />
      </Routes>,
      { route: '/content/categories' },
    )
    const table = await screen.findByRole('grid', { name: 'Categories' })
    const row = (name: string) => within(table).getByText(name).closest('[role="row"]') as HTMLElement
    await waitFor(() => expect(row('Family')).toHaveTextContent('Sub · under Beach'))
    expect(row('Beach')).toHaveTextContent('1 subcategory')
  })

  it('creates a category of a type', async () => {
    const writes = open('/content/categories')
    // "New category" opens a dialog (task-372, decision 22).
    fireEvent.click(await screen.findByRole('button', { name: 'New category' }))
    const dialog = await screen.findByRole('dialog', { name: 'New category' })
    fireEvent.change(within(dialog).getByRole('textbox', { name: 'New category' }), { target: { value: 'Wellness' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Create' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toEqual({ name: 'Wellness', type: 'main' })
  })

  it("shows this brand's records in it with how each did", async () => {
    open('/content/categories/2')
    const table = await screen.findByRole('grid', { name: 'Records in this category' })
    expect(within(table).getByText('Lisbon for families')).toBeInTheDocument()
    expect(within(table).getByText('25 %')).toBeInTheDocument()
  })

  it("says what to choose in the client's words, not the browser's", async () => {
    open('/content/categories/2')
    expect(await screen.findAllByText('Choose a category')).toHaveLength(2)
  })

  it('renames it', async () => {
    const writes = open('/content/categories/2')
    fireEvent.change(await screen.findByLabelText('Name'), { target: { value: 'Families' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toEqual({ name: 'Families', type: 'sub' })
  })

  it('removes and adds a link to another category', async () => {
    const writes = open('/content/categories/2')
    fireEvent.click(await screen.findByRole('button', { name: 'Remove link' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(new URL(writes[0].url).pathname).toBe('/content/category-relations/9')
    fireEvent.click(screen.getByRole('button', { name: /Add a subcategory/ }))
    fireEvent.click(await screen.findByRole('option', { name: 'City' }))
    fireEvent.click(screen.getAllByRole('button', { name: 'Add' })[1])
    await waitFor(() => expect(writes).toHaveLength(2))
    expect(await writes[1].json()).toEqual({ parent_category_id: 2, child_category_id: 3, relation_type: 'parent_child' })
  })

  it('asks again before deleting one that still has records or links', async () => {
    const writes = open('/content/categories/2', { deleteBlocked: true })
    fireEvent.click(await screen.findByRole('button', { name: 'Delete category…' }))
    fireEvent.click(screen.getByRole('button', { name: 'Delete Family' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Delete it with them' }))
    await waitFor(() => expect(writes).toHaveLength(2))
    expect(new URL(writes[0].url).searchParams.get('force')).toBe('false')
    expect(new URL(writes[1].url).searchParams.get('force')).toBe('true')
  })
})
