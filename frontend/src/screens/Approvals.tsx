import { Link, useNavigate, useSearchParams } from 'react-router'

import {
  useApprovalFilterOptions,
  useApprovals,
  type ApprovalQuery,
  type PendingActionRow,
} from '../api/resources'
import Choice from '../components/Choice'
import Pager, { PAGE_SIZE, useOffset } from '../components/Pager'
import DataTable, { type DataColumn } from '../components/DataTable'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'

/**
 * The requester as the server names them, with their kind beside it --
 * ADR-166 point 3's person/integration distinction is never dropped.
 */
function requester(a: PendingActionRow) {
  return a.requested_by_name ? `${a.requested_by_name} (${a.requested_by_type})` : a.requested_by_type
}

/**
 * A request's deadline. An action type may declare none (task-210; ADR-142
 * §4's addendum): it never expires, which the screen says rather than leaving
 * a blank that reads as unknown.
 */
export function deadline(iso: string | null | undefined): string {
  return iso ? formatDate(iso) : 'No deadline'
}

const waitingColumns: DataColumn<PendingActionRow>[] = [
  { key: 'label', header: 'Request', isRowHeader: true, render: (a) => a.label },
  { key: 'summary', header: 'Summary', render: (a) => a.summary },
  { key: 'requested_by', header: 'Requested by', render: requester },
  { key: 'expires', header: 'Expires', render: (a) => deadline(a.expires_at) },
]

const historyColumns: DataColumn<PendingActionRow>[] = [
  { key: 'label', header: 'Request', isRowHeader: true, render: (a) => a.label },
  { key: 'summary', header: 'Summary', render: (a) => a.summary },
  { key: 'outcome', header: 'Outcome', render: (a) => a.status },
  { key: 'requested_by', header: 'Requested by', render: requester },
  {
    key: 'decided_by',
    header: 'Decided by',
    // An expired request was decided by nobody, and says so.
    render: (a) => a.decided_by_name ?? (a.status === 'expired' ? 'nobody (expired)' : '—'),
  },
  {
    key: 'ended',
    header: 'Ended',
    // The server orders the history by this: decided, or the deadline it lapsed at.
    render: (a) => formatDate(a.decided_at ?? a.expires_at),
  },
  { key: 'reason', header: 'Reason', render: (a) => a.decision_reason ?? '—' },
]

const ANY = '__any__'

/**
 * The approval inbox, and the decision history.
 *
 * **Two screens, one list** (Manager Workflow Q1.6: log and queue stay
 * separate). The inbox answers *does anything need me* and holds only what is
 * waiting; a decided request leaves it and appears in the history, which reads
 * by when each request ended. They share everything else -- the filters, the
 * paging, the table -- so they are one component in two modes rather than two
 * copies that drift.
 *
 * ADR-169 put the inbox close to the manager's home screen, and ADR-168's
 * addendum is what makes it reachable at all -- approving requires a
 * session-authenticated person.
 *
 * **One flat list, newest first, narrowed by the manager** (Q1.3): the system
 * does not decide which requests matter enough to separate. The filters offer
 * only what this brand's requests carry -- the server's `filter-options` -- so
 * a requester is chosen by name ("what did Acme Agency send").
 *
 * **The filters live in the URL**, so a narrowed list survives a reload, the
 * back button undoes a filter, and a link to it can be shared.
 *
 * Deciding happens on a request's own screen (`ApprovalDetail`), where what it
 * would do is shown in full first.
 */
export default function Approvals({ mode = 'waiting' }: { mode?: 'waiting' | 'history' }) {
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const options = useApprovalFilterOptions()
  const history = mode === 'history'

  const action = params.get('action') ?? ANY
  const requesterKey = params.get('requester') ?? ANY // "type:id", or "type:" for no id
  const offset = useOffset()

  const [byType, byId] = requesterKey === ANY ? [undefined, undefined] : requesterKey.split(':')
  const query: ApprovalQuery = {
    status: history ? 'decided' : 'pending',
    action_key: action === ANY ? undefined : action,
    requested_by_type: byType,
    requested_by_id: byId ? Number(byId) : undefined,
    limit: PAGE_SIZE,
    offset,
  }
  const approvals = useApprovals(query)

  /** Change one filter. Any change starts again from the first page. */
  function set(name: string, value: string) {
    const next = new URLSearchParams(params)
    if (value === ANY) next.delete(name)
    else next.set(name, value)
    next.delete('offset')
    setParams(next)
  }

  const rows = approvals.data?.items ?? []
  const filtered = action !== ANY || requesterKey !== ANY || offset > 0

  return (
    <>
      <h1>{history ? 'Decision history' : 'Approvals'}</h1>
      <p>
        {history ? (
          <Link to="/approvals">← Waiting for a decision</Link>
        ) : (
          <Link to="/approvals/history">Decision history →</Link>
        )}
      </p>
      <div className="filters">
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
          selected={requesterKey}
          onChange={(v) => set('requester', v)}
        />
      </div>
      <ScreenState query={approvals}>
        <DataTable
          label={history ? 'Decided requests' : 'Waiting for a decision'}
          columns={history ? historyColumns : waitingColumns}
          items={rows}
          emptyMessage={
            filtered
              ? 'No request matches these filters.'
              : history
                ? 'Nothing has been decided yet.'
                : 'Nothing is waiting for a decision.'
          }
          onRowAction={(a) => navigate(`/approvals/${a.id}`)}
        />
        {/* The server's total (ADR-185): Older is disabled exactly on the last page. */}
        <Pager page={approvals.data} />
      </ScreenState>
    </>
  )
}
