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
      { id: 12, group_id: 3, kind: 'include', criteria: { category_id: 7, min_score: 1 }, label: 'Interested in Coast',
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
      if (b.criteria && (b.criteria as { min_score?: number }).min_score === 0)
        return jsonResponse({ detail: [{ loc: ['body', 'criteria', 'min_score'], msg: 'A minimum score must be above 0.' }] }, 422)
      const block = { id: 13, group_id: 3, source: 'manual', position: 2, label: null, ...b } as Block
      state.blocks.push(block)
      return jsonResponse(block, 201)
    }),
    'PATCH /api/audience-groups/3/blocks/11': (r) => write(r, (b) => {
      Object.assign(state.blocks[0], b)
      return jsonResponse(state.blocks[0])
    }),
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

const rule = async (name: string) => screen.findByRole('form', { name })
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

  it("lists the rules under Who's in and Leave out, the suggested one badged", async () => {
    open(server())
    const included = await section("Who's in")
    expect(await within(included).findByRole('form', { name: 'German speakers' })).toBeInTheDocument()
    const suggested = within(included).getByRole('form', { name: 'Interested in Coast' })
    expect(within(suggested).getByText('Suggested')).toBeInTheDocument()
    const leftOut = await section('Leave out')
    expect(within(leftOut).getByText(/Leaves these people out even if a rule or a hand-add includes them/)).toBeInTheDocument()
    expect(within(leftOut).getByText(/include who received it and leave out who clicked/)).toBeInTheDocument()
  })

  it('edits a rule in place and saves it with Save rule, and the arithmetic follows', async () => {
    const s = server()
    open(s)
    const form = await rule('German speakers')
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

  it('keeps what the form does not edit, such as an engagement condition, when a rule is saved', async () => {
    const s = server()
    s.state.blocks[0].criteria = { language: ['de'], engagement: { event: 'clicked', send_instance_id: 5 } }
    open(s)
    const form = await rule('German speakers')
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
    fireEvent.click(within(form).getByRole('button', { name: /Category interest/ }))
    fireEvent.click(await screen.findByRole('option', { name: 'City' }))
    expect(within(form).getByLabelText(/Minimum score/)).toHaveValue('1.0')
    fireEvent.change(within(form).getByLabelText('Rule name'), { target: { value: 'City people' } })
    fireEvent.click(within(form).getByRole('button', { name: 'Save rule' }))
    await waitFor(() => expect(last(s)).toMatchObject({
      method: 'POST', ifMatch: T(1),
      body: { kind: 'exclude', label: 'City people', criteria: { category_id: 9, min_score: 1 } },
    }))
  })

  it('shows a refused score on the score field', async () => {
    const s = server()
    open(s)
    const included = await section("Who's in")
    fireEvent.click(within(included).getByRole('button', { name: 'Add a rule' }))
    const form = await within(included).findByRole('form', { name: 'New rule' })
    fireEvent.click(within(form).getByRole('button', { name: /Category interest/ }))
    fireEvent.click(await screen.findByRole('option', { name: 'City' }))
    fireEvent.change(within(form).getByLabelText(/Minimum score/), { target: { value: '0' } })
    fireEvent.click(within(form).getByRole('button', { name: 'Save rule' }))
    expect(await within(form).findByText('A minimum score must be above 0.')).toBeInTheDocument()
  })

  it('removes a rule, stating the version', async () => {
    const s = server()
    open(s)
    fireEvent.click(within(await rule('Interested in Coast')).getByRole('button', { name: 'Remove rule' }))
    await waitFor(() => expect(last(s)).toMatchObject({ method: 'DELETE', path: '/api/audience-groups/3/blocks/12', ifMatch: T(1) }))
    await waitFor(() => expect(screen.queryByRole('form', { name: 'Interested in Coast' })).not.toBeInTheDocument())
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
