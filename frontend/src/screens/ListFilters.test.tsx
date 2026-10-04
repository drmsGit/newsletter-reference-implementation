import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import Audiences from './Audiences'
import Campaigns from './Campaigns'
import Content from './Content'
import { jsonResponse, page, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

/** The search and filters reach the server (ADR-185 point 6), and a new
 * search starts from the first page. Decided 2026-10-03: existing fields only;
 * facets are their own work. */
function lastQuery(fetchMock: ReturnType<typeof stubFetch>, path: string) {
  const calls = fetchMock.mock.calls
    .map(([input]) => new URL((input as Request).url))
    .filter((u) => u.pathname === path)
  return calls[calls.length - 1].searchParams
}

function search(label: RegExp, words: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value: words } })
  fireEvent.click(screen.getByRole('button', { name: 'Search' }))
}

describe.each([
  ['campaigns', '/campaigns', '/campaigns/', <Campaigns />, /Find a campaign/],
  ['audiences', '/audiences', '/api/audience-groups/', <Audiences />, /Find an audience/],
  ['content', '/content', '/content/', <Content />, /Find content/],
] as const)('searching %s', (_name, route, api, element, label) => {
  it('sends the words to the server and starts from the first page', async () => {
    const fetchMock = stubFetch({ [`GET ${api}`]: () => jsonResponse(page([])), ...CATEGORY_ROUTES })
    renderWithProviders(
      <Routes>
        <Route path={route} element={element} />
      </Routes>,
      { route: `${route}?offset=50` },
    )
    await waitFor(() => expect(lastQuery(fetchMock, api).get('offset')).toBe('50'))
    search(label, 'spring')
    await waitFor(() => expect(lastQuery(fetchMock, api).get('q')).toBe('spring'))
    expect(lastQuery(fetchMock, api).get('offset')).toBe('0')
  })
})

const CATEGORY_ROUTES = {
  'GET /content/categories': () =>
    jsonResponse([{ id: 7, name: 'Coast', type: 'main' }, { id: 8, name: 'Beach', type: 'sub' }]),
  'GET /content/category-relations': () =>
    jsonResponse([{ id: 1, parent_category_id: 7, child_category_id: 8, relation_type: 'parent_child' }]),
}

describe('filtering content by category (task-270)', () => {
  function contentAt(route: string) {
    const fetchMock = stubFetch({ 'GET /content/': () => jsonResponse(page([])), ...CATEGORY_ROUTES })
    renderWithProviders(
      <Routes>
        <Route path="/content" element={<Content />} />
      </Routes>,
      { route },
    )
    return fetchMock
  }

  it('sends the category held in the URL', async () => {
    const fetchMock = contentAt('/content?category=8')
    await waitFor(() => expect(lastQuery(fetchMock, '/content/').get('category_id')).toBe('8'))
    expect(await screen.findByRole('button', { name: /Beach/ })).toBeInTheDocument()
    // Search reaches the description too since task-268, and says so.
    expect(screen.getByLabelText('Find content by title or description')).toBeInTheDocument()
  })

  it('sends a chosen category and starts from the first page', async () => {
    const fetchMock = contentAt('/content?offset=50')
    await waitFor(() => expect(lastQuery(fetchMock, '/content/').get('offset')).toBe('50'))
    fireEvent.click(screen.getByRole('button', { name: /Any category/ }))
    fireEvent.click(await screen.findByRole('option', { name: 'Beach' }))
    await waitFor(() => expect(lastQuery(fetchMock, '/content/').get('category_id')).toBe('8'))
    expect(lastQuery(fetchMock, '/content/').get('offset')).toBe('0')
  })

  it('says no record matches, not that the brand has none, when a filter empties the list', async () => {
    contentAt('/content?category=8')
    expect(await screen.findByText('No content matches these filters.')).toBeInTheDocument()
    expect(screen.queryByText('No content in this brand yet.')).not.toBeInTheDocument()
  })

  it('drops the category for "Any category"', async () => {
    const fetchMock = contentAt('/content?category=8')
    fireEvent.click(await screen.findByRole('button', { name: /Beach/ }))
    fireEvent.click(await screen.findByRole('option', { name: 'Any category' }))
    await waitFor(() => expect(lastQuery(fetchMock, '/content/').has('category_id')).toBe(false))
  })
})

describe('filtering content by status', () => {
  it('sends the chosen status, from the URL', async () => {
    const fetchMock = stubFetch({ 'GET /content/': () => jsonResponse(page([])), ...CATEGORY_ROUTES })
    renderWithProviders(
      <Routes>
        <Route path="/content" element={<Content />} />
      </Routes>,
      { route: '/content?status=inactive' },
    )
    await waitFor(() => expect(lastQuery(fetchMock, '/content/').get('status')).toBe('inactive'))
  })
})
