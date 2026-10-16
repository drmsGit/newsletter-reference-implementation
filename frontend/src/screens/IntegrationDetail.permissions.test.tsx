import { screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import IntegrationDetail from './IntegrationDetail'
import { A_SESSION, jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

// From Codex's regression batch (1c74596, adapted in 836cad5). Adapted again
// with the fix (task-386, 2026-10-17): the checklist's permissions now come
// from the integrations API and its brands from the person's own session, so
// those are answered here; the user-administration routes still answer 403,
// and the rule is unchanged — integration management alone is enough.
it('lets an integration manager choose grants without user administration (task-358; ADR-150/166)', async () => {
  // These responses match a person with view + integrations.manage only:
  // integration management is allowed, the people-only admin catalogue is not.
  stubFetch({
    'GET /auth/session': () => jsonResponse({ ...A_SESSION, brands: [{ id: 1, name: 'Acme' }] }),
    'GET /integrations/permissions': () => jsonResponse([
      { key: 'content.manage', description: 'Create and edit content', brand_scoped: true },
    ]),
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
  expect(await screen.findByRole('checkbox', { name: 'content.manage' })).toBeInTheDocument()
})
