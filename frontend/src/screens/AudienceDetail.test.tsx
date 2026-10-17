import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import AudienceDetail from './AudienceDetail'
import { AudiencesSplit, NoAudienceOpen } from './Audiences'
import { jsonResponse, page, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const GROUP = { id: 3, name: 'Spring travellers', description: null,
  created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z' }

function preview(sample: object[], extra: object = {}) {
  return { group_id: 3, channel: 'email', blocks: [], resolved_count: 1200,
    arithmetic: { matched_rules: 1540, not_agreed: 340, added_by_hand: 4, removed_by_exclusion: 15,
      removed_hand_added: 2, dropped_by_consent: 1, total: 1200 },
    reachable_count: 1180, unreachable_count: 20, dropped_by_stage: { addressability: 20 },
    sample_matching: 1180, sample, ...extra }
}

/** The editor's own reads (task-297), empty: these tests are about the reach. */
const EDITOR = {
  'GET /api/audience-groups/3/blocks': () => jsonResponse([]),
  'GET /api/audience-groups/3/members': () => jsonResponse(page([])),
  'GET /api/audience-groups/criteria-values': () => jsonResponse({ languages: [], statuses: [] }),
}

const someone = (i: number) => ({ recipient_id: 900 + i, external_id: `r-${i}`, language: 'de',
  status: 'active', address: `r${i}@example.invalid` })

describe("an audience's reach", () => {
  it('counts the segment, shows twenty, and searches the server for someone', async () => {
    /** Decided 2026-10-03: a sample and a search, not a paged list. */
    const fetchMock = stubFetch({
      ...EDITOR,
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

  it('shows how the number was arrived at, on the channel, as of now (task-213)', async () => {
    stubFetch({
      ...EDITOR,
      'GET /api/audience-groups/3': () => jsonResponse(GROUP),
      'GET /settings': () => jsonResponse({ channels: [{ name: 'email', available: true }] }),
      'GET /api/audience-groups/3/preview': () => jsonResponse(preview([someone(1)])),
    })
    renderWithProviders(
      <Routes>
        <Route path="/audiences/:id" element={<AudienceDetail />} />
      </Routes>,
      { route: '/audiences/3' },
    )
    const working = await screen.findByRole('table', { name: 'How the audience on email is arrived at' })
    const rows = within(working).getAllByRole('row').map((r) => r.textContent)
    expect(rows).toEqual([
      'Match the rules1540',
      'Not agreed to email−340',
      'Added by hand+4',
      'Removed by exclusion segments (2 of them added by hand)−15',
      'Added by hand, not agreed to email−1',
      'In the audience1200',
    ])
    expect(screen.getByText(/As of now: a send works this out again when it goes out\./)).toBeInTheDocument()
    expect(screen.queryByText('Matched by the rules')).not.toBeInTheDocument()
  })

  it('leaves out the hand-added note when no hand-add was excluded', async () => {
    stubFetch({
      ...EDITOR,
      'GET /api/audience-groups/3': () => jsonResponse(GROUP),
      'GET /settings': () => jsonResponse({ channels: [{ name: 'email', available: true }] }),
      'GET /api/audience-groups/3/preview': () => jsonResponse(preview([someone(1)], {
        arithmetic: { matched_rules: 10, not_agreed: 0, added_by_hand: 0, removed_by_exclusion: 3,
          removed_hand_added: 0, dropped_by_consent: 0, total: 7 } })),
    })
    renderWithProviders(
      <Routes>
        <Route path="/audiences/:id" element={<AudienceDetail />} />
      </Routes>,
      { route: '/audiences/3' },
    )
    expect(await screen.findByText('Removed by exclusion segments')).toBeInTheDocument()
    expect(screen.queryByText(/of them added by hand/)).not.toBeInTheDocument()
  })
})

describe('the audiences beside the open one (task-372)', () => {
  const OTHER = { ...GROUP, id: 4, name: 'Autumn walkers' }
  function openSplit(route: string) {
    const fetchMock = stubFetch({
      ...EDITOR,
      'GET /api/audience-groups/': () => jsonResponse(page([GROUP, OTHER])),
      'GET /api/audience-groups/3': () => jsonResponse(GROUP),
      'GET /api/audience-groups/4': () => jsonResponse(OTHER),
      'GET /api/audience-groups/4/blocks': () => jsonResponse([]),
      'GET /api/audience-groups/4/members': () => jsonResponse(page([])),
      'GET /settings': () => jsonResponse({ channels: [{ name: 'email', available: true }] }),
      'GET /api/audience-groups/3/preview': () => jsonResponse(preview([someone(1)])),
      'GET /api/audience-groups/4/preview': () => jsonResponse(preview([someone(2)])),
    })
    renderWithProviders(
      <Routes>
        <Route element={<AudiencesSplit />}>
          <Route path="/audiences" element={<NoAudienceOpen />} />
          <Route path="/audiences/:id" element={<AudienceDetail />} />
        </Route>
      </Routes>,
      { route },
    )
    // Each check needs at least one request: "every" holds for none.
    return (path: string) => {
      const urls = fetchMock.mock.calls.map(([r]) => new URL((r as Request).url)).filter((u) => u.pathname === path)
      expect(urls.length).toBeGreaterThan(0)
      return urls
    }
  }

  it("keeps the list's search and page apart from the group's own", async () => {
    const asked = openSplit('/audiences/3?q=spr&offset=50&who=ana&people=50')
    await screen.findByRole('heading', { name: 'Spring travellers', level: 2 })
    await screen.findByText(/matching “ana”/)
    // The list asks for its search and page; the reach for its recipient; the people for theirs.
    expect(asked('/api/audience-groups/').every((u) => u.searchParams.get('q') === 'spr')).toBe(true)
    expect(asked('/api/audience-groups/').every((u) => u.searchParams.get('offset') === '50')).toBe(true)
    expect(asked('/api/audience-groups/3/preview').every((u) => u.searchParams.get('q') === 'ana')).toBe(true)
    expect(asked('/api/audience-groups/3/members').every((u) => u.searchParams.get('offset') === '50')).toBe(true)
  })

  it("opens another group with the list's search and page, and none of the group's own", async () => {
    const asked = openSplit('/audiences/3?q=spr&offset=50&who=ana&people=50')
    fireEvent.click(await screen.findByText('Autumn walkers'))
    await screen.findByRole('heading', { name: 'Autumn walkers', level: 2 })
    const row = within(screen.getByRole('grid', { name: 'Audience groups' })).getByRole('row', { name: /Autumn/ })
    expect(row).toHaveAttribute('aria-selected', 'true')
    expect(asked('/api/audience-groups/4/preview').every((u) => !u.searchParams.get('q'))).toBe(true)
    expect(asked('/api/audience-groups/4/members').every((u) => (u.searchParams.get('offset') ?? '0') === '0')).toBe(true)
    expect(asked('/api/audience-groups/').every((u) => u.searchParams.get('q') === 'spr')).toBe(true)
  })
})
