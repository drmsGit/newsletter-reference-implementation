import { Button } from 'react-aria-components'
import { useNavigate, useSearchParams } from 'react-router'

import {
  useApprovalFilterOptions,
  useApprovals,
  type ApprovalQuery,
  type PendingActionRow,
} from '../api/resources'
import Choice from '../components/Choice'
import DataTable, { type DataColumn } from '../components/DataTable'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'

const columns: DataColumn<PendingActionRow>[] = [
  { key: 'label', header: 'Request', isRowHeader: true, render: (a) => a.label },
  { key: 'summary', header: 'Summary', render: (a) => a.summary },
  { key: 'status', header: 'Status', render: (a) => a.status },
  {
    key: 'requested_by',
    header: 'Requested by',
    /**
     * The actor type comes from the server and is shown as the server says it.
     *
     * ADR-166 point 3 made the distinction between a person and an integration
     * durable, and an inbox that silently rendered both as "someone" would
     * discard the one fact that explains why a request exists.
     */
    render: (a) => a.requested_by_type,
  },
  { key: 'expires', header: 'Expires', render: (a) => formatDate(a.expires_at) },
]

/** Rows per page. The server allows up to 200; 50 is its default too. */
const PAGE = 50
const ANY = '__any__'

/**
 * The approval inbox.
 *
 * ADR-169 put this close to the manager's home screen, and ADR-168's addendum
 * is what makes it reachable at all -- approving requires a session-authenticated
 * person, and until that record the JSON plane had no way to carry one.
 *
 * **One flat list, newest first, narrowed by the manager** (Manager Workflow
 * Q1.3): the system does not decide which requests matter enough to separate.
 * The filters offer only what this brand's requests carry -- the server's
 * `filter-options` -- so a requester is chosen by name ("what did Acme Agency
 * send"), and nothing is offered that would match no row.
 *
 * **The filters live in the URL**, so a narrowed inbox survives a reload, the
 * back button undoes a filter, and a link to it can be shared.

 *
 * Deciding happens on a request's own screen (`ApprovalDetail`), where what it
 * would do is shown in full first.
 */
export default function Approvals() {
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const options = useApprovalFilterOptions()

  const status = (params.get('status') ?? 'pending') as NonNullable<ApprovalQuery['status']>
  const action = params.get('action') ?? ANY
  const requester = params.get('requester') ?? ANY // "type:id", or "type:" for no id
  const offset = Math.max(0, Number(params.get('offset') ?? 0) || 0)

  const [byType, byId] = requester === ANY ? [undefined, undefined] : requester.split(':')
  const query: ApprovalQuery = {
    status,
    action_key: action === ANY ? undefined : action,
    requested_by_type: byType,
    requested_by_id: byId ? Number(byId) : undefined,
    limit: PAGE,
    offset,
  }
  const approvals = useApprovals(query)

  /** Change one filter. Any change starts again from the first page. */
  function set(name: string, value: string) {
    const next = new URLSearchParams(params)
    if (value === ANY || (name === 'status' && value === 'pending')) next.delete(name)
    else next.set(name, value)
    next.delete('offset')
    setParams(next)
  }

  function page(to: number) {
    const next = new URLSearchParams(params)
    if (to > 0) next.set('offset', String(to))
    else next.delete('offset')
    setParams(next)
  }

  const names = new Map(
    (options.data?.requesters ?? []).map((r) => [`${r.type}:${r.id ?? ''}`, r.name]),
  )
  const rows = approvals.data ?? []
  const named = columns.map((c) =>
    c.key === 'requested_by'
      ? {
          ...c,
          // The requester's name where the server gave one, else its kind --
          // ADR-166 point 3's person/integration distinction is never dropped.
          render: (a: PendingActionRow) => {
            const name = names.get(`${a.requested_by_type}:${a.requested_by_id ?? ''}`)
            return name ? `${name} (${a.requested_by_type})` : a.requested_by_type
          },
        }
      : c,
  )

  return (
    <>
      <h1>Approvals</h1>
      <div className="filters">
        <Choice
          label="Status"
          options={[
            { id: 'pending', name: 'Waiting for a decision' },
            { id: 'decided', name: 'Decided' },
            { id: 'all', name: 'All' },
          ]}
          selected={status}
          onChange={(v) => set('status', v)}
        />
        <Choice
          label="Action"
          options={[
            { id: ANY, name: 'Any action' },
            ...(options.data?.actions ?? []).map((a) => ({ id: a.key, name: a.label })),
          ]}
          selected={action}
          onChange={(v) => set('action', v)}
        />
        <Choice
          label="Requested by"
          options={[
            { id: ANY, name: 'Anyone' },
            ...(options.data?.requesters ?? []).map((r) => ({
              id: `${r.type}:${r.id ?? ''}`,
              name: `${r.name} (${r.type})`,
            })),
          ]}
          selected={requester}
          onChange={(v) => set('requester', v)}
        />
      </div>
      <ScreenState query={approvals}>
        <DataTable
          label="Approvals"
          columns={named}
          items={rows}
          emptyMessage={
            status === 'pending' && action === ANY && requester === ANY && offset === 0
              ? 'Nothing is waiting for a decision.'
              : 'No request matches these filters.'
          }
          onRowAction={(a) => navigate(`/approvals/${a.id}`)}
        />
        {/*
          No total yet (task-88 brings one), so "next" is offered when this page
          came back full. The cost is honest and small: when the last page is
          exactly full, "next" leads to an empty page that says so.
        */}
        {(offset > 0 || rows.length === PAGE) && (
          <nav aria-label="Pages" className="pager">
            <Button isDisabled={offset === 0} onPress={() => page(Math.max(0, offset - PAGE))}>
              Newer
            </Button>
            <span className="muted">
              {rows.length > 0 ? `${offset + 1}–${offset + rows.length}` : 'No more'}
            </span>
            <Button isDisabled={rows.length < PAGE} onPress={() => page(offset + PAGE)}>
              Older
            </Button>
          </nav>
        )}
      </ScreenState>
    </>
  )
}
