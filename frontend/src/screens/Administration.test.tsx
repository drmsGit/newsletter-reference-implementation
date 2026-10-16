import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import Brands from './Brands'
import IntegrationDetail from './IntegrationDetail'
import People from './People'
import PersonDetail from './PersonDetail'
import RoleDetail from './RoleDetail'
import Roles from './Roles'
import { A_SESSION, jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const T = '2026-10-16T09:00:00Z'
const BRANDS = [{ id: 1, key: 'acme', name: 'Acme', created_at: T }, { id: 2, key: 'beta', name: 'Beta', created_at: T }]
const person = (id: number, extra = {}) => ({
  id, email: `p${id}@example.invalid`, display_name: `Person ${id}`, is_external: false, is_active: true, created_at: T,
  last_login_at: null, live_sessions: 0, grants: [{ id: 10 + id, role_id: 2, role_name: 'Manager', brand_id: 1, brand_name: 'Acme' }],
  is_you: false, ...extra,
})
const PEOPLE = [person(1, { is_you: true }), person(2)]
const ROLES = [{ id: 2, key: 'manager', name: 'Manager', description: null, is_builtin: true, is_customised: false,
  permissions: ['campaigns.manage', 'view'], holders: 2 }]
const CATALOGUE = [
  { key: 'view', description: 'Read', brand_scoped: false },
  { key: 'campaigns.manage', description: 'Campaigns', brand_scoped: true },
  { key: 'content.manage', description: 'Content', brand_scoped: true },
]
const INTEGRATION = { id: 5, name: 'CRM', description: null, is_active: true, unattended_ceiling: 0, created_at: T,
  created_by_user_id: 1, live_keys: 0, expiring_soon: false, suggested_expiry_days: null, grants: [], credentials: [] }

function server(extra: Record<string, (r: Request) => Response> = {}) {
  const writes: Request[] = []
  const write = (body: unknown, status = 200) => (r: Request) => (writes.push(r.clone()), jsonResponse(body, status))
  stubFetch({
    'GET /auth/users': () => jsonResponse(PEOPLE),
    'GET /auth/brands': () => jsonResponse(BRANDS),
    'GET /auth/roles': () => jsonResponse(ROLES),
    'GET /auth/permissions': () => jsonResponse(CATALOGUE),
    'GET /integrations': () => jsonResponse([INTEGRATION]),
    'GET /integrations/permissions': () => jsonResponse(CATALOGUE),
    'GET /auth/session': () => jsonResponse(A_SESSION),
    'POST /auth/users/2/active': write({ ...person(2), is_active: false }),
    'PUT /auth/roles/2/permissions': write(ROLES[0]),
    'PATCH /auth/brands/2': write({ ...BRANDS[1], name: 'Beta Shop' }),
    'POST /integrations/5/keys': write({ credential: { id: 1, key_id: 'k1', created_at: T }, secret_key: 'k1.s3cr3t' }, 201),
    ...extra,
  } as never)
  return writes
}

function open(route: string) {
  renderWithProviders(
    <Routes>
      <Route path="/settings/users" element={<People />} />
      <Route path="/settings/users/:id" element={<PersonDetail />} />
      <Route path="/settings/roles" element={<Roles />} />
      <Route path="/settings/roles/:id" element={<RoleDetail />} />
      <Route path="/settings/brands" element={<Brands />} />
      <Route path="/settings/integrations/:id" element={<IntegrationDetail />} />
    </Routes>,
    { route },
  )
}

describe('the administration subpages (task-358)', () => {
  it('lists people with their access per brand, and marks you', async () => {
    server()
    open('/settings/users')
    const table = await screen.findByRole('grid', { name: 'Users' })
    const me = within(table).getByText('Person 1').closest('[role="row"]') as HTMLElement
    expect(within(me).getByText(/you/)).toBeInTheDocument()
    expect(within(me).getByText('Manager on Acme')).toBeInTheDocument()
  })

  it('offers no deactivation for yourself', async () => {
    server()
    open('/settings/users/1')
    expect(await screen.findByText(/This is you/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Deactivate/ })).not.toBeInTheDocument()
  })

  it('deactivates someone else, and says why when it is refused', async () => {
    const writes = server({
      'POST /auth/users/2/active': (r) => (writes.push(r.clone()),
        jsonResponse({ detail: 'That would leave nobody who can manage users.' }, 409)),
    })
    open('/settings/users/2')
    fireEvent.click(await screen.findByRole('button', { name: /Deactivate/ }))
    expect(await screen.findByText(/leave nobody who can manage users/)).toBeInTheDocument()
    expect(await writes[0].json()).toEqual({ active: false })
  })

  it("saves a role's permissions, reading always kept", async () => {
    const writes = server()
    open('/settings/roles/2')
    expect(await screen.findByRole('checkbox', { name: /view/ })).toBeDisabled()
    fireEvent.click(screen.getByRole('checkbox', { name: /content.manage/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Save permissions' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect((await writes[0].json()).permissions.sort()).toEqual(['campaigns.manage', 'content.manage', 'view'])
  })

  it('names each role as a link to its page', async () => {
    server()
    open('/settings/roles')
    expect(await screen.findByRole('link', { name: 'Manager' })).toHaveAttribute('href', '/settings/roles/2')
  })

  it("ticks an integration's permissions per brand, each saved at once", async () => {
    const writes = server({
      'GET /integrations': () => jsonResponse([{ ...INTEGRATION, grants: [{ permission: 'campaigns.manage', brand_id: 1 }] }]),
      'POST /integrations/5/grants': (r) => (writes.push(r.clone()), jsonResponse({}, 201)),
      'DELETE /integrations/5/grants/campaigns.manage/1': (r) => (writes.push(r.clone()), new Response(null, { status: 204 })),
    })
    open('/settings/integrations/5')
    const granted = await screen.findByRole('checkbox', { name: 'campaigns.manage on Acme' })
    expect(granted).toBeChecked()
    fireEvent.click(screen.getByRole('checkbox', { name: 'content.manage on Beta' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toEqual({ permission: 'content.manage', brand_id: 2 })
    fireEvent.click(granted)
    await waitFor(() => expect(writes).toHaveLength(2))
    expect(writes[1].method).toBe('DELETE')
  })

  it('renames a brand', async () => {
    const writes = server()
    open('/settings/brands')
    fireEvent.change(await screen.findByLabelText(/Name of beta/), { target: { value: 'Beta Shop' } })
    fireEvent.click(within(screen.getByRole('form', { name: 'Brand Beta' })).getByRole('button', { name: 'Rename' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toEqual({ name: 'Beta Shop' })
  })

  it('asks before deleting a brand', async () => {
    const writes = server({ 'DELETE /auth/brands/2': (r) => (writes.push(r.clone()), new Response(null, { status: 204 })) })
    open('/settings/brands')
    fireEvent.click(await screen.findByRole('button', { name: 'Delete Beta…' }))
    expect(writes).toHaveLength(0)
    fireEvent.click(screen.getByRole('button', { name: 'Yes, delete Beta' }))
    await waitFor(() => expect(writes).toHaveLength(1))
  })

  it("shows a new key's secret once, in a dialog, and forgets it when closed (ADR-166)", async () => {
    server()
    open('/settings/integrations/5')
    fireEvent.click(await screen.findByRole('button', { name: 'Issue a key' }))
    const dialog = await screen.findByRole('dialog', { name: 'The new key' })
    expect(within(dialog).getByText('k1.s3cr3t')).toBeInTheDocument()
    expect(within(dialog).getByText(/only time it is shown/)).toBeInTheDocument()
    fireEvent.click(within(dialog).getByRole('button', { name: 'I have stored it' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(screen.queryByText('k1.s3cr3t')).not.toBeInTheDocument()
  })
})
