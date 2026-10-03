import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import Settings from './Settings'
import { jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const SETTINGS = {
  signals: { weights: { click: 500, open: 0 }, half_lives: { click: 45, open: 45 } },
  known_contribution_types: ['click', 'open'],
  max_send_recipients: 200,
  channels: [
    { name: 'email', available: true },
    { name: 'push', available: false },
  ],
  delivery_providers: [
    { name: 'mock', label: 'mock (nothing is sent)', channels: ['email', 'push'], click_content_attribution: false },
    { name: 'resend', label: 'resend (real)', channels: ['email'], click_content_attribution: true },
  ],
  ai_provider: 'claude',
  ai_providers: ['mock', 'claude'],
  ai_key_present: true,
  ai_model: 'claude-opus-5',
  ai_model_from_env: true,
  ai_budget: {
    cap: { warn_tokens: 400000, hard_stop_tokens: 500000, budget_usd: 5 },
    tokens_used: 450000,
    spend: { usd: 4.25, unpriced_runs: 0 },
    tokens_remaining: 50000,
    used_pct: 90,
    over_warn: true,
  },
  ai_tasks: [
    {
      key: 'subject_preheader',
      label: 'Subject & preheader',
      description: 'Suggests subject lines.',
      prompt_body: 'You write subject lines.',
      prompt_version: 2,
      versions: [
        { version: 1, body: 'old', is_published: false, created_at: '2026-09-01T00:00:00Z' },
        { version: 2, body: 'You write subject lines.', is_published: true, created_at: '2026-09-02T00:00:00Z' },
      ],
      model: null,
      approval_mode: 'require_approval',
    },
  ],
  governed_models: ['claude-opus-5'],
  may_manage: false,
  may_configure_ai: false,
}

describe('the settings screen', () => {
  it("shows what is set, as the server says it", async () => {
    stubFetch({ 'GET /settings': () => jsonResponse(SETTINGS) })
    renderWithProviders(<Settings />)

    expect(await screen.findByText('200')).toBeInTheDocument()
    expect(screen.getByText('switched off')).toBeInTheDocument()
    expect(screen.getByText('no — counted, not credited')).toBeInTheDocument()
    expect(screen.getByText('held for review')).toBeInTheDocument()
    expect(screen.getByText('version 2 of 2')).toBeInTheDocument()
    expect(screen.getByText('the default (claude-opus-5)')).toBeInTheDocument()
  })

  it('warns when the server says the AI warning threshold is crossed', async () => {
    stubFetch({ 'GET /settings': () => jsonResponse(SETTINGS) })
    renderWithProviders(<Settings />)
    expect(await screen.findByRole('alert')).toHaveTextContent(/warning threshold \(90%/)
  })

  it('offers nothing to press or type into — it is read-only', async () => {
    /**
     * Decided 2026-10-03: this pass shows settings and changes none. A control
     * that does nothing would suggest a change was made.
     */
    stubFetch({ 'GET /settings': () => jsonResponse(SETTINGS) })
    const { container } = renderWithProviders(<Settings />)
    await screen.findByText('200')
    const main = within(container)
    expect(main.queryAllByRole('button')).toHaveLength(0)
    expect(main.queryAllByRole('textbox')).toHaveLength(0)
    expect(main.queryAllByRole('combobox')).toHaveLength(0)
  })
})


describe('editing settings', () => {
  const MANAGER = { ...SETTINGS, may_manage: true, may_configure_ai: false }

  function sentBodies(fetchMock: ReturnType<typeof stubFetch>, method: string) {
    return Promise.all(
      fetchMock.mock.calls
        .map(([input]) => input as Request)
        .filter((r) => r.method === method)
        .map((r) => r.clone().json()),
    )
  }

  it('saves the send cap the person typed, then re-reads what the server kept', async () => {
    let reads = 0
    const fetchMock = stubFetch({
      'GET /settings': () => {
        reads += 1
        return jsonResponse(MANAGER)
      },
      'PUT /settings/send-cap': () => jsonResponse({ max_send_recipients: 150 }),
    })
    renderWithProviders(<Settings />)

    const field = await screen.findByLabelText('Most recipients one send may reach')
    fireEvent.change(field, { target: { value: '150' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save send cap' }))

    expect(await screen.findByText('Saved.')).toBeInTheDocument()
    expect(await sentBodies(fetchMock, 'PUT')).toEqual([{ max_send_recipients: 150 }])
    await waitFor(() => expect(reads).toBe(2))
  })

  it("shows the server's reason when it refuses a value", async () => {
    stubFetch({
      'GET /settings': () => jsonResponse(MANAGER),
      'PUT /settings/ai/spend-cap': () =>
        jsonResponse({ detail: 'the warning threshold is above the hard stop' }, 422),
    })
    renderWithProviders(<Settings />)

    fireEvent.click(await screen.findByRole('button', { name: 'Save AI budget' }))
    expect(await screen.findByText('Not saved: the warning threshold is above the hard stop'))
      .toBeInTheDocument()
  })

  it('does not send something that is not a whole number', async () => {
    const fetchMock = stubFetch({ 'GET /settings': () => jsonResponse(MANAGER) })
    renderWithProviders(<Settings />)

    const field = await screen.findByLabelText('Most recipients one send may reach')
    fireEvent.change(field, { target: { value: 'lots' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save send cap' }))

    expect(await screen.findByText('Enter a whole number.')).toBeInTheDocument()
    expect(fetchMock.mock.calls.filter(([r]) => (r as Request).method === 'PUT')).toHaveLength(0)
  })

  it('offers the model only to someone who may also run AI', async () => {
    /** `may_configure_ai` is the server's answer (settings.manage + ai.run). */
    stubFetch({ 'GET /settings': () => jsonResponse(MANAGER) })
    const { unmount } = renderWithProviders(<Settings />)
    await screen.findByRole('button', { name: 'Save send cap' })
    expect(screen.queryByRole('button', { name: 'Save model' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save output mode' })).toBeInTheDocument()
    unmount()
    vi.unstubAllGlobals()

    const fetchMock = stubFetch({
      'GET /settings': () => jsonResponse({ ...MANAGER, may_configure_ai: true }),
      'PUT /settings/ai/tasks/subject_preheader/model': () => jsonResponse({ model: null }),
    })
    renderWithProviders(<Settings />)
    fireEvent.click(await screen.findByRole('button', { name: 'Save model' }))
    expect(await screen.findByText('Saved.')).toBeInTheDocument()
    // "the default" is sent as null, which points the task back at the deployment default.
    expect(await sentBodies(fetchMock, 'PUT')).toEqual([{ model: null }])
  })
})
