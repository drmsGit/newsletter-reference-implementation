import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import AudienceDetail from './AudienceDetail'
import Audiences from './Audiences'
import { jsonResponse, page, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const T = (n: number) => `2026-10-06T10:00:${String(n).padStart(2, '0')}.000000Z`

type Block = { id: number; group_id: number; kind: string; criteria: Record<string, unknown>; label: string | null;
  source: string; position: number }

/**
 * A server that keeps the audience and checks its one version the way the real
 * one does (task-295, ADR-180 point 2): every write states the group's
 * `updated_at` in If-Match, a stale one is refused 409, and any accepted write
 * moves it — a rule or a hand-add as much as a rename.
 */
function server(options: { sourceCampaign?: number; inUse?: boolean } = {}) {
  let clock = 1
  const state = {
    group: { id: 3, name: 'Spring travellers', description: null as string | null, created_at: T(0),
      updated_at: T(1), source_campaign_id: options.sourceCampaign ?? null },
    blocks: [
      { id: 11, group_id: 3, kind: 'include', criteria: { language: ['de'] }, label: 'German speakers',
        source: 'manual', position: 0 },
      { id: 12, group_id: 3, kind: 'include', criteria: { categories: [{ category_id: 7, min_score: 1 }] }, label: 'Interested in Coast',
        source: 'suggested', position: 1 },
    ] as Block[],
    members: [
      { id: 1, group_id: 3, recipient_id: 40, added_at: T(0), reason: 'VIP', added_by: 'ana@example.invalid',
        external_id: 'crm-anna', left_out_by: [] as string[] },
      { id: 2, group_id: 3, recipient_id: 41, added_at: T(0), reason: null, added_by: 'ana@example.invalid',
        external_id: 'crm-ben', left_out_by: ['Paused'] },
    ],
  }
  const writes: { method: string; path: string; ifMatch: string | null; body: unknown }[] = []
  const asked: { path: string; params: URLSearchParams }[] = []
  let previews = 0
  let stale = false

  const bump = () => { state.group.updated_at = T(++clock) }
  async function write(request: Request, then: (body: Record<string, unknown>) => Response) {
    const text = await request.text()
    const body = text ? JSON.parse(text) : null
    const ifMatch = request.headers.get('If-Match')
    writes.push({ method: request.method, path: new URL(request.url).pathname, ifMatch, body })
    if (stale || ifMatch !== state.group.updated_at)
      return jsonResponse({ detail: 'This audience group was changed, after you loaded it.' }, 409)
    const answer = then(body ?? {})
    if (answer.ok) bump()
    return answer
  }

  const handlers: Record<string, (r: Request) => Response | Promise<Response>> = {
    'GET /settings': () => jsonResponse({ channels: [{ name: 'email', available: true }, { name: 'push', available: true }] }),
    'GET /content/categories': () => jsonResponse([{ id: 7, name: 'Coast', type: 'main' }, { id: 9, name: 'City', type: 'main' }]),
    'GET /content/category-relations': () => jsonResponse([]),
    'GET /api/audience-groups/criteria-values': () => jsonResponse({ languages: ['de', 'fr'], statuses: ['active', 'paused'] }),
    'GET /api/audience-groups/3': () => jsonResponse(state.group),
    'GET /api/audience-groups/3/blocks': () => jsonResponse(state.blocks),
    'GET /api/audience-groups/3/members': (r) => {
      asked.push({ path: 'members', params: new URL(r.url).searchParams })
      return jsonResponse(page(state.members))
    },
    'GET /api/audience-groups/3/preview': () => {
      previews += 1
      return jsonResponse({ group_id: 3, channel: 'email', blocks: [], resolved_count: 10,
        arithmetic: { matched_rules: 10 + previews, not_agreed: 0, added_by_hand: 2, removed_by_exclusion: 1,
          removed_hand_added: 1, dropped_by_consent: 0, total: 11 },
        reachable_count: 10, unreachable_count: 0, dropped_by_stage: {}, sample_matching: 0, sample: [] })
    },
    'PATCH /api/audience-groups/3': (r) => write(r, (b) => {
      Object.assign(state.group, b)
      return jsonResponse(state.group)
    }),
    'DELETE /api/audience-groups/3': (r) => write(r, () => options.inUse
      ? jsonResponse({ detail: 'Used by 1 send (Spring edition). Sent mail must keep its audience; remove it from planned sends first.' }, 409)
      : new Response(null, { status: 204 })),
    'POST /api/audience-groups/3/blocks': (r) => write(r, (b) => {
      if ((b.criteria as { engagement?: { within_days?: number } } | undefined)?.engagement?.within_days === 0)
        return jsonResponse({ detail: [{ loc: ['body', 'criteria', 'within_days'], msg: 'a number of days above 0' }] }, 422)
      const categories = (b.criteria as { categories?: { min_score: number }[] } | undefined)?.categories ?? []
      const refused = categories.findIndex((c) => c.min_score === 0)
      if (refused >= 0)
        return jsonResponse({ detail: [{ loc: ['body', 'criteria', `categories.${refused}.min_score`],
          msg: 'A minimum score must be above 0.' }] }, 422)
      const block = { id: 13, group_id: 3, source: 'manual', position: 2, label: null, ...b } as Block
      state.blocks.push(block)
      return jsonResponse(block, 201)
    }),
    ...Object.fromEntries([11, 12].map((id) => [`PATCH /api/audience-groups/3/blocks/${id}`, (r: Request) =>
      write(r, (b) => {
        const block = state.blocks.find((x) => x.id === id)!
        Object.assign(block, b)
        return jsonResponse(block)
      })])),
    'DELETE /api/audience-groups/3/blocks/12': (r) => write(r, () => {
      state.blocks = state.blocks.filter((b) => b.id !== 12)
      return new Response(null, { status: 204 })
    }),
    'POST /api/audience-groups/3/members/50': (r) => write(r, (b) => {
      const member = { id: 3, group_id: 3, recipient_id: 50, added_at: T(9), reason: (b.reason as string) ?? null,
        added_by: 'me@example.invalid', external_id: 'crm-cleo', left_out_by: [] }
      state.members.unshift(member)
      return jsonResponse(member, 201)
    }),
    'DELETE /api/audience-groups/3/members/41': (r) => write(r, () => {
      state.members = state.members.filter((m) => m.recipient_id !== 41)
      return new Response(null, { status: 204 })
    }),
    'POST /api/audience-groups/3/members/paste-preview': async (r) => {
      asked.push({ path: 'paste-preview', params: new URLSearchParams(await r.text()) })
      return jsonResponse({ to_add: 2, already_in: 1, not_found: ['crm-nobody'], not_agreed: 1, channel: 'email' })
    },
    'POST /api/audience-groups/3/members/paste': (r) => write(r, () => jsonResponse({ added: 2, already_in: 1, not_found: 1 })),
    'POST /api/audience-groups/3/recalculate': (r) => {
      writes.push({ method: 'POST', path: new URL(r.url).pathname, ifMatch: r.headers.get('If-Match'), body: null })
      bump()
      return jsonResponse(state.group)
    },
    'GET /recipients/': () => jsonResponse(page([{ id: 50, external_id: 'crm-cleo', email: 'cleo@example.invalid' }])),
    'GET /api/audience-groups/': () => jsonResponse(page([state.group])),
    'POST /api/audience-groups/': async (r) => {
      writes.push({ method: 'POST', path: '/api/audience-groups/', ifMatch: null, body: JSON.parse(await r.text()) })
      return jsonResponse(state.group, 201)
    },
    'POST /api/audience-groups/suggested': async (r) => {
      writes.push({ method: 'POST', path: '/api/audience-groups/suggested', ifMatch: null, body: JSON.parse(await r.text()) })
      return jsonResponse(state.group, 201)
    },
    'GET /campaigns/': () => jsonResponse(page([{ id: 77, name: 'Spring edition', status: 'draft', created_at: T(0) }])),
    'GET /delivery/send-instances': (r) => {
      asked.push({ path: 'sends', params: new URL(r.url).searchParams })
      return jsonResponse(page([{ id: 11, snapshot_id: 1, name: 'Spring send', status: 'sent', created_at: T(0),
        updated_at: T(0), campaign_id: 77, campaign_name: 'Spring edition' }]))
    },
  }
  return {
    state, writes, asked, handlers,
    previews: () => previews,
    goStale: () => { stale = true; state.group.updated_at = T(50) },
    recover: () => { stale = false },
  }
}

function open(s: ReturnType<typeof server>, route = '/audiences/3') {
  stubFetch(s.handlers as never)
  renderWithProviders(
    <Routes>
      <Route path="/audiences" element={<Audiences />} />
      <Route path="/audiences/:id" element={<AudienceDetail />} />
    </Routes>,
    { route },
  )
}

/** A saved rule reads as one line; Edit opens its form (task-300). */
const line = async (name: string) => screen.findByRole('group', { name })
async function edit(name: string) {
  fireEvent.click(within(await line(name)).getByRole('button', { name: 'Edit' }))
  return screen.findByRole('form', { name })
}
/** Add a category row to an open rule form and choose it. */
async function addCategory(form: HTMLElement, name: string) {
  fireEvent.click(within(form).getByRole('button', { name: 'Add a category' }))
  const row = within(form).getAllByRole('group', { name: /^Category \d/ }).at(-1)!
  fireEvent.click(within(row).getByRole('button', { name: /Category/ }))
  fireEvent.click(await screen.findByRole('option', { name }))
  return row
}
const section = async (name: string) => screen.findByRole('region', { name })
const last = (s: ReturnType<typeof server>) => s.writes.at(-1)!

describe('the audience list (task-297)', () => {
  it('creates an audience with a name and description and opens its page', async () => {
    const s = server()
    open(s, '/audiences')
    fireEvent.click(await screen.findByRole('button', { name: /New audience/ }))
    const dialog = await screen.findByRole('dialog')
    fireEvent.change(within(dialog).getByLabelText(/Name/), { target: { value: 'Spring travellers' } })
    fireEvent.change(within(dialog).getByLabelText(/Description/), { target: { value: 'For the spring edition' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Create' }))
    expect(await screen.findByRole('heading', { name: 'Spring travellers' })).toBeInTheDocument()
    expect(last(s).body).toEqual({ name: 'Spring travellers', description: 'For the spring edition' })
  })

  it('suggests an audience from a campaign and opens it', async () => {
    const s = server()
    open(s, '/audiences')
    fireEvent.click(await screen.findByRole('button', { name: 'Suggest from campaign' }))
    const dialog = await screen.findByRole('dialog')
    fireEvent.change(within(dialog).getByLabelText(/Campaign/), { target: { value: 'spring' } })
    fireEvent.click(await within(dialog).findByRole('button', { name: 'Spring edition' }))
    expect(await screen.findByRole('heading', { name: 'Spring travellers' })).toBeInTheDocument()
    expect(last(s)).toMatchObject({ path: '/api/audience-groups/suggested', body: { campaign_id: 77 } })
  })
})

describe('the audience page is the editor (task-297)', () => {
  it('saves the name on leaving the field, stating the version, and the next write states the new one', async () => {
    const s = server()
    open(s)
    const name = await screen.findByLabelText('Name')
    const description = screen.getByLabelText('Description')
    // Two fields left in quick succession: the second waits for the first and states its version.
    fireEvent.change(name, { target: { value: 'Summer travellers' } })
    fireEvent.blur(name)
    fireEvent.change(description, { target: { value: 'Warm places' } })
    fireEvent.blur(description)
    await waitFor(() => expect(s.writes).toHaveLength(2))
    expect(s.writes[0]).toMatchObject({ method: 'PATCH', ifMatch: T(1), body: { name: 'Summer travellers' } })
    expect(s.writes[1]).toMatchObject({ method: 'PATCH', ifMatch: T(2), body: { description: 'Warm places' } })
    expect(s.writes.every((w) => w.body && !('name' in (w.body as object) && 'description' in (w.body as object)))).toBe(true)
  })

  it('offers their version when somebody else changed the audience', async () => {
    const s = server()
    open(s)
    const name = await screen.findByLabelText('Name')
    s.goStale()
    fireEvent.change(name, { target: { value: 'Mine' } })
    fireEvent.blur(name)
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/Somebody changed this audience/)
    s.recover()
    s.state.group.name = 'Theirs'
    fireEvent.click(within(alert).getByRole('button', { name: 'Load their version' }))
    expect(await screen.findByRole('heading', { name: 'Theirs' })).toBeInTheDocument()
  })

  it("lists the rules under Who's in and Leave out as one line each, the suggested one badged", async () => {
    open(server())
    const included = await section("Who's in")
    const german = await within(included).findByRole('group', { name: 'German speakers' })
    expect(german).toHaveTextContent('Language de')
    const suggested = within(included).getByRole('group', { name: 'Interested in Coast' })
    expect(await within(suggested).findByText(/Coast ≥ 1/)).toBeInTheDocument()
    expect(within(suggested).getByText('Suggested')).toBeInTheDocument()
    expect(screen.queryByRole('form')).not.toBeInTheDocument()
    const leftOut = await section('Leave out')
    expect(within(leftOut).getByText(/Leaves these people out even if a rule or a hand-add includes them/)).toBeInTheDocument()
    expect(within(leftOut).getByText(/include who received it and leave out who clicked/)).toBeInTheDocument()
  })

  it('opens the form of the rule being edited only, and saving closes it again', async () => {
    const s = server()
    open(s)
    const form = await edit('German speakers')
    expect(screen.getAllByRole('form')).toHaveLength(1)
    expect(within(await line('Interested in Coast')).getByRole('button', { name: 'Edit' })).toBeInTheDocument()
    fireEvent.click(await within(form).findByRole('checkbox', { name: 'fr' }))
    fireEvent.click(within(form).getByRole('button', { name: 'Save rule' }))
    await waitFor(() => expect(screen.queryByRole('form')).not.toBeInTheDocument())
    expect(await line('German speakers')).toHaveTextContent('Language de or fr')
  })

  it('cancelling an edit puts the rule back as it was', async () => {
    const s = server()
    open(s)
    const form = await edit('German speakers')
    fireEvent.click(await within(form).findByRole('checkbox', { name: 'fr' }))
    fireEvent.click(within(form).getByRole('button', { name: 'Cancel' }))
    expect(await line('German speakers')).toHaveTextContent('Language de')
    expect(await line('German speakers')).not.toHaveTextContent('fr')
    const again = await edit('German speakers')
    expect(await within(again).findByRole('checkbox', { name: 'fr' })).not.toBeChecked()
    expect(s.writes).toHaveLength(0)
  })

  it('edits a rule and saves it with Save rule, and the arithmetic follows', async () => {
    const s = server()
    open(s)
    const form = await edit('German speakers')
    expect(await within(form).findByRole('checkbox', { name: 'fr' })).not.toBeChecked()
    expect(within(form).getByRole('checkbox', { name: 'de' })).toBeChecked()
    await screen.findByRole('table', { name: /arrived at/ })
    const before = s.previews()
    expect(within(form).getByRole('button', { name: 'Save rule' })).toBeDisabled()
    fireEvent.click(within(form).getByRole('checkbox', { name: 'fr' }))
    fireEvent.change(within(form).getByLabelText('Rule name'), { target: { value: 'German and French' } })
    expect(s.writes).toHaveLength(0)
    fireEvent.click(within(form).getByRole('button', { name: 'Save rule' }))
    await waitFor(() => expect(last(s)).toMatchObject({
      method: 'PATCH', path: '/api/audience-groups/3/blocks/11', ifMatch: T(1),
      body: { criteria: { language: ['de', 'fr'] }, label: 'German and French' },
    }))
    await waitFor(() => expect(s.previews()).toBeGreaterThan(before))
  })

  it('names several categories in one rule, each with its own score, and removes one', async () => {
    const s = server()
    open(s)
    const form = await edit('Interested in Coast')
    fireEvent.click(within(form).getByRole('button', { name: 'Add a category' }))
    const second = within(form).getAllByRole('group', { name: /^Category \d/ })[1]
    fireEvent.click(within(second).getByRole('button', { name: /Category/ }))
    expect(await screen.findByRole('option', { name: 'City' })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'Coast' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('option', { name: 'City' }))
    const city = second
    expect(within(city).getByLabelText('Minimum score')).toHaveValue('1.0')
    fireEvent.change(within(city).getByLabelText('Minimum score'), { target: { value: '5' } })
    fireEvent.click(within(form).getByRole('button', { name: 'Save rule' }))
    await waitFor(() => expect(last(s)).toMatchObject({
      method: 'PATCH', path: '/api/audience-groups/3/blocks/12',
      body: { criteria: { categories: [{ category_id: 7, min_score: 1 }, { category_id: 9, min_score: 5 }] } },
    }))
    expect(await line('Interested in Coast')).toHaveTextContent('Coast ≥ 1 or City ≥ 5')

    const again = await edit('Interested in Coast')
    const [coast] = within(again).getAllByRole('group', { name: /^Category \d/ })
    fireEvent.click(within(coast).getByRole('button', { name: 'Remove this category' }))
    fireEvent.click(within(again).getByRole('button', { name: 'Save rule' }))
    await waitFor(() => expect(last(s).body).toMatchObject({ criteria: { categories: [{ category_id: 9, min_score: 5 }] } }))
  })

  it("removing a rule's only category removes its category interest; an unchosen row is ignored", async () => {
    const s = server()
    open(s)
    const form = await edit('Interested in Coast')
    const [coast] = within(form).getAllByRole('group', { name: /^Category \d/ })
    fireEvent.click(within(coast).getByRole('button', { name: 'Remove this category' }))
    fireEvent.click(within(form).getByRole('button', { name: 'Add a category' }))
    fireEvent.click(within(form).getByRole('checkbox', { name: 'de' }))
    fireEvent.click(within(form).getByRole('button', { name: 'Save rule' }))
    await waitFor(() => expect(last(s).body).toEqual({ criteria: { language: ['de'] }, label: 'Interested in Coast' }))
  })

  it('reads a rule still in the old single-category shape and saves it as a list', async () => {
    const s = server()
    s.state.blocks[1].criteria = { category_id: 7, min_score: 2 }
    open(s)
    expect(await within(await line('Interested in Coast')).findByText(/Coast ≥ 2/)).toBeInTheDocument()
    const form = await edit('Interested in Coast')
    fireEvent.change(within(form).getByLabelText('Rule name'), { target: { value: 'Coast fans' } })
    fireEvent.click(within(form).getByRole('button', { name: 'Save rule' }))
    await waitFor(() => expect(last(s).body).toEqual({
      criteria: { categories: [{ category_id: 7, min_score: 2 }] }, label: 'Coast fans' }))
  })

  it('keeps what the form does not edit, such as an engagement condition, when a rule is saved', async () => {
    const s = server()
    s.state.blocks[0].criteria = { language: ['de'], engagement: { event: 'clicked', send_instance_id: 5 } }
    open(s)
    const form = await edit('German speakers')
    fireEvent.click(await within(form).findByRole('checkbox', { name: 'fr' }))
    fireEvent.click(within(form).getByRole('button', { name: 'Save rule' }))
    await waitFor(() => expect(last(s).body).toEqual({
      criteria: { language: ['de', 'fr'], engagement: { event: 'clicked', send_instance_id: 5 } }, label: 'German speakers',
    }))
  })

  it('adds a leave-out rule by category interest, the score filled in at 1.0', async () => {
    const s = server()
    open(s)
    const leftOut = await section('Leave out')
    fireEvent.click(within(leftOut).getByRole('button', { name: 'Add a rule' }))
    const form = await within(leftOut).findByRole('form', { name: 'New rule' })
    const city = await addCategory(form, 'City')
    expect(within(city).getByLabelText('Minimum score')).toHaveValue('1.0')
    fireEvent.change(within(form).getByLabelText('Rule name'), { target: { value: 'City people' } })
    fireEvent.click(within(form).getByRole('button', { name: 'Save rule' }))
    await waitFor(() => expect(last(s)).toMatchObject({
      method: 'POST', ifMatch: T(1),
      body: { kind: 'exclude', label: 'City people', criteria: { categories: [{ category_id: 9, min_score: 1 }] } },
    }))
    expect(await within(leftOut).findByRole('group', { name: 'City people' })).toBeInTheDocument()
  })

  it('shows a refused score on the form', async () => {
    const s = server()
    open(s)
    const included = await section("Who's in")
    fireEvent.click(within(included).getByRole('button', { name: 'Add a rule' }))
    const form = await within(included).findByRole('form', { name: 'New rule' })
    const city = await addCategory(form, 'City')
    fireEvent.change(within(city).getByLabelText('Minimum score'), { target: { value: '0' } })
    fireEvent.click(within(form).getByRole('button', { name: 'Save rule' }))
    expect(await within(form).findByText('A minimum score must be above 0.')).toBeInTheDocument()
  })

  it('removes a rule, stating the version', async () => {
    const s = server()
    open(s)
    fireEvent.click(within(await line('Interested in Coast')).getByRole('button', { name: 'Remove rule' }))
    await waitFor(() => expect(last(s)).toMatchObject({ method: 'DELETE', path: '/api/audience-groups/3/blocks/12', ifMatch: T(1) }))
    await waitFor(() => expect(screen.queryByRole('group', { name: 'Interested in Coast' })).not.toBeInTheDocument())
  })

  it("lists the hand-added people with reason, who and when, marking whom an exclusion leaves out on the channel", async () => {
    const s = server()
    open(s)
    const people = await section('Added by hand')
    const rows = (await within(people).findAllByRole('row')).map((r) => r.textContent)
    expect(rows.some((r) => r?.startsWith('crm-annaVIPana@example.invalid'))).toBe(true)
    expect(rows.some((r) => r?.includes('Left out by “Paused” on email'))).toBe(true)
    expect(s.asked.find((a) => a.path === 'members')?.params.get('channel')).toBe('email')
  })

  it('adds one person with the picker and a reason, and removes one', async () => {
    const s = server()
    open(s)
    const people = await section('Added by hand')
    fireEvent.change(within(people).getByLabelText(/Add a person/), { target: { value: 'cleo' } })
    fireEvent.click(await within(people).findByRole('button', { name: 'cleo@example.invalid' }))
    fireEvent.change(within(people).getByLabelText('Reason (optional)'), { target: { value: 'Asked for it' } })
    fireEvent.click(within(people).getByRole('button', { name: 'Add' }))
    await waitFor(() => expect(last(s)).toMatchObject({
      method: 'POST', path: '/api/audience-groups/3/members/50', ifMatch: T(1), body: { reason: 'Asked for it' },
    }))
    fireEvent.click(await within(people).findByRole('button', { name: 'Remove crm-ben' }))
    await waitFor(() => expect(last(s)).toMatchObject({ method: 'DELETE', path: '/api/audience-groups/3/members/41', ifMatch: T(2) }))
  })

  it('pastes people: a report first, then Add N', async () => {
    const s = server()
    open(s)
    fireEvent.click(await screen.findByRole('button', { name: 'Paste people' }))
    const dialog = await screen.findByRole('dialog')
    fireEvent.change(within(dialog).getByLabelText(/Identifiers or email addresses/), { target: { value: 'a, b c\ncrm-nobody' } })
    fireEvent.change(within(dialog).getByLabelText('Reason (optional)'), { target: { value: 'Fair list' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Check' }))
    expect(await within(dialog).findByText('2 will be added, 1 already in.')).toBeInTheDocument()
    expect(within(dialog).getByText('crm-nobody')).toBeInTheDocument()
    expect(within(dialog).getByText(/1 have not agreed to email: added, but will not receive it/)).toBeInTheDocument()
    expect(s.writes).toHaveLength(0)
    fireEvent.click(within(dialog).getByRole('button', { name: 'Add 2' }))
    await waitFor(() => expect(last(s)).toMatchObject({
      path: '/api/audience-groups/3/members/paste', ifMatch: T(1), body: { text: 'a, b c\ncrm-nobody', reason: 'Fair list' },
    }))
    expect(await screen.findByText(/Added 2/)).toBeInTheDocument()
  })

  it('deletes an unused audience after confirmation and goes back to the list', async () => {
    const s = server()
    open(s)
    fireEvent.click(await screen.findByRole('button', { name: 'Delete audience' }))
    const dialog = await screen.findByRole('alertdialog')
    expect(s.writes).toHaveLength(0)
    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete' }))
    expect(await screen.findByRole('heading', { name: 'Audiences' })).toBeInTheDocument()
    expect(last(s)).toMatchObject({ method: 'DELETE', path: '/api/audience-groups/3', ifMatch: T(1) })
  })

  it('says which sends use it when deleting is refused, without offering their version', async () => {
    const s = server({ inUse: true })
    open(s)
    fireEvent.click(await screen.findByRole('button', { name: 'Delete audience' }))
    fireEvent.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Delete' }))
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Used by 1 send (Spring edition). Sent mail must keep its audience')
    expect(within(alert).queryByRole('button', { name: 'Load their version' })).not.toBeInTheDocument()
  })

  it('recalculates the suggested rules on request, only for an audience with a source campaign', async () => {
    const s = server({ sourceCampaign: 77 })
    open(s)
    fireEvent.click(await screen.findByRole('button', { name: 'Recalculate from campaign' }))
    expect(await screen.findByText(/The suggested rules match the campaign now/)).toBeInTheDocument()
    expect(last(s).path).toBe('/api/audience-groups/3/recalculate')
  })

  it('offers no recalculation without a source campaign', async () => {
    open(server())
    await screen.findByRole('heading', { name: 'Spring travellers' })
    expect(screen.queryByRole('button', { name: 'Recalculate from campaign' })).not.toBeInTheDocument()
  })
})

/** Choose an option of a labelled choice inside `scope`. */
async function choose(scope: HTMLElement, label: RegExp, option: string) {
  fireEvent.click(within(scope).getByRole('button', { name: label }))
  fireEvent.click(await screen.findByRole('option', { name: option }))
}

async function newRule(sectionName: string) {
  const area = await section(sectionName)
  fireEvent.click(within(area).getByRole('button', { name: 'Add a rule' }))
  return within(area).findByRole('form', { name: 'New rule' })
}

describe('engagement in a rule (task-298)', () => {
  it('says who clicked one send in the last N days, with the did-not hint, and reads it back as one line', async () => {
    const s = server()
    open(s)
    const form = await newRule("Who's in")
    expect(within(form).queryByText(/include who received it and leave out who clicked/)).not.toBeInTheDocument()
    fireEvent.click(within(form).getByRole('button', { name: 'Add engagement' }))
    expect(within(form).getByText(/include who received it and leave out who clicked/)).toBeInTheDocument()
    await choose(form, /What happened/, 'Clicked in it')
    await choose(form, /Which mailing/, 'One send')
    await choose(form, /Send$/, 'Spring send')
    await choose(form, /When/, 'In the last … days')
    fireEvent.change(within(form).getByLabelText('Days'), { target: { value: '30' } })
    fireEvent.change(within(form).getByLabelText('Rule name'), { target: { value: 'Clickers' } })
    fireEvent.click(within(form).getByRole('button', { name: 'Save rule' }))
    await waitFor(() => expect(last(s)).toMatchObject({ method: 'POST', body: {
      kind: 'include', label: 'Clickers', criteria: { engagement: { event: 'clicked', send_instance_id: 11, within_days: 30 } } } }))
    expect(await within(await line('Clickers')).findByText(/Clicked in Spring send in the last 30 days/)).toBeInTheDocument()
    expect(s.asked.find((a) => a.path === 'sends')?.params.get('status')).toBe('sent')
  })

  it('says who received any send of a campaign between two dates', async () => {
    const s = server()
    open(s)
    const form = await newRule("Who's in")
    fireEvent.click(within(form).getByRole('button', { name: 'Add engagement' }))
    await choose(form, /What happened/, 'Received it')
    await choose(form, /Which mailing/, 'Any send of a campaign')
    await choose(form, /Campaign$/, 'Spring edition')
    await choose(form, /When/, 'Between two dates')
    fireEvent.change(within(form).getByLabelText('From'), { target: { value: '2026-09-01' } })
    fireEvent.change(within(form).getByLabelText('To'), { target: { value: '2026-09-15' } })
    fireEvent.click(within(form).getByRole('button', { name: 'Save rule' }))
    await waitFor(() => expect(last(s).body).toMatchObject({ criteria: { engagement: {
      event: 'received', campaign_id: 77, from: '2026-09-01', to: '2026-09-15' } } }))
    expect(await screen.findByText(/Received a send of Spring edition between 2026-09-01 and 2026-09-15/)).toBeInTheDocument()
  })

  it('says who opened any send, any time, or more than N days ago', async () => {
    const s = server()
    open(s)
    const form = await newRule('Leave out')
    fireEvent.click(within(form).getByRole('button', { name: 'Add engagement' }))
    expect(within(form).queryByText(/include who received it and leave out who clicked/)).not.toBeInTheDocument()
    expect(within(form).getByText(/any send on the channel this audience is sent on/)).toBeInTheDocument()
    await choose(form, /What happened/, 'Opened it')
    fireEvent.click(within(form).getByRole('button', { name: 'Save rule' }))
    await waitFor(() => expect(last(s).body).toEqual({ kind: 'exclude', label: null, criteria: { engagement: { event: 'opened' } } }))

    const again = await newRule('Leave out')
    fireEvent.click(within(again).getByRole('button', { name: 'Add engagement' }))
    await choose(again, /When/, 'More than … days ago')
    fireEvent.change(within(again).getByLabelText('Days'), { target: { value: '90' } })
    fireEvent.click(within(again).getByRole('button', { name: 'Save rule' }))
    await waitFor(() => expect(last(s).body).toMatchObject({ criteria: { engagement: { event: 'received', more_than_days: 90 } } }))
  })

  it('reads an engagement field back into the form, and removing it removes it', async () => {
    const s = server()
    s.state.blocks[0].criteria = { language: ['de'], engagement: { event: 'clicked', campaign_id: 77, more_than_days: 7 } }
    open(s)
    expect(await screen.findByText(/Clicked in a send of Spring edition more than 7 days ago/)).toBeInTheDocument()
    const form = await edit('German speakers')
    expect(within(form).getByRole('button', { name: /What happened/ })).toHaveTextContent('Clicked in it')
    expect(within(form).getByRole('button', { name: /Which mailing/ })).toHaveTextContent('Any send of a campaign')
    expect(within(form).getByLabelText('Days')).toHaveValue('7')
    fireEvent.click(within(form).getByRole('button', { name: 'Remove engagement' }))
    fireEvent.click(within(form).getByRole('button', { name: 'Save rule' }))
    await waitFor(() => expect(last(s).body).toEqual({ criteria: { language: ['de'] }, label: 'German speakers' }))
  })

  it("shows the server's refusal of an engagement value", async () => {
    const s = server()
    open(s)
    const form = await newRule("Who's in")
    fireEvent.click(within(form).getByRole('button', { name: 'Add engagement' }))
    await choose(form, /When/, 'In the last … days')
    fireEvent.change(within(form).getByLabelText('Days'), { target: { value: '0' } })
    fireEvent.click(within(form).getByRole('button', { name: 'Save rule' }))
    expect(await within(form).findByText('a number of days above 0')).toBeInTheDocument()
  })
})
