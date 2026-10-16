import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'

import ContentDraft from './ContentDraft'
import { jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

it('keeps a saved category after a partial failure and retries against its current assignment (task-368; ADR-141/080)', async () => {
  let cityAssigned = false
  let foodAssigned = false
  let foodAttempts = 0
  const writes: Request[] = []
  const category = (id: number, name: string, assigned: boolean) => ({
    category_id: id, name, score: 9, reason: 'From the source.',
    assigned_score: assigned ? 9 : null, assignment_id: assigned ? id + 100 : null,
  })
  stubFetch({
    'GET /content/42/drafts': () => jsonResponse([{
      run_id: 90, status: 'ok', created_at: '2026-10-16T10:00:00Z', provider: 'mock', model: 'mock',
      prompt_version: 1, input_tokens: 10, output_tokens: 20, fields: [], notices: [], reply: '{}', message: null,
      categories: [category(5, 'City breaks', cityAssigned), category(6, 'Food', foodAssigned)],
    }]),
    'GET /content/42/assignments': () => jsonResponse([]),
    'POST /content/42/categories': async (request: Request) => {
      writes.push(request.clone())
      const body = await request.json()
      if (body.category_id === 5) {
        expect(cityAssigned).toBe(false)
        cityAssigned = true
        return jsonResponse({ id: 105, content_id: 42, category_id: 5, score: 9 })
      }
      foodAttempts += 1
      if (foodAttempts === 1) return jsonResponse({ detail: 'Category service temporarily unavailable.' }, 503)
      foodAssigned = true
      return jsonResponse({ id: 106, content_id: 42, category_id: 6, score: 9 })
    },
    'PATCH /content/42/assignments/105': (request: Request) => {
      writes.push(request.clone())
      return jsonResponse({ id: 105, content_id: 42, category_id: 5, score: 9 })
    },
  } as never)
  renderWithProviders(<ContentDraft recordId={42} fields={[]} />)
  fireEvent.click(await screen.findByRole('button', { name: 'Assign ticked' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Category service temporarily unavailable.')
  expect(screen.queryByText('2 categories assigned.')).not.toBeInTheDocument()
  expect(screen.getByText(/on the record at 9/)).toBeInTheDocument()
  expect(cityAssigned).toBe(true)
  expect(foodAssigned).toBe(false)
  await waitFor(() => expect(screen.getByRole('button', { name: 'Assign ticked' })).toBeEnabled())

  fireEvent.click(screen.getByRole('button', { name: 'Assign ticked' }))
  expect(await screen.findByText('2 categories assigned.')).toHaveAttribute('role', 'status')
  expect(foodAssigned).toBe(true)
  expect(writes.map((request) => [request.method, new URL(request.url).pathname])).toEqual([
    ['POST', '/content/42/categories'], ['POST', '/content/42/categories'],
    ['PATCH', '/content/42/assignments/105'], ['POST', '/content/42/categories'],
  ])
  expect(await Promise.all(writes.map((request) => request.json()))).toEqual([
    { category_id: 5, score: 9, applied_suggestion_run_id: 90 },
    { category_id: 6, score: 9, applied_suggestion_run_id: 90 },
    { score: 9, applied_suggestion_run_id: 90 },
    { category_id: 6, score: 9, applied_suggestion_run_id: 90 },
  ])
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
})
