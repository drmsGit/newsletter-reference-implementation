import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { Outlet, Route, Routes } from 'react-router'

import { keys } from '../api/resources'
import { jsonResponse, makeQueryClient, page, renderWithProviders, stubFetch } from '../test-utils'
import ApprovalDetail from './ApprovalDetail'
import Approvals from './Approvals'

afterEach(() => vi.unstubAllGlobals())

const FIRST = {
  id: 7, action_key: 'ai_subject_apply', label: 'First subject request', summary: 'Spring campaign',
  status: 'pending', brand_id: 1, requested_by_type: 'integration', requested_by_id: 2,
  created_at: '2026-10-17T10:00:00Z', expires_at: null, decided_at: null,
  payload: {}, rows: [], may_decide: true, blocked_reason: null, describe_error: null, warnings: [],
  options: [{ index: 0, label: 'Spring is here' }, { index: 1, label: 'Go outside' }],
}
const SECOND = {
  ...FIRST, id: 8, label: 'Second subject request', summary: 'Winter campaign',
  options: [{ index: 0, label: 'Winter is here' }, { index: 1, label: 'Stay warm' }],
}

it.each(['choice', 'reason'] as const)('keeps the %s local to the request when a cached request opens (task-372)', async (field) => {
  // ADR-141 section 4: pick-one and feedback belong to the item being reviewed.
  // A cache hit matters: a loading screen would unmount Decide and conceal the
  // carryover seen when returning to an already visited request in the split UI.
  const client = makeQueryClient()
  client.setQueryData(keys.approval(7), FIRST)
  client.setQueryData(keys.approval(8), SECOND)
  const fetchMock = stubFetch({
    'GET /approvals/': () => jsonResponse(page([FIRST, SECOND])),
    'GET /approvals/filter-options': () => jsonResponse({ actions: [], requesters: [] }),
    'GET /approvals/7': () => jsonResponse(FIRST),
    'GET /approvals/8': () => jsonResponse(SECOND),
  })
  renderWithProviders(
    <Routes>
      {/* The persistent inbox beside the routed detail, as in the split layout.
          Uses existing screens so this test also applies to the older tests-branch base. */}
      <Route element={<><Approvals /><Outlet /></>}>
        <Route path="/approvals/:id" element={<ApprovalDetail />} />
      </Route>
    </Routes>,
    { client, route: '/approvals/7' },
  )

  expect(await screen.findByRole('heading', { name: FIRST.label })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Approve and run' })).toBeDisabled()
  fireEvent.click(screen.getByRole('radio', { name: 'Go outside' }))
  fireEvent.change(screen.getByLabelText(/Reason/), { target: { value: 'Only for the spring campaign' } })
  expect(screen.getByRole('button', { name: 'Approve and run' })).toBeEnabled()

  const inbox = await screen.findByRole('grid', { name: 'Waiting for a decision' })
  fireEvent.click(within(inbox).getByText(SECOND.label))
  await waitFor(() => expect(screen.getByRole('heading', { name: SECOND.label })).toBeInTheDocument())
  expect(fetchMock.mock.calls.filter(([input]) => (input as Request).method === 'POST')).toHaveLength(0)

  if (field === 'choice') {
    expect(screen.getByRole('radio', { name: 'Stay warm' })).not.toBeChecked()
    expect(screen.getByRole('button', { name: 'Approve and run' })).toBeDisabled()
  } else {
    expect(screen.getByLabelText(/Reason/)).toHaveValue('')
  }
})
