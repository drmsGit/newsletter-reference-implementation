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
    const fetchMock = stubFetch({ [`GET ${api}`]: () => jsonResponse(page([])) })
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

describe('filtering content by status', () => {
  it('sends the chosen status, from the URL', async () => {
    const fetchMock = stubFetch({ 'GET /content/': () => jsonResponse(page([])) })
    renderWithProviders(
      <Routes>
        <Route path="/content" element={<Content />} />
      </Routes>,
      { route: '/content?status=inactive' },
    )
    await waitFor(() => expect(lastQuery(fetchMock, '/content/').get('status')).toBe('inactive'))
  })
})
