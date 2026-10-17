import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import TopicProposal from './TopicProposal'
import { jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const T = '2026-10-17T10:00:00Z'
const PROPOSAL = {
  run_id: 80, status: 'ok', created_at: T, provider: 'mock', model: 'mock-1', prompt_version: 1,
  input_tokens: 400, output_tokens: 100, offered: 60, reply: '{}', message: null,
  notices: ['Not offered, so left out: record 999.'],
  hero: { record_id: 1, title: 'Lisbon', reason: 'The city.' },
  editorial: 'Three cities for a long weekend.',
  blocks: [{ record_id: 2, title: 'Porto', reason: 'Nearby.' }, { record_id: 3, title: 'Madrid', reason: 'Food.' }],
  slot: { category_ids: [7], categories: ['City'], reason: 'Each reader picks.' },
  subject: 'A long weekend in Iberia', preheader: 'Lisbon, Porto, Madrid',
}

function open(handlers: Record<string, (r: Request) => Response | Promise<Response>> = {}) {
  const writes: Request[] = []
  const fetchMock = stubFetch({
    'GET /campaigns/variants/3/topic-proposals': () => jsonResponse([PROPOSAL]),
    'POST /campaigns/variants/3/build-from-proposal': (r: Request) => (writes.push(r.clone()), jsonResponse({ built: 5 })),
    'GET /campaigns/1/composition': () => jsonResponse({ campaign: {}, variants: [] }),
    ...handlers,
  } as never)
  renderWithProviders(<TopicProposal campaignId={1} variantId={3} />)
  return { writes, fetchMock }
}

describe('preparing a variant from a topic (task-370)', () => {
  it('asks once with the topic, then shows the proposed stack in order', async () => {
    let answer: (r: Response) => void = () => {}
    let proposals: unknown[] = []
    const { fetchMock } = open({
      'GET /campaigns/variants/3/topic-proposals': () => jsonResponse(proposals),
      'POST /campaigns/variants/3/topic-proposals': () => new Promise<Response>((resolve) => (answer = resolve)),
    })
    fireEvent.change(screen.getByLabelText(/^Topic/), { target: { value: 'City breaks in Iberia' } })
    fireEvent.click(screen.getByRole('button', { name: 'Propose a variant' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Asking the model…' }))
    const posts = fetchMock.mock.calls.map(([r]) => r as Request).filter((r) => r.method === 'POST')
    expect(posts).toHaveLength(1)
    expect(await posts[0].clone().json()).toEqual({ topic: 'City breaks in Iberia' })
    proposals = [PROPOSAL]
    await act(async () => answer(jsonResponse({ outcome: 'inline', message: null, ai_run_id: 80, pending_action_id: null })))
    const items = (await screen.findByRole('list', { name: 'Proposed stack' })).querySelectorAll(':scope > li')
    expect([...items].map((li) => (li.querySelector('strong') ?? li.querySelector('label'))?.textContent))
      .toEqual(['Hero', 'Editorial', 'Image left', 'Image right', 'Slot', 'Subject'])
    expect(screen.getByText(/among the 60 most recently created/)).toBeInTheDocument()
    expect(screen.getByText('Not offered, so left out: record 999.')).toBeInTheDocument()
  })

  it('shows a refused topic on the field and a refused variant in words', async () => {
    open({
      'POST /campaigns/variants/3/topic-proposals': () =>
        jsonResponse({ detail: [{ loc: ['body', 'topic'], msg: 'Name the topic.' }] }, 422),
    })
    fireEvent.click(screen.getByRole('button', { name: 'Propose a variant' }))
    expect(await screen.findByText('Name the topic.')).toBeInTheDocument()
  })

  it('builds only the ticked parts, the editorial as edited, left and right following the ticks', async () => {
    const { writes } = open()
    fireEvent.click(await screen.findByRole('checkbox', { name: 'Block: Porto' }))
    // Porto left out, so Madrid moves to the left.
    expect(screen.getByRole('checkbox', { name: 'Block: Madrid' }).closest('li')).toHaveTextContent(/^Image left/)
    fireEvent.click(screen.getByRole('checkbox', { name: 'Slot by categories' }))
    fireEvent.change(screen.getByLabelText(/^Editorial/), { target: { value: 'Two cities.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Build the variant' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toEqual({
      run_id: 80, hero: true, editorial: 'Two cities.', blocks: [3], slot: false, envelope: true,
    })
  })

  it('says why a build was refused', async () => {
    open({
      'POST /campaigns/variants/3/build-from-proposal': () =>
        jsonResponse({ detail: 'This variant already has content blocks.' }, 409),
    })
    fireEvent.click(await screen.findByRole('button', { name: 'Build the variant' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('already has content blocks')
  })

  it('shows what the model said when nothing could be read', async () => {
    open({
      'GET /campaigns/variants/3/topic-proposals': () => jsonResponse([{ ...PROPOSAL, hero: null, editorial: '',
        blocks: [], slot: null, notices: [], reply: 'I cannot.' }]),
    })
    expect(await screen.findByText('I cannot.')).toBeInTheDocument()
  })

  it('shows a refused run in words', async () => {
    open({
      'GET /campaigns/variants/3/topic-proposals': () => jsonResponse([{ ...PROPOSAL, status: 'blocked',
        message: 'No published prompt for this task — publish one in Settings.' }]),
    })
    expect(await screen.findByRole('alert')).toHaveTextContent('publish one in Settings')
  })
})
