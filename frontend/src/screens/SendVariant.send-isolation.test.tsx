import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import { jsonResponse, makeQueryClient, page, renderWithProviders, stubFetch } from '../test-utils'
import SendVariant from './SendVariant'

afterEach(() => vi.unstubAllGlobals())

it('does not call the next planned send Sent after the previous send finishes (task-372; ADR-183)', async () => {
  let firstSent = false
  const writes: string[] = []
  const now = (id: number, recipients: number) => ({
    send_instance_id: id, status: id === 9 && firstSent ? 'sent' : 'draft', recipients, cap: 200,
    provider: 'mock', provider_label: 'mock', reaches_real_inboxes: false, from_address: null,
    scheduled_at: null,
  })
  const client = makeQueryClient()
  // Already visited: opening this send must not rely on a loading-screen
  // unmount to throw away the previous mutation's result.
  client.setQueryData(['deliveries', 10, 'recipients-now'], now(10, 5))
  stubFetch({
    'GET /campaigns/1/composition': () => jsonResponse({
      campaign: { id: 1, name: 'Spring' },
      variants: [{ variant: { id: 3, name: 'Main', channel: 'email' } }],
    }),
    'GET /settings': () => jsonResponse({ delivery_providers: [] }),
    'GET /snapshots/variants/3/preview': () => jsonResponse({
      channel: 'email', subject: 'Hello', html: '<p>Hello</p>',
    }),
    'GET /delivery/send-instances': () => jsonResponse(page([
      { id: 9, name: 'First send', status: firstSent ? 'sent' : 'draft', created_at: '2026-10-17T10:00:00Z' },
      { id: 10, name: 'Next send', status: 'draft', created_at: '2026-10-17T10:00:00Z' },
    ])),
    'GET /delivery/send-instances/9/recipients-now': () => jsonResponse(now(9, 3)),
    'GET /delivery/send-instances/10/recipients-now': () => jsonResponse(now(10, 5)),
    'POST /delivery/send-instances/9/send': () => {
      writes.push('9')
      firstSent = true
      return jsonResponse({ status: 'sent' })
    },
    'POST /delivery/send-instances/10/send': () => {
      writes.push('10')
      return jsonResponse({ status: 'sent' })
    },
  })
  renderWithProviders(
    <Routes><Route path="/campaigns/:id/variants/:variantId/send" element={<SendVariant />} /></Routes>,
    { client, route: '/campaigns/1/variants/3/send?send=9' },
  )
  fireEvent.click(await screen.findByRole('button', { name: 'Send to 3' }))
  expect(await screen.findByText('Sent.')).toHaveAttribute('role', 'status')
  const next = (await screen.findByText(/Next send — planned/)).closest('li')!
  fireEvent.click(within(next).getByRole('button', { name: 'Continue' }))
  await waitFor(() => expect(screen.getByRole('link', { name: 'The delivery' }))
    .toHaveAttribute('href', '/deliveries/10'))

  expect(writes).toEqual(['9'])
  expect(screen.queryByText('Sent.')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Send to 5' }))
  await waitFor(() => expect(writes).toEqual(['9', '10']))
})
