import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import Translations, { LanguageChoice } from './Translations'
import { jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const T = '2026-10-17T10:00:00Z'
const FIELDS = [
  { name: 'headline_medium', label: 'Headline', channel: 'email', type: 'text', concept: 'headline' },
  { name: 'body_medium', label: 'Body text (short)', channel: 'email', type: 'richtext', concept: 'body' },
]
const RECORD = {
  id: 42, title: 'Lisbon', description: null, content: {}, status: 'active', updated_at: T, language: 'en',
  latest_version_number: 1, unpublished_changes: false, machine_ready: false, readiness: [],
  language_choices: ['de', 'en', 'fr'], language_locked: null, original: null,
  translations: [{ id: 50, title: 'Lissabon', language: 'de' }], original_changed: [],
}
const TWIN = {
  ...RECORD, id: 50, title: 'Lissabon', language: 'de', latest_version_number: null, translations: [],
  original: { id: 42, title: 'Lisbon', language: 'en' }, language_locked: 'This record is a translation, so its language stays.',
}
const PROPOSAL = {
  run_id: 95, status: 'ok', created_at: T, provider: 'mock', model: 'mock-1', prompt_version: 1, input_tokens: 9,
  output_tokens: 9, reply: '{}', message: null, notices: [], categories: [],
  fields: [
    { name: 'title', label: 'Title', channel: null, text: 'Lissabon neu', current: 'Lissabon' },
    { name: 'headline_medium', label: 'Headline', channel: 'email', text: 'Vier Tage', current: 'Drei Tage' },
  ],
}

function open(record: object, handlers: Record<string, (r: Request) => Response | Promise<Response>> = {}) {
  const writes: Request[] = []
  const fetchMock = stubFetch({
    'GET /content/42': () => jsonResponse(RECORD),
    'GET /content/50': () => jsonResponse(TWIN),
    'PATCH /content/42': (r: Request) => (writes.push(r.clone()), jsonResponse(RECORD)),
    'PATCH /content/50': (r: Request) => (writes.push(r.clone()), jsonResponse(TWIN)),
    'GET /content/50/retranslations': () => jsonResponse([PROPOSAL]),
    ...handlers,
  } as never)
  renderWithProviders(
    <Routes>
      <Route path="/content/:id" element={<>
        <LanguageChoice record={record as never} />
        <Translations record={record as never} fields={FIELDS as never} />
      </>} />
      <Route path="/content/77" element={<p>The new record</p>} />
    </Routes>,
    { route: `/content/${(record as { id: number }).id}` },
  )
  return { writes, fetchMock }
}

describe("a record's language (ADR-200 point 1)", () => {
  it('offers the brand profile languages and not set, and saves the choice', async () => {
    const { writes } = open(RECORD)
    fireEvent.click(screen.getByRole('button', { name: /Language/ }))
    fireEvent.click(await screen.findByRole('option', { name: 'German' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toMatchObject({ language: 'de' })
    fireEvent.click(screen.getByRole('button', { name: /Language/ }))
    fireEvent.click(await screen.findByRole('option', { name: 'Not set (any language)' }))
    await waitFor(() => expect(writes).toHaveLength(2))
    expect(await writes[1].json()).toMatchObject({ language: null })
  })

  it('says why a language was refused', async () => {
    open(RECORD, {
      'PATCH /content/42': () =>
        jsonResponse({ detail: [{ loc: ['body', 'language'], msg: 'This record has translations, so its language stays.' }] }, 422),
    })
    fireEvent.click(screen.getByRole('button', { name: /Language/ }))
    fireEvent.click(await screen.findByRole('option', { name: 'French' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('so its language stays')
  })

  it('shows a locked language as text with the reason', () => {
    open(TWIN)
    expect(screen.queryByRole('button', { name: /Language/ })).not.toBeInTheDocument()
    expect(screen.getByText(/so its language stays/)).toBeInTheDocument()
  })
})

describe('translating (ADR-200 points 3-5)', () => {
  it("lists the original's translations and offers only the languages it has none in", async () => {
    open(RECORD)
    expect(within(screen.getByRole('list', { name: 'Translations of this record' })).getByRole('link', { name: 'Lissabon' }))
      .toHaveAttribute('href', '/content/50')
    fireEvent.click(screen.getByRole('button', { name: /Translate into/ }))
    const options = (await screen.findAllByRole('option')).map((o) => o.textContent)
    expect(options).toEqual(['French'])
  })

  it('translates once and opens the new record', async () => {
    let answer: (r: Response) => void = () => {}
    const { fetchMock } = open(RECORD, {
      'POST /content/42/translations': () => new Promise<Response>((resolve) => (answer = resolve)),
    })
    fireEvent.click(screen.getByRole('button', { name: 'Translate with AI' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Asking the model…' }))
    const posts = fetchMock.mock.calls.map(([r]) => r as Request).filter((r) => r.method === 'POST')
    expect(posts).toHaveLength(1)
    expect(await posts[0].clone().json()).toEqual({ language: 'fr' })
    await act(async () => answer(jsonResponse({ record_id: 77, ai_run_id: 9, notices: [] }, 201)))
    expect(await screen.findByText('The new record')).toBeInTheDocument()
  })

  it("asks for the original's own language first", () => {
    open({ ...RECORD, language: null, translations: [] })
    expect(screen.getByText(/Set this record.s language above to translate it/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Translate with AI' })).not.toBeInTheDocument()
  })

  it('shows a refusal in words', async () => {
    open(RECORD, {
      'POST /content/42/translations': () =>
        jsonResponse({ detail: [{ loc: ['body', 'language'], msg: "'fr' is none of this brand's profile languages." }] }, 422),
    })
    fireEvent.click(screen.getByRole('button', { name: 'Translate with AI' }))
    expect(await screen.findByRole('alert')).toHaveTextContent("none of this brand's profile languages")
  })

  it('says where a translation came from, and to review it before publishing', () => {
    open(TWIN)
    expect(screen.getByRole('link', { name: 'Lisbon' })).toHaveAttribute('href', '/content/42')
    expect(screen.getByText(/review it before publishing/)).toBeInTheDocument()
    expect(screen.getByText('Up to date with the original.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Translate again' })).not.toBeInTheDocument()
  })

  it('names what changed in the original, and takes a fresh translation field by field, title included', async () => {
    const { writes, fetchMock } = open({ ...TWIN, original_changed: ['headline_medium', 'title'] }, {
      'POST /content/50/retranslations': () => jsonResponse({ ai_run_id: 95, status: 'ok', message: null }),
    })
    expect(screen.getByText(/The original changed since this was translated: Headline, Title/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Translate again' }))
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([r]) => r as Request).filter((r) => r.method === 'POST')).toHaveLength(1))
    // What changed in the original starts ticked, though the record has text there.
    expect(await screen.findByRole('checkbox', { name: 'Title' })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'Headline' })).toBeChecked()
    fireEvent.click(screen.getByRole('button', { name: 'Use ticked fields' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toEqual({
      title: 'Lissabon neu', content: { headline_medium: 'Vier Tage' }, groups: ['email'], applied_suggestion_run_id: 95,
    })
  })
})
