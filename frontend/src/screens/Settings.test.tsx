import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { Route, Routes } from 'react-router'

import Settings from './Settings'
import { AiPromptDetail } from './AiPrompts'
import { jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

/** One AI task's own page (task-372, decision 23): its model, output and prompt moved off General. */
function renderTask(key = 'subject_preheader') {
  return renderWithProviders(
    <Routes>
      <Route path="/settings/ai-prompts/:key" element={<AiPromptDetail />} />
    </Routes>,
    { route: `/settings/ai-prompts/${key}` },
  )
}

const SETTINGS = {
  signals: { weights: { click: 500, open: 0 }, half_lives: { click: 45, open: 45 } },
  signal_defaults: { weights: { click: 500, open: 0 }, half_lives: { click: 45, open: 45 } },
  known_contribution_types: ['click', 'open'],
  max_send_recipients: 200,
  session_absolute_hours: 12,
  session_idle_minutes: 60,
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
    period: 'month',
    period_start: '2026-10-01T00:00:00Z',
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
      held_form: true,
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
    // The tasks are not here: General points at their own part.
    expect(screen.queryByText('held for review')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'AI prompts' })).toHaveAttribute('href', '/settings/ai-prompts')
  })

  it("shows one AI task's model, output and prompt on its own page", async () => {
    stubFetch({ 'GET /settings': () => jsonResponse(SETTINGS) })
    const { container } = renderTask()
    expect(await screen.findByRole('heading', { name: 'Subject & preheader' })).toBeInTheDocument()
    expect(screen.getByText('held for review')).toBeInTheDocument()
    expect(screen.getByText('version 2 of 2')).toBeInTheDocument()
    expect(screen.getByText('the default (claude-opus-5)')).toBeInTheDocument()
    // Read-only too, without the permissions.
    expect(within(container).queryAllByRole('button')).toHaveLength(0)
  })

  it('shows every fact as a shared fact row, inset as the fields beside it (task-392 item 11)', async () => {
    stubFetch({ 'GET /settings': () => jsonResponse(SETTINGS) })
    const { container } = renderWithProviders(<Settings />)
    await screen.findByText('200')
    const terms = [...container.querySelectorAll('dt')]
    expect(terms.length).toBeGreaterThan(5)
    for (const term of terms) expect(term.parentElement).toHaveClass('fact')
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

  it('sets how often the AI budget refills, and says since when the figures count', async () => {
    const fetchMock = stubFetch({
      'GET /settings': () => jsonResponse(MANAGER),
      'PUT /settings/ai/budget-period': () => jsonResponse({ ...SETTINGS.ai_budget, period: 'quarter' }),
    })
    renderWithProviders(<Settings />)
    expect(await screen.findByText(/since/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Every month/ }))
    fireEvent.click(await screen.findByRole('option', { name: 'Every quarter' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save budget period' }))
    await waitFor(async () => expect(await sentBodies(fetchMock, 'PUT')).toEqual([{ period: 'quarter' }]))
  })

  it('sets how long a sign-in lasts, saying the ranges', async () => {
    const fetchMock = stubFetch({
      'GET /settings': () => jsonResponse(MANAGER),
      'PUT /settings/session-lengths': () => jsonResponse({ absolute_hours: 8, idle_minutes: 30 }),
    })
    renderWithProviders(<Settings />)
    const hours = await screen.findByLabelText(/A sign-in lasts at most \(hours, 1 to 72\)/)
    fireEvent.change(hours, { target: { value: '8' } })
    fireEvent.change(screen.getByLabelText(/no activity for \(minutes, 5 to 480\)/), { target: { value: '30' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save sign-in lengths' }))
    await waitFor(async () =>
      expect(await sentBodies(fetchMock, 'PUT')).toEqual([{ absolute_hours: 8, idle_minutes: 30 }]),
    )
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

  it('shows a validation list from the server as its messages, not a generic refusal', async () => {
    stubFetch({
      'GET /settings': () => jsonResponse(MANAGER),
      'PUT /settings/ai/spend-cap': () =>
        jsonResponse({ detail: [{ loc: ['body', 'hard_stop_usd'], msg: 'must be positive', type: 'value_error' }] }, 422),
    })
    renderWithProviders(<Settings />)

    fireEvent.click(await screen.findByRole('button', { name: 'Save AI budget' }))
    // Before task-253 a list detail was dropped and the screen said only that
    // the value was refused, not why.
    expect(await screen.findByText('Not saved: must be positive')).toBeInTheDocument()
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
    const { unmount } = renderTask()
    await screen.findByRole('button', { name: 'Save output mode' })
    expect(screen.queryByRole('button', { name: 'Save model' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save output mode' })).toBeInTheDocument()
    unmount()
    vi.unstubAllGlobals()

    const fetchMock = stubFetch({
      'GET /settings': () => jsonResponse({ ...MANAGER, may_configure_ai: true }),
      'PUT /settings/ai/tasks/subject_preheader/model': () => jsonResponse({ model: null }),
    })
    renderTask()
    fireEvent.click(await screen.findByRole('button', { name: 'Save model' }))
    expect(await screen.findByText('Saved.')).toBeInTheDocument()
    // "the default" is sent as null, which points the task back at the deployment default.
    expect(await sentBodies(fetchMock, 'PUT')).toEqual([{ model: null }])
  })
})

describe('a task with no approval step (ADR-140 addendum 2026-10-16)', () => {
  it('says so in place of the switch, even to someone who may manage', async () => {
    const draft = { ...SETTINGS.ai_tasks[0], key: 'content_draft', label: 'Content draft', held_form: false,
      approval_mode: 'auto_apply' }
    stubFetch({ 'GET /settings': () => jsonResponse({ ...SETTINGS, may_manage: true, ai_tasks: [draft, SETTINGS.ai_tasks[0]] }) })
    const { unmount } = renderTask('content_draft')
    expect(await screen.findByText(/no approval step/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Output of Content draft/ })).not.toBeInTheDocument()
    unmount()
    renderTask('subject_preheader')
    expect(await screen.findByRole('button', { name: /Output of Subject & preheader/ })).toBeInTheDocument()
  })
})

describe('signal tuning and prompts', () => {
  const MANAGER = { ...SETTINGS, may_manage: true, may_configure_ai: false }
  const AI = { ...SETTINGS, may_manage: true, may_configure_ai: true }

  function puts(fetchMock: ReturnType<typeof stubFetch>, method: string) {
    return Promise.all(
      fetchMock.mock.calls
        .map(([input]) => input as Request)
        .filter((r) => r.method === method)
        .map((r) => r.clone().json()),
    )
  }

  it('says what each default is, and leaves a blank field out so it falls back', async () => {
    const fetchMock = stubFetch({
      'GET /settings': () => jsonResponse(MANAGER),
      'PUT /settings/signals': () => jsonResponse(SETTINGS.signals),
    })
    renderWithProviders(<Settings />)

    const clickWeight = await screen.findByLabelText('Weight for click (default 500)')
    fireEvent.change(clickWeight, { target: { value: '400' } })
    fireEvent.change(screen.getByLabelText('Weight for open (default 0)'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save signal tuning' }))

    expect(await screen.findByText('Saved.')).toBeInTheDocument()
    expect(await puts(fetchMock, 'PUT')).toEqual([
      { weights: { click: 400 }, half_lives: { click: 45, open: 45 } },
    ])
  })

  it('does not send a value that is not a number', async () => {
    const fetchMock = stubFetch({ 'GET /settings': () => jsonResponse(MANAGER) })
    renderWithProviders(<Settings />)

    fireEvent.change(await screen.findByLabelText('Half-life in days for open (default 45)'), {
      target: { value: 'soon' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save signal tuning' }))

    expect(await screen.findByText('Not a number: open.')).toBeInTheDocument()
    expect(fetchMock.mock.calls.filter(([r]) => (r as Request).method === 'PUT')).toHaveLength(0)
  })

  it('offers publishing only to someone who may also run AI', async () => {
    stubFetch({ 'GET /settings': () => jsonResponse(MANAGER) })
    renderTask()
    await screen.findByRole('button', { name: 'Save output mode' })
    expect(screen.queryByRole('button', { name: /Publish as version/ })).not.toBeInTheDocument()
  })

  it('publishes a NEW version, named before and confirmed after by the server', async () => {
    /**
     * ADR-140 §3: a prompt is never edited, only superseded. The button names
     * the version it will create; the confirmation uses the server's number.
     */
    const fetchMock = stubFetch({
      'GET /settings': () => jsonResponse(AI),
      'POST /settings/ai/tasks/subject_preheader/prompt': () =>
        jsonResponse({ version: 3, body: 'Shorter.', is_published: true, created_at: '2026-10-03T00:00:00Z' }, 201),
    })
    renderTask()

    fireEvent.change(await screen.findByLabelText('Prompt for Subject & preheader'), {
      target: { value: 'Shorter.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Publish as version 3' }))

    expect(await screen.findByText('Published as version 3; it is now the live prompt.'))
      .toBeInTheDocument()
    expect(await puts(fetchMock, 'POST')).toEqual([{ body: 'Shorter.' }])
  })
})
