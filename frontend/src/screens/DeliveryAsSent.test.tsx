import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import DeliveryAsSent from './DeliveryAsSent'
import { jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

describe('what one recipient got (task-109)', () => {
  it('lists every copy of a slot module that showed several picks, in order', async () => {
    const slot = { module_id: 12, module_type: 'single_stack', kind: 'slot', override_id: null }
    stubFetch({
      'GET /delivery/executions/7/as-sent': () => jsonResponse({
        execution_id: 7, send_instance_id: 3, recipient_id: 1, channel: 'email', sent_at: '2026-10-11T10:00:00Z',
        envelope: { subject: 'Hello' }, body: '<html></html>', fields: null,
        modules: [
          { module_id: 9, module_type: 'envelope', kind: 'static', rank: null, content_record_id: null,
            content_version_id: null, override_id: null, decision_resolution_id: null },
          { ...slot, rank: 1, content_record_id: 41, content_version_id: 410, decision_resolution_id: 1 },
          { ...slot, rank: 2, content_record_id: 42, content_version_id: 420, decision_resolution_id: 2 },
        ],
        templates_match: true, hash_matches: true,
      }),
    })
    renderWithProviders(
      <Routes>
        <Route path="/deliveries/:id/executions/:executionId" element={<DeliveryAsSent />} />
      </Routes>,
      { route: '/deliveries/3/executions/7' },
    )
    const table = await screen.findByRole('grid', { name: 'Modules in this message' })
    const rows = within(table).getAllByRole('row').slice(1)
    expect(rows).toHaveLength(3)
    expect(rows[1]).toHaveTextContent('slot (pick 1)')
    expect(rows[1]).toHaveTextContent('41')
    expect(rows[2]).toHaveTextContent('slot (pick 2)')
    expect(rows[2]).toHaveTextContent('42')
  })
})
