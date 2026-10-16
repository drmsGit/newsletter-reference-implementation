import { fireEvent, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import IntegrationDetail from './IntegrationDetail'
import { jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

it('lets an integration manager choose grants without user administration (task-358; ADR-150/166)', async () => {
  // These responses match a person with view + integrations.manage only:
  // integration management is allowed, the people-only admin catalogue is not.
  stubFetch({
    'GET /integrations': () => jsonResponse([{
      id: 5, name: 'Managed CRM', description: null, is_active: true, unattended_ceiling: 0,
      created_at: '2026-10-16T09:00:00Z', created_by_user_id: 1, live_keys: 0,
      expiring_soon: false, suggested_expiry_days: null, grants: [], credentials: [],
    }]),
    'GET /auth/permissions': () => jsonResponse({ detail: 'users.manage required' }, 403),
    'GET /auth/brands': () => jsonResponse({ detail: 'users.manage required' }, 403),
  })
  renderWithProviders(
    <Routes>
      <Route path="/settings/integrations/:id" element={<IntegrationDetail />} />
    </Routes>,
    { route: '/settings/integrations/5' },
  )
  expect(await screen.findByRole('heading', { name: 'Managed CRM' })).toBeInTheDocument()
  fireEvent.click(await screen.findByRole('button', { name: /Choose a permission/ }))
  expect(await screen.findByRole('option', { name: 'content.manage' })).toBeInTheDocument()
})
