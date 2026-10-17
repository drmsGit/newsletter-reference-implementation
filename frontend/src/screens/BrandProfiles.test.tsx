import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import BrandProfileDetail from './BrandProfileDetail'
import BrandProfiles from './BrandProfiles'
import { jsonResponse, makeQueryClient, page, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const T = (n: number) => `2026-10-11T10:00:0${n}.000000Z`

/** As `GET /brand-profiles/structure` answers: the core, plus one declared colour. */
const STRUCTURE = [
  { name: 'legal_company_name', type: 'text', label: 'Legal company name', group: 'Legal details',
    multiline: false, core: true, required_for: ['marketing', 'transactional'] },
  { name: 'legal_address', type: 'text', label: 'Legal address', group: 'Legal details',
    multiline: true, core: true, required_for: ['marketing', 'transactional'] },
  { name: 'imprint_url', type: 'url', label: 'Imprint URL', group: 'Legal details',
    multiline: false, core: true, required_for: ['marketing', 'transactional'] },
  { name: 'privacy_url', type: 'url', label: 'Privacy URL', group: 'Legal details',
    multiline: false, core: true, required_for: ['marketing', 'transactional'] },
  { name: 'unsubscribe_text', type: 'text', label: 'Unsubscribe text', group: 'Unsubscribe',
    multiline: false, core: true, required_for: ['marketing'] },
  { name: 'colour_primary', type: 'colour', label: 'Primary colour', group: 'Look',
    multiline: false, core: false, required_for: [] },
  { name: 'menu_links', type: 'links', label: 'Menu links', group: 'Header',
    multiline: false, core: false, required_for: [] },
]

const summary = (over: Record<string, unknown>) => ({
  id: 1, name: 'Default', language: 'en', kind: 'marketing', is_default: true,
  complete: true, missing: [], updated_at: T(1), ...over,
})

describe('the profile list', () => {
  it('puts the default first and says in words what a profile still lacks', async () => {
    stubFetch({
      'GET /brand-profiles/': () => jsonResponse(page([
        summary({}),
        summary({ id: 2, name: 'Black Friday', is_default: false, complete: false,
          missing: ['legal_company_name', 'imprint_url'] }),
      ])),
      'GET /brand-profiles/structure': () => jsonResponse(STRUCTURE),
    })
    renderWithProviders(<BrandProfiles />)
    // A list of rows (task-372): the default first, said in its summary line.
    const rows = await screen.findAllByRole('row')
    expect(within(rows[0]).getByText('Default · en · marketing')).toBeInTheDocument()
    expect(within(rows[0]).getByText('Complete')).toBeInTheDocument()
    expect(await within(rows[1]).findByText('Missing: Legal company name, Imprint URL')).toBeInTheDocument()
  })
})

function detailServer(over: Record<string, unknown> = {}) {
  const state = {
    ...summary({ id: 2, name: 'Calm', is_default: false, complete: false,
      missing: ['legal_address', 'imprint_url', 'privacy_url', 'unsubscribe_text'] }),
    field_values: { legal_company_name: 'Example GmbH', colour_primary: '#1a5db0' } as Record<string, unknown>,
    may_manage: true,
    ...over,
  }
  const writes: Request[] = []
  const handlers: Record<string, (request: Request) => Response | Promise<Response>> = {
    'GET /brand-profiles/2': () => jsonResponse(state),
    'GET /brand-profiles/structure': () => jsonResponse(STRUCTURE),
    'PUT /brand-profiles/2': async (request) => {
      writes.push(request.clone())
      // As the server does (ADR-180 point 2): a stale version is refused.
      const version = request.headers.get('If-Match')
      if (version !== null && version !== state.updated_at) {
        return jsonResponse({ detail: 'This brand profile was changed after you loaded it.' }, 409)
      }
      const body = await request.json()
      if (body.field_values.imprint_url === 'imprint') {
        return jsonResponse({ detail: [{ loc: ['body', 'field_values', 'imprint_url'],
          msg: 'A full web address starting with https:// or http://.', type: 'value_error' }] }, 422)
      }
      Object.assign(state, { name: body.name, updated_at: T(2),
        field_values: Object.fromEntries(Object.entries(body.field_values).filter(([, v]) => v !== '')) })
      return jsonResponse(state)
    },
    'DELETE /brand-profiles/2': (request) => {
      writes.push(request.clone())
      return jsonResponse({ variants_moved: 1 })
    },
    'GET /brand-profiles/': () => jsonResponse(page([])),
  }
  return { state, writes, handlers }
}

function openDetail(handlers: Record<string, (request: Request) => Response | Promise<Response>>) {
  stubFetch(handlers as never)
  renderWithProviders(
    <Routes>
      <Route path="/settings/brand-profiles/:id" element={<BrandProfileDetail />} />
      <Route path="/settings/brand-profiles" element={<p>The list</p>} />
    </Routes>,
    { route: '/settings/brand-profiles/2' },
  )
}

describe('one profile', () => {
  it('builds its form from the setup file, grouped, and names what is missing', async () => {
    openDetail(detailServer().handlers)
    expect(await screen.findByRole('group', { name: 'Look' })).toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'Legal details' })).toBeInTheDocument()
    expect(screen.getByLabelText(/^Primary colour/)).toHaveValue('#1a5db0')
    expect(screen.getByText(/Incomplete\. .*Legal address, Imprint URL, Privacy URL, Unsubscribe text\./))
      .toBeInTheDocument()
    // Required to send only where the profile's kind needs it.
    expect(screen.getByText('Unsubscribe text').parentElement).toHaveTextContent('(required to send)')
    expect(screen.getByText('Primary colour').parentElement).not.toHaveTextContent('(required to send)')
  })

  it('offers the transactional kind only to a holder of its permission', async () => {
    const { writes, handlers } = detailServer({ may_mark_transactional: true })
    openDetail(handlers)
    fireEvent.click(await screen.findByRole('button', { name: /Marketing: needs an opt-in/ }))
    fireEvent.click(await screen.findByRole('option', { name: /Transactional: sent without the opt-in check/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect((await writes[0].json()).kind).toBe('transactional')
  })

  it('shows the kind read-only without the permission, and says what transactional means', async () => {
    openDetail(detailServer({ kind: 'transactional' }).handlers)
    expect(await screen.findByText(/making a profile transactional needs its own permission/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Transactional: sent without/ })).not.toBeInTheDocument()
    expect(screen.getByText(/go out without the opt-in check, and carry no unsubscribe line/)).toBeInTheDocument()
  })

  it('takes a link list in a text box and says how to write it', async () => {
    openDetail(detailServer().handlers)
    const menu = await screen.findByLabelText(/^Menu links/)
    expect(menu.tagName).toBe('TEXTAREA')
    expect(screen.getByText(/One link per line, written Label \| https:\/\/address/)).toBeInTheDocument()
  })

  it('saves every field together, with the version it read', async () => {
    const { writes, handlers } = detailServer()
    openDetail(handlers)
    const save = await screen.findByRole('button', { name: 'Save' })
    expect(save).toBeDisabled()
    fireEvent.change(screen.getByLabelText(/^Imprint URL/), { target: { value: 'https://example.test/imprint' } })
    fireEvent.click(save)
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(writes[0].headers.get('If-Match')).toBe(T(1))
    expect(await writes[0].json()).toEqual({
      name: 'Calm', language: 'en', kind: 'marketing',
      field_values: { legal_company_name: 'Example GmbH', legal_address: '', imprint_url: 'https://example.test/imprint',
        privacy_url: '', unsubscribe_text: '', colour_primary: '#1a5db0', menu_links: '' },
    })
    expect(await screen.findByText('Saved.')).toBeInTheDocument()
  })

  it('shows a refused value on its field', async () => {
    openDetail(detailServer().handlers)
    fireEvent.change(await screen.findByLabelText(/^Imprint URL/), { target: { value: 'imprint' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByText('A full web address starting with https:// or http://.')).toBeInTheDocument()
  })

  it('is read-only for a reader who may not manage profiles', async () => {
    openDetail(detailServer({ may_manage: false }).handlers)
    expect(await screen.findByText(/Changing it needs the brand-profile permission/)).toBeInTheDocument()
    expect(screen.getByLabelText(/^Primary colour/)).toHaveAttribute('readonly')
    expect(screen.queryByRole('button', { name: 'Save' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Delete/ })).not.toBeInTheDocument()
  })

  it('deletes only after a confirmation that says where its variants go', async () => {
    const { writes, handlers } = detailServer()
    openDetail(handlers)
    fireEvent.click(await screen.findByRole('button', { name: 'Delete…' }))
    expect(screen.getByText(/Variants using it will move to the default profile/)).toBeInTheDocument()
    expect(writes).toHaveLength(0)
    fireEvent.click(screen.getByRole('button', { name: 'Delete Calm' }))
    expect(await screen.findByText('The list')).toBeInTheDocument()
    expect(writes.map((w) => w.method)).toEqual(['DELETE'])
  })

  it('never saves over a version that arrived while editing, and can load it', async () => {
    const { state, writes, handlers } = detailServer()
    const client = makeQueryClient()
    stubFetch(handlers as never)
    renderWithProviders(
      <Routes>
        <Route path="/settings/brand-profiles/:id" element={<BrandProfileDetail />} />
      </Routes>,
      { client, route: '/settings/brand-profiles/2' },
    )
    fireEvent.change(await screen.findByLabelText(/^Legal company name/), { target: { value: 'Mine GmbH' } })
    // Somebody else saves meanwhile; a background refresh brings it in.
    Object.assign(state, { updated_at: T(5), field_values: { ...state.field_values, legal_company_name: 'Theirs GmbH' } })
    await act(async () => {
      await client.invalidateQueries()
    })
    expect(await screen.findByText(/Somebody changed this profile while you were editing/)).toBeInTheDocument()
    expect(screen.getByLabelText(/^Legal company name/)).toHaveValue('Mine GmbH')

    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(writes[0].headers.get('If-Match')).toBe(T(1)) // the version the edit began from

    fireEvent.click(screen.getAllByRole('button', { name: 'Load their version' })[0])
    await waitFor(() => expect(screen.getByLabelText(/^Legal company name/)).toHaveValue('Theirs GmbH'))
  })

  it('offers no delete and no make-default on the default', async () => {
    openDetail(detailServer({ is_default: true }).handlers)
    expect(await screen.findByRole('button', { name: 'Duplicate' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Delete/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Make default' })).not.toBeInTheDocument()
  })
})

describe('settings and its parts', () => {
  it('reaches brand profiles from the Settings menu as a drill-in, with the way back', async () => {
    // task-372, decision 19: the list replaces the menu in column 2.
    const { SettingsMenu, SettingsSplit } = await import('./SettingsLayout')
    stubFetch({
      'GET /brand-profiles/': () => jsonResponse(page([summary({})])),
      'GET /brand-profiles/structure': () => jsonResponse(STRUCTURE),
    })
    renderWithProviders(
      <Routes>
        <Route path="/settings" element={<SettingsSplit label="Settings parts" list={<SettingsMenu />} />}>
          <Route index element={<p>General settings</p>} />
        </Route>
        <Route element={<SettingsSplit label="Brand profile list" list={<BrandProfiles />} />}>
          <Route path="/settings/brand-profiles" element={<p>No profile open</p>} />
        </Route>
      </Routes>,
      { route: '/settings' },
    )
    const parts = screen.getByRole('navigation', { name: 'Settings' })
    expect(within(parts).getByRole('link', { name: 'General' })).toHaveAttribute('aria-current', 'page')
    fireEvent.click(within(parts).getByRole('link', { name: 'Brand profiles' }))
    expect(await screen.findByRole('heading', { name: 'Brand profiles' })).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Settings' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Settings' })).toHaveAttribute('href', '/settings')
  })
})
