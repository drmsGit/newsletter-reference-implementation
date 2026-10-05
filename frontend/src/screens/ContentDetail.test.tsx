import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import ContentDetail from './ContentDetail'
import { jsonResponse, page, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const T = (n: number) => `2026-10-05T10:00:${String(n).padStart(2, '0')}.000000Z`

const FIELDS = [
  // In the modules' declared order (task-276), which the page keeps.
  { name: 'headline_hero', label: 'Hero headline', type: 'text', channel: 'email' },
  { name: 'button_url', label: 'Button link', type: 'url', channel: 'email' },
  { name: 'push_title', label: 'Notification title', type: 'text', channel: 'push' },
]

/**
 * A server that keeps the record and checks its version the way the real one
 * does (task-257): a PATCH stating a stale `If-Match` is refused with 409.
 */
function server(options: {
  campaigns?: object[]; total?: number; versions?: object[]; reach?: number; assignRefused?: number
} = {}) {
  let clock = 1
  const categories = [
    { id: 7, name: 'Coast', type: 'main' }, { id: 8, name: 'Beach', type: 'sub' }, { id: 9, name: 'City', type: 'main' },
  ]
  const assignments = [{ assignment_id: 5, category_id: 7, name: 'Coast', type: 'main', score: 7 }]
  const state = {
    record: {
      id: 42, title: 'Lisbon in spring', description: null as string | null, status: 'active',
      // Stored in an order that is neither declared nor alphabetical.
      content: { legacy_key: 'kept', button_url: 'https://x.test', headline_hero: 'Lisbon' } as Record<string, unknown>,
      updated_at: T(1), latest_version_number: 1 as number | null, unpublished_changes: false,
    },
  }
  const writes: Request[] = []
  const handlers = {
    'GET /content/42': () => jsonResponse(state.record),
    'GET /content/fields': () => jsonResponse(FIELDS),
    'GET /content/42/campaigns': () =>
      jsonResponse(page(options.campaigns ?? [], { total: options.total ?? (options.campaigns ?? []).length })),
    'GET /content/42/unsent-campaigns': () => jsonResponse({ count: options.reach ?? 3, campaigns: [] }),
    'GET /content/42/versions': () => jsonResponse(options.versions ?? []),
    'GET /content/42/duplicate-targets': () =>
      jsonResponse([{ id: 1, name: 'Acme', crossing: false }, { id: 2, name: 'Beta', crossing: true }]),
    'PATCH /content/42': async (request: Request) => {
      writes.push(request.clone())
      if (request.headers.get('If-Match') !== state.record.updated_at) return jsonResponse({ detail: 'changed' }, 409)
      const body = await request.json()
      Object.assign(state.record, {
        ...(body.title !== undefined && { title: body.title }),
        ...(body.description !== undefined && { description: body.description }),
        content: { ...state.record.content, ...body.content },
        updated_at: T(++clock), unpublished_changes: true,
      })
      return jsonResponse(state.record)
    },
    'PUT /content/42/status': async (request: Request) => {
      writes.push(request.clone())
      // No version token, but the version moves — as on the real server.
      Object.assign(state.record, { status: (await request.json()).status, updated_at: T(++clock) })
      return jsonResponse(state.record)
    },
    'POST /content/versions': () => {
      Object.assign(state.record, { latest_version_number: 2, unpublished_changes: false })
      return jsonResponse({ id: 9, content_record_id: 42, version_number: 2, content: {} })
    },
    'POST /content/42/duplicate': async (request: Request) => {
      writes.push(request.clone())
      return jsonResponse({ ...state.record, id: 77, title: 'Lisbon in spring (copy)' }, 201)
    },
    'GET /content/77': () => jsonResponse({ ...state.record, id: 77, title: 'Lisbon in spring (copy)' }),
    'GET /content/77/campaigns': () => jsonResponse(page([])),
    'GET /content/77/unsent-campaigns': () => jsonResponse({ count: 0, campaigns: [] }),
    'GET /content/77/versions': () => jsonResponse([]),
    'GET /content/77/duplicate-targets': () => jsonResponse([]),
    'GET /content/77/assignments': () => jsonResponse([]),
    'GET /content/categories': () => jsonResponse(categories),
    'GET /content/category-relations': () =>
      jsonResponse([{ id: 1, parent_category_id: 7, child_category_id: 8, relation_type: 'parent_child' }]),
    'GET /content/42/assignments': () => jsonResponse(assignments),
    'POST /content/42/categories': async (request: Request) => {
      writes.push(request.clone())
      if (options.assignRefused) return jsonResponse({ detail: 'Category already assigned to this content record' }, options.assignRefused)
      const body = await request.json()
      const category = categories.find((c) => c.id === body.category_id)!
      assignments.push({ assignment_id: 6, category_id: category.id, name: category.name, type: category.type, score: body.score })
      return jsonResponse({ id: 6, content_id: 42, category_id: category.id, score: body.score })
    },
    'PATCH /content/42/assignments/5': async (request: Request) => {
      writes.push(request.clone())
      assignments[0].score = (await request.json()).score
      return jsonResponse({ id: 5, content_id: 42, category_id: 7, score: assignments[0].score })
    },
    'DELETE /content/42/assignments/5': (request: Request) => {
      writes.push(request.clone())
      assignments.splice(0, 1)
      return new Response(null, { status: 204 })
    },
  }
  return { state, writes, handlers }
}

function open(handlers: Record<string, (request: Request) => Response | Promise<Response>>) {
  stubFetch(handlers as never)
  renderWithProviders(
    <Routes>
      <Route path="/content/:id" element={<ContentDetail />} />
    </Routes>,
    { route: '/content/42' },
  )
}

async function edit(label: string | RegExp, value: string) {
  const input = await screen.findByLabelText(label)
  fireEvent.change(input, { target: { value } })
  fireEvent.blur(input)
}

describe('writing a record (task-279)', () => {
  it('saves a field on blur with its channel group and the version it edited', async () => {
    const { handlers, writes } = server()
    open(handlers)
    await edit('Hero headline', 'Lisbon, shorter')
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(writes[0].headers.get('If-Match')).toBe(T(1))
    // Only the email group may be cleared by this save (B19): push is untouched.
    expect(await writes[0].json()).toEqual({ content: { headline_hero: 'Lisbon, shorter' }, groups: ['email'] })
  })

  it('saves the title and description without touching any channel', async () => {
    const { handlers, writes } = server()
    open(handlers)
    await edit(/^Title/, 'Lisbon in autumn')
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toEqual({ content: {}, groups: [], title: 'Lisbon in autumn' })
    await edit('Description', 'Three days')
    await waitFor(() => expect(writes).toHaveLength(2))
    // The second save states the version the first one produced.
    expect(writes[1].headers.get('If-Match')).toBe(T(2))
  })

  it('shows a stale save in place and loads the other version on request', async () => {
    const { handlers, state } = server()
    open(handlers)
    await screen.findByLabelText('Hero headline')
    state.record.updated_at = T(50) // somebody else saved meanwhile
    await edit('Hero headline', 'Mine')
    expect(await screen.findByText(/changed/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /load their version/i }))
    await waitFor(() => expect(screen.getByLabelText('Hero headline')).toHaveValue('Lisbon'))
  })

  it('lists channels as sections, fields in declared order, and undefined keys read-only', async () => {
    const { handlers } = server()
    open(handlers)
    const email = (await screen.findByRole('heading', { name: 'Email' })).closest('details') as HTMLElement
    expect(email).toHaveAttribute('open')
    const labels = [...email.querySelectorAll('label')].map((l) => l.textContent)
    expect(labels).toEqual(['Hero headline', 'Button link'])
    expect(screen.getByRole('heading', { name: 'Push' })).toBeInTheDocument()
    const other = screen.getByRole('region', { name: 'Other stored values' })
    expect(within(other).getByText('legacy_key')).toBeInTheDocument()
    expect(screen.queryByLabelText('legacy_key')).not.toBeInTheDocument()
  })

  it('says how far an edit reaches, without asking', async () => {
    open(server({ reach: 3 }).handlers)
    expect(
      await screen.findByText(/Edits here change this record for 3 unsent campaigns\. Sends use the published version\./),
    ).toBeInTheDocument()
  })

  it('offers Publish once an edit is unpublished', async () => {
    const { handlers } = server()
    open(handlers)
    await edit('Hero headline', 'Lisbon, shorter')
    fireEvent.click(await screen.findByRole('button', { name: 'Publish' }))
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Publish' })).not.toBeInTheDocument())
  })

  it('lists published versions read-only, each saying what it held', async () => {
    open(server({ versions: [
      { id: 2, content_record_id: 42, version_number: 2, content: { headline_hero: 'Lisbon v2' },
        created_by: 'A Manager', created_at: '2026-10-05T09:00:00Z' },
    ] }).handlers)
    const versions = await screen.findByRole('region', { name: 'Published versions' })
    expect(await within(versions).findByText('Version 2')).toBeInTheDocument()
    expect(within(versions).getByText('Lisbon v2')).toBeInTheDocument()
    expect(within(versions).queryByRole('button', { name: /restore/i })).not.toBeInTheDocument()
  })

  it('deactivates, and the next field save states the version the status change produced', async () => {
    const { handlers, writes } = server()
    open(handlers)
    fireEvent.click(await screen.findByRole('button', { name: 'Deactivate' }))
    expect(await screen.findByRole('button', { name: 'Reactivate' })).toBeInTheDocument()
    expect(await writes[0].json()).toEqual({ status: 'inactive' })
    await edit('Hero headline', 'After')
    await waitFor(() => expect(writes).toHaveLength(2))
    expect(writes[1].headers.get('If-Match')).toBe(T(2))
  })

  it('opens a copy made in this brand', async () => {
    const { handlers, writes } = server()
    open(handlers)
    fireEvent.click(await screen.findByRole('button', { name: 'Duplicate' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toEqual({ target_brand_id: 1 })
    expect(await screen.findByRole('heading', { name: 'Lisbon in spring (copy)' })).toBeInTheDocument()
  })

  it('says where a copy into another brand went, and that it is unpublished there', async () => {
    const { handlers, writes } = server()
    open(handlers)
    fireEvent.click(await screen.findByRole('button', { name: /Acme/ }))
    fireEvent.click(await screen.findByRole('option', { name: 'Beta' }))
    fireEvent.click(screen.getByRole('button', { name: 'Duplicate' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toEqual({ target_brand_id: 2 })
    expect(await screen.findByText(/Copied to Beta\. The copy has no published version/)).toBeInTheDocument()
  })
})

describe('a record\'s categories (task-280)', () => {
  const section = () => screen.findByRole('region', { name: 'Categories' })

  it('says what categories are for, and offers no way to create one', async () => {
    open(server().handlers)
    const categories = await section()
    expect(within(categories).getByText(/build each recipient's interest profile/)).toBeInTheDocument()
    expect(within(categories).queryByRole('button', { name: /new|create/i })).not.toBeInTheDocument()
    expect(within(categories).queryByRole('textbox')).not.toBeInTheDocument()
  })

  it('changes a score in place', async () => {
    const { handlers, writes } = server()
    open(handlers)
    const categories = await section()
    fireEvent.click(await within(categories).findByRole('button', { name: /Score for Coast/ }))
    fireEvent.click(await screen.findByRole('option', { name: '3' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(writes[0].method).toBe('PATCH')
    expect(new URL(writes[0].url).pathname).toBe('/content/42/assignments/5')
    expect(await writes[0].json()).toEqual({ score: 3 })
  })

  it('removes a category', async () => {
    const { handlers, writes } = server()
    open(handlers)
    fireEvent.click(await within(await section()).findByRole('button', { name: 'Remove Coast' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(writes[0].method).toBe('DELETE')
    expect(await within(await section()).findByText('No categories yet.')).toBeInTheDocument()
  })

  it('adds one from the hierarchy, not offering those already assigned', async () => {
    const { handlers, writes } = server()
    open(handlers)
    const categories = await section()
    fireEvent.click(await within(categories).findByRole('button', { name: /Choose a category/ }))
    expect(screen.queryByRole('option', { name: 'Coast' })).not.toBeInTheDocument()
    fireEvent.click(await screen.findByRole('option', { name: 'Beach' }))
    fireEvent.click(within(categories).getByRole('button', { name: /\bScore$/ }))
    fireEvent.click(await screen.findByRole('option', { name: '4' }))
    fireEvent.click(within(categories).getByRole('button', { name: 'Add' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toEqual({ category_id: 8, score: 4 })
    expect(await within(categories).findByText('Beach')).toBeInTheDocument()
  })

  it('shows a refusal in the server\'s words, not as a stale version', async () => {
    open(server({ assignRefused: 409 }).handlers)
    const categories = await section()
    fireEvent.click(await within(categories).findByRole('button', { name: /Choose a category/ }))
    fireEvent.click(await screen.findByRole('option', { name: 'City' }))
    fireEvent.click(within(categories).getByRole('button', { name: 'Add' }))
    expect(await within(categories).findByRole('alert')).toHaveTextContent(
      'Not saved: Category already assigned to this content record',
    )
    expect(within(categories).queryByRole('button', { name: /Load their version/ })).not.toBeInTheDocument()
  })
})

describe('where a record is used (task-267)', () => {
  it('links each campaign and each variant that uses it, and marks a sent one', async () => {
    open(server({ campaigns: [
      { id: 1, name: 'Spring', variants: [
        { id: 3, name: 'Variant A', channel: 'email', stage: 'composing' },
        { id: 4, name: 'Variant B', channel: 'push', stage: 'sent' },
      ] },
    ] }).handlers)
    const section = await screen.findByRole('region', { name: 'Used in' })
    expect(await within(section).findByRole('link', { name: 'Spring' })).toHaveAttribute('href', '/campaigns/1')
    expect(within(section).getByRole('link', { name: 'Variant B' })).toHaveAttribute('href', '/campaigns/1/variants/4')
    expect(within(section).getByText('(push, sent)')).toHaveClass('used-in__sent')
    expect(within(section).getByText('(email, composing)')).not.toHaveClass('used-in__sent')
  })

  it('says so when no campaign uses it', async () => {
    open(server().handlers)
    expect(await screen.findByText('No campaign has a module bound to this record.')).toBeInTheDocument()
  })

  it('says how many there are when not all fit on the page', async () => {
    open(server({ campaigns: [{ id: 1, name: 'Spring', variants: [{ id: 3, name: 'A', channel: 'email', stage: 'sent' }] }],
      total: 51 }).handlers)
    expect(await screen.findByText('Showing 1 of 51 campaigns.')).toBeInTheDocument()
  })
})
