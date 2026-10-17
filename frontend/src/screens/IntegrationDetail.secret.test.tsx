import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import IntegrationDetail from './IntegrationDetail'
import { A_SESSION, jsonResponse, makeQueryClient, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

it('forgets an issued secret from client caches when its dialog closes (task-358; ADR-166)', async () => {
  const secret = 'test-key.synthetic-once-only-secret'
  const timestamp = '2026-10-16T09:00:00Z'
  const integration = {
    id: 5, name: 'Test CRM', description: null, is_active: true, unattended_ceiling: 0,
    created_at: timestamp, created_by_user_id: 1, live_keys: 0, expiring_soon: false,
    suggested_expiry_days: null, grants: [], credentials: [],
  }
  // The checklist's sources since task-386 (the integrations API and the
  // session) are answered too; the rule tested is unchanged.
  stubFetch({
    'GET /auth/session': () => jsonResponse(A_SESSION),
    'GET /integrations/permissions': () => jsonResponse([]),
    'GET /integrations': () => jsonResponse([integration]),
    'GET /auth/permissions': () => jsonResponse([]),
    'GET /auth/brands': () => jsonResponse([{ id: 1, key: 'test', name: 'Test', created_at: timestamp }]),
    'POST /integrations/5/keys': () => jsonResponse({
      credential: { id: 9, key_id: 'test-key', created_at: timestamp }, secret_key: secret,
    }, 201),
  })
  const client = makeQueryClient()
  const view = renderWithProviders(
    <Routes>
      <Route path="/settings/integrations/:id" element={<IntegrationDetail />} />
    </Routes>,
    { client, route: '/settings/integrations/5' },
  )
  try {
    fireEvent.click(await screen.findByRole('button', { name: 'Issue a key' }))
    const dialog = await screen.findByRole('dialog', { name: 'The new key' })
    expect(within(dialog).getByText(secret)).toBeInTheDocument()
    // Its two actions at its foot, the closing one last (task-392 item 14).
    expect([...dialog.querySelector('.dialog-actions')!.querySelectorAll('button')].map((b) => b.textContent))
      .toEqual(['Copy', 'I have stored it'])
    fireEvent.click(within(dialog).getByRole('button', { name: 'I have stored it' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(screen.queryByText(secret)).not.toBeInTheDocument()
    // A hidden dialog is insufficient: the successful mutation response must
    // not retain a second reachable copy of this shown-once credential.
    await waitFor(() => {
      const retained = {
        queries: client.getQueryCache().getAll().map((query) => query.state.data),
        mutations: client.getMutationCache().getAll().map((mutation) => mutation.state.data),
      }
      expect(JSON.stringify(retained)).not.toContain(secret)
    })
  } finally {
    view.unmount()
    client.clear()
  }
})
