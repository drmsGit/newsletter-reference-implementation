import { screen, within } from '@testing-library/react'
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
