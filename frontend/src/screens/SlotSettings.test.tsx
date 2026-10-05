import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import VariantEditor from './VariantEditor'
import { jsonResponse, page, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const T = (n: number) => `2026-10-04T10:00:${String(n).padStart(2, '0')}.000000Z`

const STRATEGIES = [
  {
    name: 'top_score', label: 'Top Score', description: 'Highest-scored content.', requires_recipient: false,
    candidate_filter_fields: [{ name: 'category_ids', type: 'list[int]', required: false, default: [], description: '' }],
    config_fields: [],
  },
  {
    name: 'recipient_top_score', label: 'Recipient Top Score', description: 'Per recipient.', requires_recipient: true,
    candidate_filter_fields: [{ name: 'category_ids', type: 'list[int]', required: false, default: [], description: '' }],
    config_fields: [
      { name: 'preference_score_weight', type: 'number', required: false, default: 10, description: 'Weight of the preference.' },
    ],
  },
]

/** A server that keeps the slot's state and checks its version (ADR-180 point 2). */
function server(options: { unbound?: boolean } = {}) {
  let clock = 1
  const state = {
    module: {
      id: 12, position: 1, module_type: 'hero', content_record_id: null,
      decision_slot_id: options.unbound ? null : 5, module_data: {}, known: true,
      overrideable: false, active_override: null, updated_at: T(1),
    } as Record<string, unknown>,
    slot: {
      id: 5, variant_id: 3, name: 'Hero (position 1)', decision_type: 'content_recommendation',
      decision_strategy: 'recipient_top_score', candidate_filter: { category_ids: [1] },
      strategy_config: { preference_score_weight: 10 }, max_results: 1, created_at: T(0), updated_at: T(1),
    } as Record<string, unknown>,
  }
  const writes: Request[] = []
  const stale = (request: Request, current: unknown) =>
    request.headers.get('If-Match') !== null && request.headers.get('If-Match') !== current
  const handlers = {
    'GET /campaigns/1/composition': () => jsonResponse({
      campaign: { id: 1, name: 'Spring' },
      variants: [{
        variant: { id: 3, name: 'Variant A', channel: 'email', status: 'draft', updated_at: T(1) },
        module_limit: null, can_add_module: true, has_envelope: false, accepted_module_types: ['hero'],
        modules: [state.module], envelope_modules: [], decision_slots: [],
      }],
    }),
    'GET /modules': () => jsonResponse([{
      name: 'hero', channel: 'email', label: 'Hero', description: '', cms: true,
      variables: [{ name: 'headline_hero', required: true, envelope: false, type: 'text' }],
    }]),
    'GET /campaigns/decision-slots/5/stats': () => jsonResponse({
      slot: state.slot, variant_id: 3, variant_name: 'Variant A', campaign_id: 1, campaign_name: 'Spring',
      summary: {}, top_content: [], latest: [], reasons: [],
    }),
    'GET /campaigns/decision-slots/5/candidates': () =>
      jsonResponse({ slot_id: 5, candidate_count: 7, category_ids: [1], requires_recipient: true }),
    'GET /decision/strategies': () => jsonResponse(STRATEGIES),
    'GET /content/categories': () => jsonResponse([{ id: 1, name: 'Food', type: 'main' }, { id: 2, name: 'City', type: 'main' }]),
    'GET /content/category-relations': () => jsonResponse([]),
    'GET /content/': () =>
      jsonResponse(page([{ id: 42, title: 'Lisbon', content: {}, status: 'active', latest_version_number: 1, ready_for: ['email'] }])),
    'PATCH /campaigns/decision-slots/5': async (request: Request) => {
      writes.push(request.clone())
      if (stale(request, state.slot.updated_at)) return jsonResponse({ detail: 'changed' }, 409)
      Object.assign(state.slot, await request.json(), { updated_at: T(++clock) })
      return jsonResponse(state.slot)
    },
    'POST /campaigns/modules/12/decision-slot': (request: Request) => {
      writes.push(request.clone())
      if (stale(request, state.module.updated_at)) return jsonResponse({ detail: 'changed' }, 409)
      Object.assign(state.module, { decision_slot_id: 5, updated_at: T(++clock) })
      return jsonResponse({ module: state.module, slot: state.slot })
    },
    'PUT /campaigns/modules/12': async (request: Request) => {
      writes.push(request.clone())
      Object.assign(state.module, await request.json(), { updated_at: T(++clock) })
      return jsonResponse(state.module)
    },
  }
  return { state, writes, handlers }
}

function open(handlers: Record<string, (request: Request) => Response | Promise<Response>>) {
  stubFetch(handlers as never)
  renderWithProviders(
    <Routes>
      <Route path="/campaigns/:id/variants/:variantId" element={<VariantEditor />} />
    </Routes>,
    { route: '/campaigns/1/variants/3' },
  )
}

describe('a slot on its module', () => {
  it('shows its strategy, what it would choose between, and never max_results', async () => {
    open(server().handlers)
    expect(await screen.findByRole('status')).toHaveTextContent('Would choose between 7 active content records now')
    expect(screen.getByRole('button', { name: /Recipient Top Score/ })).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: 'Food' })).toBeChecked()
    expect(screen.queryByLabelText(/max results/i)).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'See what it has picked' })).toHaveAttribute('href', '/decision-slots/5')
  })

  it('saves a category with the slot version, keeping the rest of the filter', async () => {
    const { handlers, writes } = server()
    open(handlers)
    fireEvent.click(await screen.findByRole('checkbox', { name: 'City' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(writes[0].headers.get('If-Match')).toBe(T(1))
    expect(await writes[0].json()).toEqual({ candidate_filter: { category_ids: [1, 2] } })
  })

  it('changes the strategy, sending only the strategy', async () => {
    const { handlers, writes } = server()
    open(handlers)
    fireEvent.click(await screen.findByRole('button', { name: /Recipient Top Score/ }))
    fireEvent.click(await screen.findByRole('option', { name: 'Top Score' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toEqual({ decision_strategy: 'top_score' })
  })

  it('saves a setting as a number on blur, and refuses what is not one', async () => {
    const { handlers, writes } = server()
    open(handlers)
    const weight = await screen.findByLabelText('preference score weight')
    fireEvent.change(weight, { target: { value: 'lots' } })
    fireEvent.blur(weight)
    expect(await screen.findByText('Enter a number.')).toBeInTheDocument()
    expect(writes).toHaveLength(0)
    fireEvent.change(weight, { target: { value: '25' } })
    fireEvent.blur(weight)
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toEqual({ strategy_config: { preference_score_weight: 25 } })
  })

  it('goes back to one content record', async () => {
    const { handlers, writes } = server()
    open(handlers)
    fireEvent.click(await screen.findByRole('button', { name: 'Use one content record instead' }))
    // The picker lists records on open (task-269), so no search is needed.
    fireEvent.click(await screen.findByRole('option', { name: /Lisbon/ }))
    await waitFor(() => expect(writes).toHaveLength(1))
    const body = await writes[0].json()
    expect([body.content_record_id, body.decision_slot_id]).toEqual([42, null])
  })
})

describe('an unbound catalogue module', () => {
  it('can be filled from a new decision slot in one write with the module version', async () => {
    const { handlers, writes } = server({ unbound: true })
    open(handlers)
    fireEvent.click(await screen.findByRole('button', { name: 'Personalise with a decision slot' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(new URL(writes[0].url).pathname).toBe('/campaigns/modules/12/decision-slot')
    expect(writes[0].headers.get('If-Match')).toBe(T(1))
    expect(await screen.findByRole('status')).toHaveTextContent('Would choose between 7')
  })
})
