import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { Link, Route, Routes } from 'react-router'

import { keys } from '../api/resources'
import { jsonResponse, makeQueryClient, page, renderWithProviders, stubFetch } from '../test-utils'
import ContentDetail from './ContentDetail'

afterEach(() => vi.unstubAllGlobals())

function openRecords() {
  const record = (id: number, title: string) => ({
    id, title, description: null, status: 'active', content: { headline_hero: 'Shared headline' },
    updated_at: '2026-10-17T10:00:00Z', latest_version_number: null, unpublished_changes: true,
    machine_ready: false, readiness: [], language: null, language_choices: [], translations: [],
  })
  const first = record(42, 'Spring walk')
  const second = record(77, 'Winter walk')
  const client = makeQueryClient()
  client.setQueryData(keys.contentRecord(42), first)
  client.setQueryData(keys.contentRecord(77), second)
  const handlers: Parameters<typeof stubFetch>[0] = {
    'GET /content/fields': () => jsonResponse([
      { name: 'headline_hero', label: 'Hero headline', type: 'text', channel: 'email' },
    ]),
    'GET /content/categories': () => jsonResponse([]),
    'GET /content/category-relations': () => jsonResponse([]),
    'PATCH /content/42': () => jsonResponse({ detail: 'Temporary save failure.' }, 503),
  }
  for (const row of [first, second]) {
    handlers[`GET /content/${row.id}`] = () => jsonResponse(row)
    handlers[`GET /content/${row.id}/campaigns`] = () => jsonResponse(page([]))
    handlers[`GET /content/${row.id}/unsent-campaigns`] = () => jsonResponse({ count: 0, campaigns: [] })
    for (const suffix of ['versions', 'drafts', 'duplicate-targets', 'assignments']) {
      handlers[`GET /content/${row.id}/${suffix}`] = () => jsonResponse([])
    }
  }
  const fetchMock = stubFetch(handlers)
  renderWithProviders(
    <>
      <Link to="/content/77">Open winter record</Link>
      <Routes><Route path="/content/:id" element={<ContentDetail />} /></Routes>
    </>,
    { client, route: '/content/42' },
  )
  return fetchMock
}

it('never carries a refused edit into a cached record with the same stored field (task-372; ADR-180)', async () => {
  const fetchMock = openRecords()
  const headline = await screen.findByLabelText('Hero headline')
  fireEvent.change(headline, { target: { value: 'Spring-only draft' } })
  fireEvent.blur(headline)
  await waitFor(() => expect(fetchMock.mock.calls.some(([r]) => (r as Request).method === 'PATCH')).toBe(true))
  expect(await screen.findByText(/Temporary save failure/)).toBeInTheDocument()

  fireEvent.click(screen.getByRole('link', { name: 'Open winter record' }))
  await screen.findByRole('heading', { name: 'Winter walk' })
  const winterHeadline = screen.getByLabelText('Hero headline')
  expect(winterHeadline).toHaveValue('Shared headline')
  fireEvent.blur(winterHeadline)
  expect(fetchMock.mock.calls.filter(([r]) => (r as Request).method === 'PATCH')
    .map(([r]) => new URL((r as Request).url).pathname)).toEqual(['/content/42'])
})

it('starts a cached record with its own empty AI brief (task-372; ADR-141)', async () => {
  openRecords()
  fireEvent.change(await screen.findByLabelText('Source'), { target: { value: 'Draft a spring walking campaign' } })
  fireEvent.click(screen.getByRole('link', { name: 'Open winter record' }))
  await screen.findByRole('heading', { name: 'Winter walk' })
  expect(screen.getByLabelText('Source')).toHaveValue('')
})
