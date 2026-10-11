import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import BrandProfileDetail from './BrandProfileDetail'
import { jsonResponse, makeQueryClient, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

it('preserves an unsaved profile field when a background refresh brings a newer version', async () => {
  const state = {
    id: 2, name: 'Calm', language: 'en', kind: 'marketing', is_default: false,
    complete: true, missing: [], may_manage: true,
    updated_at: '2026-10-11T10:00:01.000000Z',
    field_values: { legal_company_name: 'Original company' },
  }
  let reads = 0
  stubFetch({
    'GET /brand-profiles/2': () => { reads += 1; return jsonResponse(state) },
    'GET /brand-profiles/structure': () => jsonResponse([{
      name: 'legal_company_name', type: 'text', label: 'Legal company name',
      group: 'Legal details', multiline: false, core: true,
      required_for: ['marketing', 'transactional'],
    }]),
  })
  const client = makeQueryClient()
  renderWithProviders(
    <Routes><Route path="/settings/brand-profiles/:id" element={<BrandProfileDetail />} /></Routes>,
    { client, route: '/settings/brand-profiles/2' },
  )
  fireEvent.change(await screen.findByLabelText(/^Legal company name/), {
    target: { value: 'My unsaved company' },
  })
  expect(screen.getByRole('button', { name: 'Save' })).toBeEnabled()

  // A focus refresh or another mutation can invalidate the cached read while
  // the editor is dirty. No explicit discard or reload was requested here.
  state.field_values.legal_company_name = 'Other manager company'
  state.updated_at = '2026-10-11T10:00:02.000000Z'
  await act(async () => { await client.invalidateQueries() })
  await waitFor(() => expect(reads).toBe(2))
  expect(screen.getByLabelText(/^Legal company name/)).toHaveValue('My unsaved company')
})
