import { fireEvent, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import Monitoring from './Monitoring'
import { jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const ROW = {
  id: 1,
  name: 'Spring',
  state: 'in_flight',
  has_failures: true,
  next_scheduled_at: '2026-10-03T09:00:00Z',
  last_sent_at: null,
  updated_at: '2026-10-02T09:00:00Z',
  variants: [
    { id: 3, name: 'Main', channel: 'email', stage: 'scheduled', has_failures: false },
    { id: 4, name: 'Push', channel: 'push', stage: 'snapshotted', has_failures: true },
  ],
}

describe('the monitoring screen', () => {
  it("shows the server's state and each variant's stage, failures included", async () => {
    stubFetch({ 'GET /campaigns/monitoring': () => jsonResponse([ROW]) })
    renderWithProviders(<Monitoring />)

    expect(await screen.findByText('In flight — with failures')).toBeInTheDocument()
    expect(
      screen.getByText('Main (email): scheduled; Push (push): approved, not planned'),
    ).toBeInTheDocument()
  })

  it('opens the campaign from its row', async () => {
    stubFetch({ 'GET /campaigns/monitoring': () => jsonResponse([ROW]) })
    renderWithProviders(
      <Routes>
        <Route path="/monitoring" element={<Monitoring />} />
        <Route path="/campaigns/:id" element={<p>campaign screen</p>} />
      </Routes>,
      { route: '/monitoring' },
    )
    fireEvent.click(await screen.findByText('Spring'))
    expect(await screen.findByText('campaign screen')).toBeInTheDocument()
  })
})
