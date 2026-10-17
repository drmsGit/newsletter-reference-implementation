import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes, useParams } from 'react-router'

import Content from './Content'
import { ContentMenu, ContentSplit, NothingOpen, RECORDS } from './ContentLayout'
import { jsonResponse, page, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const RECORD = { id: 42, title: 'Lisbon in spring', description: 'Three days', status: 'active', content: {} }

function Opened() {
  return <p>record {useParams().id}</p>
}

/** Content's drill-in (task-372, decision 20), routed as App routes it. */
function open(route: string) {
  const fetchMock = stubFetch({
    'GET /content/': () => jsonResponse(page([RECORD])),
    'GET /content/fields': () => jsonResponse([]),
    'GET /content/categories': () => jsonResponse([]),
    'GET /content/category-relations': () => jsonResponse([]),
  } as never)
  renderWithProviders(
    <Routes>
      <Route path="/content" element={<ContentSplit label="Content parts" list={<ContentMenu />} />}>
        <Route index element={<NothingOpen text="Choose records, categories or the graph." />} />
      </Route>
      <Route element={<ContentSplit label="Records" list={<Content />} />}>
        <Route path={RECORDS} element={<NothingOpen text="Select a record to see it." />} />
        <Route path="/content/:id" element={<Opened />} />
      </Route>
    </Routes>,
    { route },
  )
  return fetchMock
}

describe("Content's drill-in (task-372)", () => {
  it('starts with its parts, and Records opens the list with a way back', async () => {
    open('/content')
    const menu = screen.getByRole('navigation', { name: 'Content' })
    expect(within(menu).getByRole('link', { name: 'Categories' })).toHaveAttribute('href', '/content/categories')
    expect(within(menu).getByRole('link', { name: 'Graph' })).toHaveAttribute('href', '/content/graph')
    fireEvent.click(within(menu).getByRole('link', { name: 'Records' }))
    expect(await screen.findByRole('heading', { name: 'Records' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Content' })).toHaveAttribute('href', '/content')
  })

  it('opens a record beside the list, keeping the filters, and marks it as the one open', async () => {
    const fetchMock = open(`${RECORDS}?status=active`)
    fireEvent.click(await screen.findByText('Lisbon in spring'))
    expect(await screen.findByText('record 42')).toBeInTheDocument()
    const row = within(screen.getByRole('grid', { name: 'Content records' })).getByRole('row', { name: /Lisbon/ })
    expect(row).toHaveAttribute('aria-selected', 'true')
    const reads = fetchMock.mock.calls.map(([r]) => new URL((r as Request).url)).filter((u) => u.pathname === '/content/')
    expect(reads.every((u) => u.searchParams.get('status') === 'active')).toBe(true)
  })
})
