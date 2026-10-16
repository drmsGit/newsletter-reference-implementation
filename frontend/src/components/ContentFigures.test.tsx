import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { Performance, shareText } from './ContentFigures'
import { jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const FIGURES = { deliveries: 40, picked: 12, clicks: 9, unique_clickers: 7, clicks_in_deliveries: 30, click_share: 0.3 }

function open(body: object) {
  stubFetch({ 'GET /content/42/performance': () => jsonResponse(body) } as never)
  renderWithProviders(<Performance recordId={42} />)
}

describe("a record's figures (task-359; ADR-196 addendum 2026-10-16)", () => {
  it('says how often it went out, its clicks and its share of the clicks', async () => {
    open({ overall: FIGURES, by_campaign: [{ campaign_id: 3, campaign_name: 'Spring', figures: FIGURES }] })
    expect(await screen.findByText(/40 deliveries, 12 of them picked by a personalised block/)).toBeInTheDocument()
    expect(screen.getByText('9, from 7 deliveries')).toBeInTheDocument()
    expect(screen.getByText(/of the 30 clicks in the emails that carried it/)).toBeInTheDocument()
    const table = screen.getByRole('grid', { name: 'By campaign' })
    expect(within(table).getByText('Spring')).toBeInTheDocument()
    expect(within(table).getByText('30 %')).toBeInTheDocument()
  })

  it('says plainly when it has not been sent', async () => {
    open({ overall: { ...FIGURES, deliveries: 0, picked: 0, clicks: 0, unique_clickers: 0, clicks_in_deliveries: 0,
      click_share: null }, by_campaign: [] })
    expect(await screen.findByText(/has been sent yet/)).toBeInTheDocument()
  })

  it('tells no clicks apart from a share of nothing', () => {
    expect(shareText({ ...FIGURES, click_share: null })).toBe('No clicks yet')
    expect(shareText({ ...FIGURES, deliveries: 0 })).toBe('Not sent yet')
    expect(shareText(FIGURES)).toBe('30 %')
  })
})
