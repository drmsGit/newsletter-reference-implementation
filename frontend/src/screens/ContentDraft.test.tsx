import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router'

import ContentDraft from './ContentDraft'
import { jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const T = '2026-10-16T10:00:00Z'
const FIELDS = [
  { name: 'headline_medium', label: 'Headline', channel: 'email', type: 'text', concept: 'headline' },
  { name: 'body_medium', label: 'Body text (short)', channel: 'email', type: 'richtext', concept: 'body' },
  { name: 'push_title', label: 'Notification title', channel: 'push', type: 'text', concept: 'push_title' },
]
const DRAFT = {
  run_id: 90, status: 'ok', created_at: T, provider: 'mock', model: 'mock-1', prompt_version: 1,
  input_tokens: 300, output_tokens: 120, reply: '{}', message: null,
  notices: ['Not in the category list, so left out: Nightlife.'],
  fields: [
    { name: 'headline_medium', label: 'Headline', channel: 'email', text: 'Three days in Lisbon', current: 'Mine' },
    { name: 'body_medium', label: 'Body text (short)', channel: 'email', text: 'Ride tram 28.', current: '' },
    { name: 'push_title', label: 'Notification title', channel: 'push', text: 'Lisbon calls', current: '' },
  ],
  categories: [
    { category_id: 5, name: 'City breaks', score: 9, reason: 'A short city trip.', assigned_score: null, assignment_id: null },
    { category_id: 6, name: 'Food', score: 6, reason: 'Pastries.', assigned_score: 3, assignment_id: 61 },
  ],
}

function open(handlers: Record<string, (r: Request) => Response | Promise<Response>>) {
  const writes: Request[] = []
  const write = (body: unknown, status = 200) => (r: Request) => (writes.push(r.clone()), jsonResponse(body, status))
  const fetchMock = stubFetch({
    'GET /content/42/drafts': () => jsonResponse([DRAFT, { ...DRAFT, run_id: 80 }]),
    'PATCH /content/42': write({ id: 42 }),
    'POST /content/42/categories': write({ id: 70, content_id: 42, category_id: 5, score: 9 }),
    'PATCH /content/42/assignments/61': write({ id: 61, content_id: 42, category_id: 6, score: 6 }),
    'GET /content/42': () => jsonResponse({ id: 42, updated_at: T }),
    'GET /content/42/assignments': () => jsonResponse([]),
    ...handlers,
  } as never)
  renderWithProviders(<ContentDraft recordId={42} fields={FIELDS as never} />)
  return { writes, fetchMock }
}

describe('drafting a record with AI (task-368)', () => {
  it('asks with the source and the ticked channels, once, and shows the newest draft', async () => {
    let answer: (r: Response) => void = () => {}
    let drafts: unknown[] = []
    const { fetchMock } = open({
      // Nothing yet: the draft is there only once it was asked for, so it shows only if re-read.
      'GET /content/42/drafts': () => jsonResponse(drafts),
      'POST /content/42/drafts': () => new Promise<Response>((resolve) => (answer = resolve)),
    })
    fireEvent.change(screen.getByLabelText(/^Source/), { target: { value: 'Lisbon in spring' } })
    fireEvent.click(screen.getByRole('checkbox', { name: 'Push' }))
    fireEvent.click(screen.getByRole('button', { name: 'Draft with AI' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Asking the model…' }))
    const posts = fetchMock.mock.calls.map(([r]) => r as Request).filter((r) => r.method === 'POST')
    expect(posts).toHaveLength(1)
    expect(await posts[0].clone().json()).toEqual({ source: 'Lisbon in spring', channels: ['email'] })
    drafts = [DRAFT]
    await act(async () => answer(jsonResponse({ ai_run_id: 90, status: 'ok', message: null })))
    expect(await screen.findByText('Three days in Lisbon', { exact: false })).toBeInTheDocument()
    expect(screen.getByText('Not in the category list, so left out: Nightlife.')).toBeInTheDocument()
    expect(screen.getByText(/420 tokens/)).toBeInTheDocument()
  })

  it('ticks every channel even when the fields arrive after the panel', async () => {
    stubFetch({ 'GET /content/42/drafts': () => jsonResponse([]) } as never)
    const { rerender, client } = renderWithProviders(<ContentDraft recordId={42} fields={[]} />)
    rerender(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <ContentDraft recordId={42} fields={FIELDS as never} />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(screen.getByRole('checkbox', { name: 'Email' })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'Push' })).toBeChecked()
  })

  it('says on the box that the personal details stay out and how long it may be', () => {
    open({})
    expect(screen.getByText(/not anyone.s personal details/)).toHaveTextContent('0 of 12,000 characters')
  })

  it('shows a refusal on the field at fault', async () => {
    open({
      'POST /content/42/drafts': () =>
        jsonResponse({ detail: [{ loc: ['body', 'source'], msg: 'Paste the text to draft from.' }] }, 422),
    })
    fireEvent.click(await screen.findByRole('button', { name: 'Draft with AI' }))
    expect(await screen.findByText('Paste the text to draft from.')).toBeInTheDocument()
  })

  it('leaves a filled field unticked and saves the ticked ones in one edit, naming the run', async () => {
    const { writes } = open({})
    const headline = await screen.findByRole('checkbox', { name: 'Headline' })
    expect(headline).not.toBeChecked()
    expect(screen.getByText(/now: Mine/)).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: 'Body text (short)' })).toBeChecked()
    fireEvent.click(screen.getByRole('button', { name: 'Use ticked fields' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toEqual({
      content: { body_medium: 'Ride tram 28.', push_title: 'Lisbon calls' },
      groups: ['email', 'push'], applied_suggestion_run_id: 90,
    })
    expect(await screen.findByText('2 fields saved.')).toHaveAttribute('role', 'status')
  })

  it('assigns the ticked categories with the chosen score, and re-scores one already on the record', async () => {
    let assigned = false
    const { writes } = open({
      // After the assignment the draft is re-read and says what the record now holds.
      'GET /content/42/drafts': () => jsonResponse([assigned ? { ...DRAFT, categories: [
        { ...DRAFT.categories[0], assigned_score: 7, assignment_id: 70 }, DRAFT.categories[1]] } : DRAFT]),
      'POST /content/42/categories': (r) => ((assigned = true), writes.push(r.clone()),
        jsonResponse({ id: 70, content_id: 42, category_id: 5, score: 7 })),
    })
    const food = await screen.findByRole('checkbox', { name: 'Food' })
    expect(food).not.toBeChecked()
    expect(screen.getByText(/on the record at 3/)).toBeInTheDocument()
    fireEvent.click(food)
    const scoreFor = within(screen.getByText('City breaks').closest('.draft-category') as HTMLElement)
    fireEvent.click(scoreFor.getByRole('button', { name: /Score for City breaks/ }))
    fireEvent.click(await screen.findByRole('option', { name: '7' }))
    fireEvent.click(screen.getByRole('button', { name: 'Assign ticked' }))
    await waitFor(() => expect(writes).toHaveLength(2))
    expect(writes[0].url).toMatch(/\/content\/42\/categories$/)
    expect(await writes[0].json()).toEqual({ category_id: 5, score: 7, applied_suggestion_run_id: 90 })
    expect(writes[1].url).toMatch(/\/assignments\/61$/)
    expect(await writes[1].json()).toEqual({ score: 6, applied_suggestion_run_id: 90 })
    expect(await screen.findByText(/on the record at 7/)).toBeInTheDocument()
  })

  it('shows what the model said when nothing could be read, and why a run was refused', async () => {
    open({
      'GET /content/42/drafts': () => jsonResponse([{ ...DRAFT, fields: [], categories: [], notices: [], reply: 'No.' }]),
    })
    expect(await screen.findByText('No.')).toBeInTheDocument()
  })

  it('shows a refused run in words', async () => {
    open({
      'GET /content/42/drafts': () => jsonResponse([{ ...DRAFT, status: 'blocked', fields: [], categories: [],
        message: 'No published prompt for this task — publish one in Settings.' }]),
    })
    expect(await screen.findByRole('alert')).toHaveTextContent('publish one in Settings')
  })
})
