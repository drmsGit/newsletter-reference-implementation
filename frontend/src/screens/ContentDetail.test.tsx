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
  readinessRefused?: number; machineRefused?: number; hold?: boolean
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
      machine_ready: true,
      readiness: [{ channel: 'email', marked_by: 'ana@example.invalid', marked_at: T(0), warning: null }] as {
        channel: string; marked_by: string; marked_at: string; warning: string | null
      }[],
    },
    reads: 0,
  }
  const writes: Request[] = []
  // A test that must see a change while it is still being saved holds the
  // answers to readiness and machine-ready writes until it lets them go.
  let release = () => {}
  const held = () => options.hold ? new Promise<void>((resolve) => { release = resolve }) : Promise.resolve()
  // Marks live in their own table on the real server: marking moves no
  // version, and the warning is the server's, read back with the record.
  const mark = (channel: string) => async (request: Request) => {
    writes.push(request.clone())
    await held()
    if (options.readinessRefused) return jsonResponse({ detail: 'No channel here' }, options.readinessRefused)
    const row = {
      channel, marked_by: 'manager@example.invalid', marked_at: T(30),
      warning: state.record.content.push_title ? null : 'Marked ready for Push, but Notification title is empty',
    }
    state.record.readiness = [...state.record.readiness.filter((r) => r.channel !== channel), row]
    return jsonResponse(row)
  }
  const unmark = (channel: string) => (request: Request) => {
    writes.push(request.clone())
    state.record.readiness = state.record.readiness.filter((r) => r.channel !== channel)
    return new Response(null, { status: 204 })
  }
  const handlers = {
    'GET /content/42': () => {
      state.reads++
      return jsonResponse(state.record)
    },
    'PUT /content/42/readiness/push': mark('push'),
    'PUT /content/42/readiness/email': mark('email'),
    'DELETE /content/42/readiness/push': unmark('push'),
    'DELETE /content/42/readiness/email': unmark('email'),
    'PUT /content/42/machine-ready': async (request: Request) => {
      writes.push(request.clone())
      await held()
      if (options.machineRefused) return jsonResponse({ detail: 'People only' }, options.machineRefused)
      // A column on the record, so the version moves — as on the real server.
      Object.assign(state.record, { machine_ready: (await request.json()).machine_ready, updated_at: T(++clock) })
      return jsonResponse({ machine_ready: state.record.machine_ready })
    },
    'GET /content/fields': () => jsonResponse(FIELDS),
    'GET /content/42/campaigns': () =>
      jsonResponse(page(options.campaigns ?? [], { total: options.total ?? (options.campaigns ?? []).length })),
    'GET /content/42/unsent-campaigns': () => jsonResponse({ count: options.reach ?? 3, campaigns: [] }),
    'GET /content/42/versions': () => jsonResponse(options.versions ?? []),
    'GET /content/42/drafts': () => jsonResponse([]),
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
    'GET /content/77/drafts': () => jsonResponse([]),
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
  return { state, writes, handlers, release: () => release() }
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

  it("never shows an image's alt field on its own, and saves it with an address (ADR-197)", async () => {
    const { handlers, writes } = server()
    open({
      ...handlers,
      'GET /content/fields': () => jsonResponse([
        { name: 'image_url', label: 'Image', type: 'image', channel: 'email', alt: 'image_alt' },
        { name: 'image_alt', label: 'Image description (alt text)', type: 'text', channel: 'email' },
      ]),
    })
    const group = await screen.findByRole('group', { name: 'Image' })
    expect(screen.queryByLabelText(/Image description/)).not.toBeInTheDocument()
    fireEvent.click(within(group).getByRole('button', { name: 'Choose image…' }))
    const dialog = within(await screen.findByRole('dialog'))
    fireEvent.click(dialog.getByRole('tab', { name: 'Web address' }))
    fireEvent.change(await dialog.findByLabelText('Image address'), { target: { value: 'https://cdn.example.org/a.jpg' } })
    fireEvent.change(dialog.getByLabelText('Alt text'), { target: { value: 'A red door' } })
    fireEvent.click(dialog.getByRole('button', { name: 'Use this address' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toEqual({
      content: { image_url: 'https://cdn.example.org/a.jpg', image_alt: 'A red door' }, groups: ['email'],
    })
  })

  it('lists channels as sections, fields in declared order, and undefined keys read-only', async () => {
    const { handlers } = server()
    open(handlers)
    const email = (await screen.findByRole('heading', { name: 'Email' })).closest('details') as HTMLElement
    expect(email).toHaveAttribute('open')
    // The fields' labels; the Ready switch is a label too (task-285).
    const labels = [...email.querySelectorAll('label:not(.react-aria-Switch)')].map((l) => l.textContent)
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

describe('readiness per channel and machine ready (task-285)', () => {
  const channel = async (name: string) =>
    (await screen.findByRole('heading', { name })).closest('details') as HTMLElement

  it('gives each channel section a Ready switch saying who marked it and when', async () => {
    open(server().handlers)
    const email = await channel('Email')
    expect(within(email).getByRole('switch', { name: 'Ready for Email' })).toBeChecked()
    expect(within(email).getByText(/Marked ready by ana@example\.invalid/)).toBeInTheDocument()
    const push = await channel('Push')
    expect(within(push).getByRole('switch', { name: 'Ready for Push' })).not.toBeChecked()
    expect(within(push).queryByText(/Marked ready by/)).not.toBeInTheDocument()
  })

  it('marks a channel, re-reads the record and shows the server\'s warning, which does not block', async () => {
    const { handlers, writes, state } = server()
    open(handlers)
    const push = await channel('Push')
    const before = state.reads
    fireEvent.click(within(push).getByRole('switch', { name: 'Ready for Push' }))
    expect(await within(push).findByText('Marked ready for Push, but Notification title is empty')).toBeInTheDocument()
    expect(within(push).getByRole('switch', { name: 'Ready for Push' })).toBeChecked()
    expect(within(push).getByText(/Marked ready by manager@example\.invalid/)).toBeInTheDocument()
    expect(state.reads).toBeGreaterThan(before)
    expect(writes.map((w) => `${w.method} ${new URL(w.url).pathname}`)).toEqual(['PUT /content/42/readiness/push'])
    // A warning informs; the field is still there to fill (ADR-174 point 2).
    expect(within(push).getByLabelText('Notification title')).toBeEnabled()
  })

  it('unmarks a channel', async () => {
    const { handlers, writes } = server()
    open(handlers)
    const email = await channel('Email')
    fireEvent.click(within(email).getByRole('switch', { name: 'Ready for Email' }))
    await waitFor(() => expect(within(email).getByRole('switch', { name: 'Ready for Email' })).not.toBeChecked())
    expect(within(email).queryByText(/Marked ready by/)).not.toBeInTheDocument()
    expect(writes.map((w) => `${w.method} ${new URL(w.url).pathname}`)).toEqual(['DELETE /content/42/readiness/email'])
  })

  it('shows a refused mark in place, in that channel\'s section', async () => {
    open(server({ readinessRefused: 404 }).handlers)
    const push = await channel('Push')
    fireEvent.click(within(push).getByRole('switch', { name: 'Ready for Push' }))
    expect(await within(push).findByRole('alert')).toHaveTextContent('Not saved: No channel here')
    expect(within(push).getByRole('switch', { name: 'Ready for Push' })).not.toBeChecked()
  })

  it('has a Machine ready switch by the status, saying what it means', async () => {
    open(server().handlers)
    const machine = await screen.findByRole('switch', { name: 'Machine ready' })
    expect(machine).toBeChecked()
    expect(machine.closest('.record-actions')).toBeInTheDocument()
    expect(screen.getByText(/may a decision slot pick this without a person choosing it/i)).toBeInTheDocument()
  })

  it('turns machine ready off, and the next field save states the version that change produced', async () => {
    const { handlers, writes } = server()
    open(handlers)
    fireEvent.click(await screen.findByRole('switch', { name: 'Machine ready' }))
    await waitFor(() => expect(screen.getByRole('switch', { name: 'Machine ready' })).not.toBeChecked())
    expect(await writes[0].json()).toEqual({ machine_ready: false })
    await edit('Hero headline', 'After')
    await waitFor(() => expect(writes).toHaveLength(2))
    expect(writes[1].headers.get('If-Match')).toBe(T(2))
  })

  it('turns machine ready on for a record that is not', async () => {
    const { handlers, writes, state } = server()
    state.record.machine_ready = false
    open(handlers)
    const machine = await screen.findByRole('switch', { name: 'Machine ready' })
    expect(machine).not.toBeChecked()
    fireEvent.click(machine)
    await waitFor(() => expect(screen.getByRole('switch', { name: 'Machine ready' })).toBeChecked())
    expect(await writes[0].json()).toEqual({ machine_ready: true })
  })

  it('keeps a switch focused while its change is saved, so the keyboard does not lose its place', async () => {
    const { handlers, release } = server({ hold: true })
    open(handlers)
    const push = await channel('Push')
    const ready = within(push).getByRole('switch', { name: 'Ready for Push' })
    const machine = screen.getByRole('switch', { name: 'Machine ready' })
    for (const toggle of [ready, machine]) {
      toggle.focus()
      fireEvent.click(toggle)
      // Saving: the switch takes no second change, but stays enabled — a
      // disabled input drops focus to the page.
      await waitFor(() => expect(toggle.closest('label')).toHaveAttribute('data-readonly'))
      expect(toggle).toBeEnabled()
      expect(toggle).toHaveFocus()
      release()
      await waitFor(() => expect(toggle.closest('label')).not.toHaveAttribute('data-readonly'))
    }
  })

  it('shows a refused machine-ready change in place and leaves the switch as it was', async () => {
    open(server({ machineRefused: 403 }).handlers)
    fireEvent.click(await screen.findByRole('switch', { name: 'Machine ready' }))
    expect(await screen.findByText('You do not have permission to change machine ready.')).toBeInTheDocument()
    expect(screen.getByRole('switch', { name: 'Machine ready' })).toBeChecked()
  })
})
