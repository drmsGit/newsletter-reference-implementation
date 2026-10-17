import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import Deliveries, { DeliveriesSplit, NoSendOpen } from './Deliveries'
import DeliveryAsSent from './DeliveryAsSent'
import DeliveryDetail from './DeliveryDetail'
import { jsonResponse, page, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const A_SEND = {
  id: 4,
  snapshot_id: 9,
  name: 'Spring launch — send 1',
  status: 'sent',
  provider: 'mock',
  scheduled_at: null,
  created_at: '2026-10-02T09:00:00Z',
  updated_at: '2026-10-02T09:05:00Z',
  from_address: 'news@example.invalid',
  audience_group_id: 3,
  sent_count: 2,
  failed_count: 0,
  excluded_count: 1,
}

function execution(id: number, status: string, extra: object = {}) {
  return {
    id,
    send_instance_id: 4,
    recipient_id: 100 + id,
    status,
    provider: 'mock',
    provider_message_id: null,
    created_at: '2026-10-02T09:00:00Z',
    updated_at: '2026-10-02T09:05:00Z',
    recipient_external_id: `ext-${id}`,
    exclusion_reason: null,
    sent_at: status === 'sent' ? '2026-10-02T09:05:00Z' : null,
    ...extra,
  }
}

const AS_SENT = {
  execution_id: 11,
  send_instance_id: 4,
  recipient_id: 111,
  channel: 'email',
  sent_at: '2026-10-02T09:05:00Z',
  envelope: { subject: 'Spring is here', preheader: 'Three new trips' },
  body: '<html><body><h1>Spring is here</h1><script>parent.x=1</script></body></html>',
  fields: null,
  modules: [
    {
      module_id: 1,
      module_type: 'hero',
      kind: 'content',
      content_record_id: 42,
      content_version_id: 7,
      override_id: null,
      decision_resolution_id: null,
    },
  ],
  templates_match: true,
  hash_matches: true,
}

function renderAsSent() {
  return renderWithProviders(
    <Routes>
      <Route path="/deliveries/:id/executions/:executionId" element={<DeliveryAsSent />} />
    </Routes>,
    { route: '/deliveries/4/executions/11' },
  )
}

describe('the deliveries list', () => {
  it("shows the server's counts and where each send came from", async () => {
    stubFetch({
      'GET /delivery/send-instances': () =>
        jsonResponse(page([
          {
            ...A_SEND,
            campaign_id: 1,
            campaign_name: 'Spring',
            variant_id: 2,
            variant_name: 'Main',
            execution_count: 3,
            event_count: 0,
          },
        ])),
    })
    renderWithProviders(<Deliveries />)

    expect(await screen.findByText('Spring launch — send 1')).toBeInTheDocument()
    expect(screen.getByText('Spring / Main')).toBeInTheDocument()
    expect(screen.getByText('2 / 0 / 1')).toBeInTheDocument()
    // Everything fits on one page, so there is nothing to page through.
    expect(screen.queryByRole('navigation', { name: 'Pages' })).not.toBeInTheDocument()
  })
})

describe('a send in detail', () => {
  function stubDetail() {
    stubFetch({
      'GET /delivery/send-instances/4': () =>
        jsonResponse({
          ...A_SEND,
          execution_count: 3,
          exclusions_by_stage: { consent: 1 },
          audience_group_name: 'Spring travellers',
        }),
      'GET /delivery/send-instances/4/executions': () =>
        jsonResponse(page([
          execution(11, 'sent'),
          execution(12, 'excluded', { exclusion_reason: 'consent' }),
        ])),
    })
    renderWithProviders(
      <Routes>
        <Route path="/deliveries/:id" element={<DeliveryDetail />} />
      </Routes>,
      { route: '/deliveries/4' },
    )
  }

  it('explains the gap between planned and sent, by stage', async () => {
    /**
     * ADR-176 point 4 makes exclusions routine: a manager who approved three and
     * sees two sent needs the reason, and the stage counts are that reason.
     */
    stubDetail()
    expect(await screen.findByText('Excluded: consent')).toBeInTheDocument()
    expect(screen.getByText('Spring travellers')).toBeInTheDocument()
  })

  it('links to "as sent" only for a recipient who was sent something', async () => {
    /**
     * Only a sent execution has a delivery record (ADR-183). A link on the
     * excluded row could only end in "nothing to show".
     */
    stubDetail()
    const links = await screen.findAllByRole('link', { name: 'As sent' })
    expect(links).toHaveLength(1)
    expect(links[0]).toHaveAttribute('href', '/deliveries/4/executions/11')
  })

  it("answers another brand's send as absent", async () => {
    stubFetch({
      'GET /delivery/send-instances/4': () => jsonResponse({ detail: 'not found' }, 404),
      'GET /delivery/send-instances/4/executions': () => jsonResponse(page([])),
    })
    renderWithProviders(
      <Routes>
        <Route path="/deliveries/:id" element={<DeliveryDetail />} />
      </Routes>,
      { route: '/deliveries/4' },
    )
    expect(await screen.findByRole('alert')).toHaveTextContent('That record does not exist.')
  })
})

describe('a message as sent', () => {
  it('renders the message in a frame with every permission withheld', async () => {
    /**
     * **The assertion that keeps email HTML out of this origin.** An empty
     * `sandbox` refuses scripts, forms and popups and gives the frame an origin
     * of its own; any token added to it -- `allow-scripts`, `allow-same-origin`
     * -- would let a stored message act as the person viewing it.
     */
    stubFetch({ 'GET /delivery/executions/11/as-sent': () => jsonResponse(AS_SENT) })
    renderAsSent()

    const frame = await screen.findByTitle('The message as sent')
    expect(frame).toHaveAttribute('sandbox', '')
    expect(frame.getAttribute('srcdoc')).toContain('Spring is here')
    expect(screen.getByText('Three new trips')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('says so when the layout is not the one that was sent', async () => {
    // ADR-183 point 4: a layout difference is reported, never hidden.
    stubFetch({
      'GET /delivery/executions/11/as-sent': () =>
        jsonResponse({ ...AS_SENT, templates_match: false, hash_matches: false }),
    })
    renderAsSent()

    const alerts = await screen.findAllByRole('alert')
    expect(alerts.map((a) => a.textContent).join(' ')).toMatch(/templates have changed/i)
    expect(alerts.map((a) => a.textContent).join(' ')).toMatch(/not byte-identical/i)
  })

  it('tells "nothing was sent" apart from a failure', async () => {
    // 409 is the server's answer for an execution with no delivery record.
    stubFetch({
      'GET /delivery/executions/11/as-sent': () => jsonResponse({ detail: 'no record' }, 409),
    })
    renderAsSent()

    expect(await screen.findByRole('status')).toHaveTextContent(/nothing to show/i)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})

describe('paging the deliveries list', () => {
  it('asks the server for the page in the URL and shows where it is', async () => {
    const fetchMock = stubFetch({
      'GET /delivery/send-instances': (request) => {
        const offset = Number(new URL(request.url).searchParams.get('offset') ?? 0)
        return jsonResponse(page([{ ...A_SEND, campaign_id: 1, campaign_name: 'Spring',
          variant_id: 2, variant_name: 'Main', execution_count: 3, event_count: 0 }],
        { total: 51, offset }))
      },
    })
    renderWithProviders(
      <Routes>
        <Route path="/deliveries" element={<Deliveries />} />
      </Routes>,
      { route: '/deliveries?offset=50' },
    )
    expect(await screen.findByText('51–51 of 51')).toBeInTheDocument()
    const asked = fetchMock.mock.calls
      .map(([input]) => new URL((input as Request).url))
      .find((u) => u.pathname === '/delivery/send-instances')!
    expect(asked.searchParams.get('offset')).toBe('50')
    expect(asked.searchParams.get('limit')).toBe('50')
  })
})

describe("finding someone in a send", () => {
  it('shows twenty and searches the server for the rest', async () => {
    /** Decided 2026-10-03: a sample and a search, not a paged list. */
    const fetchMock = stubFetch({
      'GET /delivery/send-instances/4': () =>
        jsonResponse({ ...A_SEND, execution_count: 300, exclusions_by_stage: {},
          audience_group_name: 'Big' }),
      'GET /delivery/send-instances/4/executions': (request) => {
        const q = new URL(request.url).searchParams.get('q')
        return q
          ? jsonResponse(page([execution(77, 'sent')], { total: 1, limit: 20 }))
          : jsonResponse(page([execution(11, 'sent'), execution(12, 'sent')], { total: 300, limit: 20 }))
      },
    })
    renderWithProviders(
      <Routes>
        <Route path="/deliveries/:id" element={<DeliveryDetail />} />
      </Routes>,
      { route: '/deliveries/4' },
    )
    expect(await screen.findByText(/Showing 2 of 300/)).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Pages' })).not.toBeInTheDocument()

    fireEvent.change(screen.getByLabelText(/Find a recipient/), { target: { value: ' anna@ ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))
    expect(await screen.findByText(/1 matching “anna@”/)).toBeInTheDocument()
    const asked = fetchMock.mock.calls
      .map(([input]) => new URL((input as Request).url))
      .filter((u) => u.pathname === '/delivery/send-instances/4/executions')
      .at(-1)!.searchParams
    expect([asked.get('q'), asked.get('limit')]).toEqual(['anna@', '20'])
  })
})

describe('a send stranded in sending (ADR-192, task-325)', () => {
  const STRANDED = {
    ...A_SEND,
    status: 'sending',
    stranded: true,
    last_activity_at: '2026-10-09T10:00:00Z',
    execution_count: 3,
    exclusions_by_stage: {},
    audience_group_name: null,
  }

  function render(handlers: Record<string, (request: Request) => Response>) {
    const fetchMock = stubFetch({
      'GET /delivery/send-instances/4/executions': () => jsonResponse(page([])),
      ...handlers,
    })
    renderWithProviders(
      <Routes>
        <Route path="/deliveries/:id" element={<DeliveryDetail />} />
      </Routes>,
      { route: '/deliveries/4' },
    )
    return fetchMock
  }

  it('is flagged, and a person can release it', async () => {
    let released = false
    const fetchMock = render({
      'GET /delivery/send-instances/4': () =>
        jsonResponse(released ? { ...STRANDED, status: 'failed', stranded: false } : STRANDED),
      'POST /delivery/send-instances/4/release': () => {
        released = true
        return jsonResponse({ ...STRANDED, status: 'failed', stranded: false })
      },
    })
    expect(await screen.findByRole('heading', { name: 'This send looks stranded' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Release this send' }))
    await waitFor(() =>
      expect(screen.queryByRole('heading', { name: 'This send looks stranded' })).not.toBeInTheDocument(),
    )
    expect(
      fetchMock.mock.calls.some(([input]) => {
        const request = typeof input === 'string' ? new Request(input) : (input as Request)
        return request.method === 'POST' && request.url.endsWith('/delivery/send-instances/4/release')
      }),
    ).toBe(true)
  })

  it('says why a release was refused', async () => {
    render({
      'GET /delivery/send-instances/4': () => jsonResponse(STRANDED),
      'POST /delivery/send-instances/4/release': () =>
        jsonResponse({ detail: 'SendInstance 4 is not stranded: it is sending' }, 409),
    })
    fireEvent.click(await screen.findByRole('button', { name: 'Release this send' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('not stranded')
  })

  it('offers nothing for a send that is not stranded', async () => {
    render({ 'GET /delivery/send-instances/4': () => jsonResponse({ ...STRANDED, stranded: false }) })
    expect(await screen.findByText(A_SEND.name)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Release this send' })).not.toBeInTheDocument()
  })
})

describe('the sends beside the open one (task-372)', () => {
  const OTHER = { ...A_SEND, id: 5, name: 'Autumn — send 1' }
  const detail = (send: typeof A_SEND) => () =>
    jsonResponse({ ...send, execution_count: 1, exclusions_by_stage: {}, audience_group_name: 'Everyone' })

  function openSplit(route: string) {
    const fetchMock = stubFetch({
      'GET /delivery/send-instances': () => jsonResponse(page([A_SEND, OTHER])),
      'GET /delivery/send-instances/4': detail(A_SEND),
      'GET /delivery/send-instances/5': detail(OTHER),
      'GET /delivery/send-instances/4/executions': () => jsonResponse(page([execution(11, 'sent')])),
      'GET /delivery/send-instances/5/executions': () => jsonResponse(page([])),
      'GET /delivery/executions/11/as-sent': () => jsonResponse(AS_SENT),
    })
    renderWithProviders(
      <Routes>
        <Route element={<DeliveriesSplit />}>
          <Route path="/deliveries" element={<NoSendOpen />} />
          <Route path="/deliveries/:id" element={<DeliveryDetail />} />
          <Route path="/deliveries/:id/executions/:executionId" element={<DeliveryAsSent />} />
        </Route>
      </Routes>,
      { route },
    )
    return fetchMock
  }
  const row = (name: RegExp) =>
    within(screen.getByRole('grid', { name: 'Sends' })).getByRole('row', { name })

  it("opens another send on the list's page, without the open send's recipient search", async () => {
    const fetchMock = openSplit('/deliveries/4?offset=50&q=ana')
    await screen.findByRole('heading', { name: 'Spring launch — send 1', level: 2 })
    fireEvent.click(await screen.findByText('Autumn — send 1'))
    await screen.findByRole('heading', { name: 'Autumn — send 1', level: 2 })
    expect(row(/Autumn/)).toHaveAttribute('aria-selected', 'true')
    const executions = fetchMock.mock.calls
      .map(([r]) => new URL((r as Request).url))
      .filter((u) => u.pathname === '/delivery/send-instances/5/executions')
    expect(executions.length).toBeGreaterThan(0)
    expect(executions.every((u) => !u.searchParams.get('q'))).toBe(true)
    const lists = fetchMock.mock.calls
      .map(([r]) => new URL((r as Request).url))
      .filter((u) => u.pathname === '/delivery/send-instances')
    expect(lists.every((u) => u.searchParams.get('offset') === '50')).toBe(true)
  })

  it("keeps the send marked while one recipient's message is open", async () => {
    openSplit('/deliveries/4/executions/11')
    expect(await screen.findByRole('heading', { name: 'As sent' })).toBeInTheDocument()
    await waitFor(() => expect(row(/Spring launch/)).toHaveAttribute('aria-selected', 'true'))
  })
})
