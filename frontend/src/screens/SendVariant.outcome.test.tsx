import { fireEvent, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import SendVariant from './SendVariant'
import { jsonResponse, renderWithProviders } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

// Task-323: completed execution must not imply successful delivery.
// ADR-183 governs the send flow; all requests are intercepted locally.
it.each(['failed', 'partial_failed', 'no_recipients'])(
  'does not label a %s outcome as sent',
  async (outcome) => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const request = input instanceof Request ? input : new Request(input)
      const path = new URL(request.url).pathname
      if (path === '/campaigns/1/composition')
        return jsonResponse({
          campaign: { id: 1, name: 'Spring' },
          variants: [{ variant: { id: 3, name: 'Main', channel: 'email' } }],
        })
      if (path === '/settings') return jsonResponse({ delivery_providers: [] })
      if (path === '/snapshots/variants/3/preview')
        return jsonResponse({ channel: 'email', subject: 'Hello', html: '<p>Hello</p>' })
      if (path === '/delivery/send-instances/9/recipients-now')
        return jsonResponse({
          send_instance_id: 9, status: 'draft', recipients: 3, cap: 200,
          provider: 'mock', provider_label: 'mock', reaches_real_inboxes: false,
        })
      if (path === '/delivery/send-instances/9/send' && request.method === 'POST')
        return jsonResponse({ status: outcome })
      throw new Error(`Unexpected request: ${request.method} ${path}`)
    }))
    renderWithProviders(
      <Routes>
        <Route path="/campaigns/:id/variants/:variantId/send" element={<SendVariant />} />
      </Routes>,
      { route: '/campaigns/1/variants/3/send?send=9' },
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Send to 3' }))
    const notice = await screen.findByText(new RegExp(outcome.replace('_', ' '), 'i'))
    expect(notice).toHaveAttribute('role', 'status')
    expect(notice).not.toHaveTextContent(/^Sent:/i)
  },
)
