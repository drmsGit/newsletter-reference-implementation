import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import VariantEditor from './VariantEditor'
import { jsonResponse, page, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const T = (n: number) => `2026-10-04T10:00:${String(n).padStart(2, '0')}.000000Z`

const STATES = [
  { module_id: 11, position: 1, module_type: 'cta', kind: 'typed', slot_state: null, generic_pick: false,
    unpublished_changes: false, missing_required: ['url'] },
  { module_id: 12, position: 2, module_type: 'hero', kind: 'record', slot_state: null, generic_pick: false,
    unpublished_changes: true, missing_required: [] },
  { module_id: 13, position: 3, module_type: 'hero', kind: 'slot', slot_state: 'finds_nothing', generic_pick: false,
    unpublished_changes: false, missing_required: [] },
  { module_id: 14, position: 4, module_type: 'hero', kind: 'slot', slot_state: 'not_run', generic_pick: false,
    unpublished_changes: false, missing_required: [] },
  { module_id: 15, position: 5, module_type: 'hero', kind: 'slot', slot_state: 'resolved', generic_pick: true,
    unpublished_changes: false, missing_required: [] },
  { module_id: 16, position: 6, module_type: 'hero', kind: 'slot', slot_state: 'per_recipient', generic_pick: false,
    unpublished_changes: false, missing_required: [] },
]

function handlers(options: { channel?: string; renderFails?: boolean } = {}) {
  const renders: Request[] = []
  let label = 'Go'
  let clock = 1
  return {
    renders,
    handlers: {
      'GET /campaigns/1/composition': () => jsonResponse({
        campaign: { id: 1, name: 'Spring' },
        variants: [{
          variant: { id: 3, name: 'Variant A', channel: options.channel ?? 'email', status: 'draft', updated_at: T(1) },
          module_limit: null, can_add_module: true, has_envelope: false, accepted_module_types: ['cta'],
          modules: [{ id: 11, position: 1, module_type: 'cta', content_record_id: null, decision_slot_id: null,
            module_data: { label }, known: true, overrideable: false, active_override: null, updated_at: T(clock) }],
          envelope_modules: [], decision_slots: [],
        }],
      }),
      'GET /modules': () => jsonResponse([
        { name: 'cta', channel: 'email', label: 'Call to action', description: '', cms: false,
          variables: [{ name: 'label', required: true, label: 'Button label', envelope: false, type: 'text' }] },
        { name: 'hero', channel: 'email', label: 'Hero', description: '', cms: true, variables: [] },
      ]),
      'GET /rendering/variants/3': (request: Request) => {
        renders.push(request)
        if (options.renderFails) return jsonResponse({ detail: 'boom' }, 500)
        return jsonResponse({
          variant_id: 3, channel: options.channel ?? 'email', role: 'body',
          artifact_body: options.channel === 'push' ? '' : `<html><body><h1>${label}</h1></body></html>`,
          fields: options.channel === 'push' ? { title: 'Hello', body: 'World' } : null,
          modules: STATES,
        })
      },
      'GET /recipients/': () => jsonResponse(page([{ id: 77, external_id: 'r-77', email: 'jana@example.invalid', status: 'active' }])),
      'PUT /campaigns/modules/11': async (request: Request) => {
        label = (await request.json()).module_data.label
        clock += 1
        return jsonResponse({ id: 11, updated_at: T(clock) })
      },
    },
  }
}

function open(h: Record<string, (request: Request) => Response | Promise<Response>>) {
  stubFetch(h as never)
  renderWithProviders(
    <Routes>
      <Route path="/campaigns/:id/variants/:variantId" element={<VariantEditor />} />
    </Routes>,
    { route: '/campaigns/1/variants/3' },
  )
}

describe('the preview bar', () => {
  it('says what the render found, marking only a slot that finds nothing', async () => {
    open(handlers().handlers)
    const findings = await screen.findByText(/1 slot finds nothing/)
    expect(findings).toHaveTextContent('1 slot finds nothing · 1 record with unpublished edits · 1 required field empty')
    expect(findings).toHaveClass('preview-bar__findings--marked')
  })

  it('renders again after a save, with no render button', async () => {
    const { handlers: h, renders } = handlers()
    open(h)
    await screen.findByText(/finds nothing/)
    const before = renders.length
    const input = await screen.findByLabelText(/^Button label/)
    fireEvent.change(input, { target: { value: 'Go now' } })
    fireEvent.blur(input)
    await waitFor(() => expect(renders.length).toBeGreaterThan(before))
  })

  it('never shows an all-clear when the render failed', async () => {
    open(handlers({ renderFails: true }).handlers)
    expect(await screen.findByText('The preview could not be rendered.')).toBeInTheDocument()
    expect(screen.queryByText('Nothing to flag.')).not.toBeInTheDocument()
  })
})

describe('the preview overlay', () => {
  it('shows the sandboxed render, the module states and what a preview is', async () => {
    open(handlers().handlers)
    fireEvent.click(await screen.findByRole('button', { name: 'Open preview' }))
    const dialog = await screen.findByRole('dialog', { name: 'Preview of Variant A' })
    const frame = within(dialog).getByTitle('Rendered email: Variant A')
    expect(frame).toHaveAttribute('sandbox', '')
    expect(frame.getAttribute('srcdoc')).toContain('<h1>Go</h1>')
    expect(within(dialog).getByText(/A test send shows what will actually be sent/)).toBeInTheDocument()
    expect(within(dialog).getByText(/finds nothing — its rule matches no content/).closest('li'))
      .toHaveClass('module-state--marked')
    const unrun = within(dialog).getByText(/not run yet/).closest('li')
    expect(unrun).not.toHaveClass('module-state--marked')
    expect(within(dialog).getByText(/shows unpublished edits/)).toBeInTheDocument()
    expect(within(dialog).getByText(/picks per recipient — name a recipient/).closest('li'))
      .not.toHaveClass('module-state--marked')
    expect(within(dialog).getByText(/empty: url/)).toBeInTheDocument()
  })

  it('renders for a named recipient and says when it shows the generic pick', async () => {
    const { handlers: h, renders } = handlers()
    open(h)
    fireEvent.click(await screen.findByRole('button', { name: 'Open preview' }))
    const dialog = await screen.findByRole('dialog')
    // Nobody named: a generic pick is just "picked".
    expect(within(dialog).queryByText(/no pick of their own/)).not.toBeInTheDocument()
    fireEvent.change(within(dialog).getByLabelText('Preview for a recipient (optional)'), { target: { value: 'jana' } })
    fireEvent.click(await within(dialog).findByRole('button', { name: 'jana@example.invalid' }))
    await waitFor(() =>
      expect(renders.some((r) => new URL(r.url).searchParams.get('recipient_id') === '77')).toBe(true),
    )
    expect(await within(dialog).findByText(/the generic pick — this recipient has no pick of their own yet/))
      .toBeInTheDocument()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Generic preview' }))
    expect(within(dialog).getByLabelText('Preview for a recipient (optional)')).toBeInTheDocument()
  })

  it('shows a push variant as its fields, not a document', async () => {
    open(handlers({ channel: 'push' }).handlers)
    fireEvent.click(await screen.findByRole('button', { name: 'Open preview' }))
    const dialog = await screen.findByRole('dialog')
    expect(await within(dialog).findByText('World')).toBeInTheDocument()
    expect(within(dialog).queryByTitle(/Rendered email/)).not.toBeInTheDocument()
  })
})
