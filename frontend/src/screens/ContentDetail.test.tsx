import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import ContentDetail from './ContentDetail'
import { jsonResponse, page, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const RECORD = {
  id: 42, title: 'Lisbon in spring', description: null, status: 'active', content: {},
  updated_at: '2026-10-04T10:00:00Z', latest_version_number: 1, unpublished_changes: false,
}

function open(campaigns: object[], total = campaigns.length) {
  const fetchMock = stubFetch({
    'GET /content/42': () => jsonResponse(RECORD),
    'GET /content/42/campaigns': () => jsonResponse(page(campaigns, { total })),
  })
  renderWithProviders(
    <Routes>
      <Route path="/content/:id" element={<ContentDetail />} />
    </Routes>,
    { route: '/content/42' },
  )
  return fetchMock
}

describe('where a record is used (task-267)', () => {
  it('links each campaign and each variant that uses it, and marks a sent one', async () => {
    open([
      { id: 1, name: 'Spring', variants: [
        { id: 3, name: 'Variant A', channel: 'email', stage: 'composing' },
        { id: 4, name: 'Variant B', channel: 'push', stage: 'sent' },
      ] },
    ])
    const section = await screen.findByRole('region', { name: 'Used in' })
    expect(await within(section).findByRole('link', { name: 'Spring' })).toHaveAttribute('href', '/campaigns/1')
    expect(within(section).getByRole('link', { name: 'Variant B' })).toHaveAttribute('href', '/campaigns/1/variants/4')
    const sent = within(section).getByText('(push, sent)')
    expect(sent).toHaveClass('used-in__sent')
    expect(within(section).getByText('(email, composing)')).not.toHaveClass('used-in__sent')
  })

  it('says so when no campaign uses it', async () => {
    open([])
    expect(await screen.findByText('No campaign has a module bound to this record.')).toBeInTheDocument()
  })

  it('says how many there are when not all fit on the page', async () => {
    open([{ id: 1, name: 'Spring', variants: [{ id: 3, name: 'A', channel: 'email', stage: 'sent' }] }], 51)
    expect(await screen.findByText('Showing 1 of 51 campaigns.')).toBeInTheDocument()
  })
})
