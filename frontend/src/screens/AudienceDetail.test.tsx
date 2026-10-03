import { fireEvent, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import AudienceDetail from './AudienceDetail'
import { jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const GROUP = { id: 3, name: 'Spring travellers', description: null,
  created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z' }

function preview(sample: object[], extra: object = {}) {
  return { group_id: 3, channel: 'email', blocks: [], resolved_count: 1200,
    reachable_count: 1180, unreachable_count: 20, dropped_by_stage: { addressability: 20 },
    sample_matching: 1180, sample, ...extra }
}

const someone = (i: number) => ({ recipient_id: 900 + i, external_id: `r-${i}`, language: 'de',
  status: 'active', address: `r${i}@example.invalid` })

describe("an audience's reach", () => {
  it('counts the segment, shows twenty, and searches the server for someone', async () => {
    /** Decided 2026-10-03: a sample and a search, not a paged list. */
    const fetchMock = stubFetch({
      'GET /api/audience-groups/3': () => jsonResponse(GROUP),
      'GET /settings': () => jsonResponse({ channels: [{ name: 'email', available: true }] }),
      'GET /api/audience-groups/3/preview': (request) => {
        const q = new URL(request.url).searchParams.get('q')
        return jsonResponse(q
          ? preview([someone(42)], { sample_matching: 1 })
          : preview(Array.from({ length: 20 }, (_, i) => someone(i))))
      },
    })
    renderWithProviders(
      <Routes>
        <Route path="/audiences/:id" element={<AudienceDetail />} />
      </Routes>,
      { route: '/audiences/3' },
    )
    expect(await screen.findByText(/Showing 20 of 1180/)).toBeInTheDocument()
    expect(screen.getByText('Not reachable: addressability')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText(/Find a recipient/), { target: { value: 'r42' } })
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))
    expect(await screen.findByText(/1 matching “r42”/)).toBeInTheDocument()
    expect(screen.getByText('r42@example.invalid')).toBeInTheDocument()
    const asked = fetchMock.mock.calls
      .map(([input]) => new URL((input as Request).url))
      .filter((u) => u.pathname === '/api/audience-groups/3/preview')
      .at(-1)!.searchParams
    expect([asked.get('channel'), asked.get('q')]).toEqual(['email', 'r42'])
  })
})
