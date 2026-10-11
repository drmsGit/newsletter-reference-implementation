import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import VariantEditor from './VariantEditor'
import { A_SESSION, jsonResponse, renderWithProviders, stubFetch, A_BRAND_PROFILE } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const AT = '2026-10-04T10:42:00Z'

function open(fence: object | null) {
  let current = fence
  const fetchMock = stubFetch({
    'GET /auth/session': () => jsonResponse(A_SESSION),
    'GET /campaigns/1/composition': () => jsonResponse({
      campaign: { id: 1, name: 'Spring' },
      variants: [{
        variant: { id: 3, name: 'Variant A', channel: 'email', status: 'draft', updated_at: AT },
        fence: current, module_limit: null, can_add_module: true, has_envelope: false, brand_profile: A_BRAND_PROFILE,
        accepted_module_types: [], modules: [], envelope_modules: [], decision_slots: [],
      }],
    }),
    'GET /modules': () => jsonResponse([]),
    'GET /rendering/variants/3': () => jsonResponse({ variant_id: 3, channel: 'email', role: 'body', artifact_body: '', modules: [] }),
    'DELETE /campaigns/variants/3/fence': () => {
      current = null
      return jsonResponse(null)
    },
  })
  renderWithProviders(
    <Routes>
      <Route path="/campaigns/:id/variants/:variantId" element={<VariantEditor />} />
    </Routes>,
    { route: '/campaigns/1/variants/3' },
  )
  return fetchMock
}

describe('the fence on a variant', () => {
  it("names someone else's active fence, says edits still save, and unblocks", async () => {
    const fetchMock = open({ by: 'jana@example.invalid', by_type: 'user', at: AT, active: true })
    const fence = await screen.findByText(/is working on this variant/)
    expect(fence).toHaveTextContent('jana@example.invalid is working on this variant')
    expect(fence).toHaveTextContent('Your edits still save')
    fireEvent.click(screen.getByRole('button', { name: 'Unblock' }))
    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([r]) => (r as Request).method === 'DELETE')).toBe(true),
    )
    await waitFor(() => expect(screen.queryByText(/is working on this variant/)).not.toBeInTheDocument())
  })

  it('says when the fence is your own', async () => {
    open({ by: A_SESSION.user.email, by_type: 'user', at: AT, active: true })
    expect(await screen.findByText(/You are editing this variant/)).toBeInTheDocument()
    expect(screen.queryByText(/is working on this variant/)).not.toBeInTheDocument()
  })

  it('shows a lapsed fence as the last edit, with nothing to unblock', async () => {
    open({ by: 'jana@example.invalid', by_type: 'user', at: AT, active: false })
    expect(await screen.findByText(/Last edited by jana@example.invalid at/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Unblock' })).not.toBeInTheDocument()
  })

  it('says nothing when nobody has edited', async () => {
    open(null)
    await screen.findByRole('heading', { name: 'Variant A' })
    expect(screen.queryByText(/edit/i)).not.toBeInTheDocument()
  })
})
