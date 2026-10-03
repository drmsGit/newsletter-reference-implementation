import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import ApprovalDetail from './ApprovalDetail'
import Approvals from './Approvals'
import { jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const A_ROW = {
  id: 7,
  action_key: 'ai_subject_apply',
  label: 'Apply a suggested subject',
  summary: 'Variant 3 of Spring launch',
  status: 'pending',
  brand_id: 1,
  requested_by_type: 'integration',
  requested_by_id: 2,
  created_at: '2026-09-20T10:00:00Z',
  expires_at: '2026-09-21T10:00:00Z',
  decided_at: null,
}

describe('the approval inbox', () => {
  it('shows who requested each item, as the server typed it', async () => {
    /**
     * ADR-166 point 3 made "a person" and "an integration" durably different
     * actors. An inbox that rendered both as "someone" would discard the fact
     * that explains why a request exists at all.
     */
    stubFetch({ 'GET /approvals/': () => jsonResponse([A_ROW]) })
    renderWithProviders(<Approvals />)

    expect(await screen.findByText('Apply a suggested subject')).toBeInTheDocument()
    expect(screen.getByText('integration')).toBeInTheDocument()
  })
})

describe('an approval in detail', () => {
  it('reads may_decide from the server rather than deciding for itself', async () => {
    /**
     * **The assertion that keeps a rule on the server.**
     *
     * `docs/react-screen-inventory.md` lists "deciding whether a person may
     * approve a particular held action" among the things the SPA must never
     * reimplement: the real check is against the ROW's brand, not the reader's.
     * A client that computed it would be a second answer free to disagree.
     */
    stubFetch({
      'GET /approvals/7': () =>
        jsonResponse({
          ...A_ROW,
          rows: [{ label: 'Variant', value: 'Spring launch / 3' }],
          may_decide: false,
          blocked_reason: 'You requested this yourself.',
          warnings: [],
          options: null,
        }),
    })

    renderWithProviders(
      <Routes>
        <Route path="/approvals/:id" element={<ApprovalDetail />} />
      </Routes>,
      { route: '/approvals/7' },
    )

    expect(await screen.findByRole('status')).toHaveTextContent(/cannot decide this request/i)
    expect(screen.getByText('You requested this yourself.', { exact: false })).toBeInTheDocument()
    // The server's own description of the request, rendered generically.
    expect(screen.getByText('Spring launch / 3')).toBeInTheDocument()
  })
})

describe('narrowing and paging the inbox', () => {
  const OPTIONS = {
    actions: [{ key: 'send.fire', label: 'Fire a send' }],
    requesters: [
      { type: 'integration', id: 5, name: 'Acme Agency' },
      { type: 'user', id: 1, name: 'Sam Planner' },
    ],
  }

  function lastListQuery(fetchMock: ReturnType<typeof stubFetch>) {
    const calls = fetchMock.mock.calls
      .map(([input]) => new URL((input as Request).url))
      .filter((u) => u.pathname === '/approvals/')
    return calls[calls.length - 1].searchParams
  }

  it('names each requester, from the filter options the server gives', async () => {
    stubFetch({
      'GET /approvals/': () => jsonResponse([{ ...A_ROW, requested_by_id: 5 }]),
      'GET /approvals/filter-options': () => jsonResponse(OPTIONS),
    })
    renderWithProviders(<Approvals />)
    const table = await screen.findByRole('grid', { name: 'Approvals' })
    expect(await within(table).findByText('Acme Agency (integration)')).toBeInTheDocument()
  })

  it('sends the filters held in the URL, so a narrowed inbox can be linked to', async () => {
    const fetchMock = stubFetch({
      'GET /approvals/': () => jsonResponse([]),
      'GET /approvals/filter-options': () => jsonResponse(OPTIONS),
    })
    renderWithProviders(
      <Routes>
        <Route path="/approvals" element={<Approvals />} />
      </Routes>,
      { route: '/approvals?status=all&action=send.fire&requester=integration:5' },
    )
    expect(await screen.findByText('No request matches these filters.')).toBeInTheDocument()
    const sent = lastListQuery(fetchMock)
    expect(sent.get('status')).toBe('all')
    expect(sent.get('action_key')).toBe('send.fire')
    expect(sent.get('requested_by_type')).toBe('integration')
    expect(sent.get('requested_by_id')).toBe('5')
    expect(sent.get('limit')).toBe('50')
  })

  it('pages older from a full page, and a new filter starts from the first page', async () => {
    const full = Array.from({ length: 50 }, (_, i) => ({ ...A_ROW, id: 1000 + i }))
    const fetchMock = stubFetch({
      'GET /approvals/': () => jsonResponse(full),
      'GET /approvals/filter-options': () => jsonResponse(OPTIONS),
    })
    renderWithProviders(
      <Routes>
        <Route path="/approvals" element={<Approvals />} />
      </Routes>,
      { route: '/approvals' },
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Older' }))
    await waitFor(() => expect(lastListQuery(fetchMock).get('offset')).toBe('50'))
    expect(screen.getByRole('button', { name: 'Newer' })).not.toBeDisabled()

    // Choosing a requester resets the page.
    fireEvent.click(screen.getByRole('button', { name: /Requested by/ }))
    fireEvent.click(await screen.findByRole('option', { name: 'Acme Agency (integration)' }))
    await waitFor(() => expect(lastListQuery(fetchMock).get('requested_by_id')).toBe('5'))
    expect(lastListQuery(fetchMock).get('offset')).toBe('0')
  })
})


describe('deciding a request', () => {
  const PENDING = {
    ...A_ROW,
    status: 'pending',
    rows: [{ label: 'Send', value: 'Spring launch' }],
    may_decide: true,
    blocked_reason: null,
    describe_error: null,
    warnings: [] as string[],
    options: null as null | { index: number; label: string }[],
  }

  function renderDetail() {
    return renderWithProviders(
      <Routes>
        <Route path="/approvals/:id" element={<ApprovalDetail />} />
      </Routes>,
      { route: '/approvals/7' },
    )
  }

  function bodies(fetchMock: ReturnType<typeof stubFetch>, path: string) {
    return Promise.all(
      fetchMock.mock.calls
        .map(([input]) => input as Request)
        .filter((r) => r.method === 'POST' && new URL(r.url).pathname === path)
        .map((r) => r.clone().json()),
    )
  }

  it('approves in one press, says what happened, and re-reads the request', async () => {
    let reads = 0
    const fetchMock = stubFetch({
      'GET /approvals/7': () => {
        reads += 1
        return jsonResponse(PENDING)
      },
      'POST /approvals/7/approve': () =>
        jsonResponse({ ok: true, message: 'Approved and executed.', status: 'approved' }),
    })
    renderDetail()

    fireEvent.click(await screen.findByRole('button', { name: 'Approve and run' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Approved and executed.')
    // No reason typed: sent as nothing, never as an empty string to store.
    expect(await bodies(fetchMock, '/approvals/7/approve')).toEqual([
      { reason: null, choice_index: null },
    ])
    await waitFor(() => expect(reads).toBe(2))
  })

  it('rejects with the reason the person typed', async () => {
    const fetchMock = stubFetch({
      'GET /approvals/7': () => jsonResponse(PENDING),
      'POST /approvals/7/reject': () =>
        jsonResponse({ ok: true, message: 'Rejected.', status: 'rejected' }),
    })
    renderDetail()

    fireEvent.change(await screen.findByLabelText(/Reason/), {
      target: { value: '  Wrong audience  ' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Reject' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Rejected.')
    expect(await bodies(fetchMock, '/approvals/7/reject')).toEqual([
      { reason: 'Wrong audience', choice_index: null },
    ])
  })

  it('needs an option chosen before a pick-one can be approved, and sends its index', async () => {
    const fetchMock = stubFetch({
      'GET /approvals/7': () =>
        jsonResponse({
          ...PENDING,
          options: [
            { index: 0, label: 'Spring is here' },
            { index: 1, label: 'Go now' },
          ],
        }),
      'POST /approvals/7/approve': () =>
        jsonResponse({ ok: true, message: 'Approved and executed.', status: 'approved' }),
    })
    renderDetail()

    const approve = await screen.findByRole('button', { name: 'Approve and run' })
    expect(approve).toBeDisabled()
    fireEvent.click(screen.getByRole('radio', { name: 'Go now' }))
    expect(approve).not.toBeDisabled()
    fireEvent.click(approve)
    await screen.findByRole('status')
    expect(await bodies(fetchMock, '/approvals/7/approve')).toEqual([
      { reason: null, choice_index: 1 },
    ])
  })

  it('can still reject what the action says it cannot run, but never approve it', async () => {
    stubFetch({
      'GET /approvals/7': () =>
        jsonResponse({ ...PENDING, blocked_reason: 'The send was already fired.' }),
    })
    renderDetail()
    expect(await screen.findByRole('button', { name: 'Approve and run' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Reject' })).not.toBeDisabled()
  })

  it('shows the warnings, and offers no decision once a request is decided', async () => {
    stubFetch({
      'GET /approvals/7': () =>
        jsonResponse({
          ...PENDING,
          status: 'rejected',
          warnings: ['The audience changed since this was requested.'],
          decision_reason: 'Wrong audience',
        }),
    })
    renderDetail()
    expect(await screen.findByText('The audience changed since this was requested.'))
      .toBeInTheDocument()
    expect(screen.getByText('Wrong audience')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Reject' })).not.toBeInTheDocument()
  })
})
