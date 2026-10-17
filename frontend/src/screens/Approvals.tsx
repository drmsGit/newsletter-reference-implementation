import { AlertTriangle, History } from 'lucide-react'
import { GridList, GridListItem } from 'react-aria-components'
import { Link, Outlet, useLocation, useMatch, useNavigate, useSearchParams } from 'react-router'

import {
  useApprovalFilterOptions,
  useApprovals,
  type ApprovalQuery,
  type PendingActionRow,
} from '../api/resources'
import BackTo from '../components/BackTo'
import Choice from '../components/Choice'
import Pager, { PAGE_SIZE, useOffset } from '../components/Pager'
import DataTable, { type DataColumn } from '../components/DataTable'
import ScreenState from '../components/ScreenState'
import StatusChip from '../components/StatusChip'
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

/** Where a request's subject lives in this app, when it has a page. */
function subjectLink(a: PendingActionRow): string | null {
  return a.subject_type === 'send_instance' && a.subject_id != null ? `/deliveries/${a.subject_id}` : null
}

const historyColumns: DataColumn<PendingActionRow>[] = [
  { key: 'label', header: 'Request', isRowHeader: true, render: (a) => <Link to={`/approvals/${a.id}`}>{a.label}</Link> },
  { key: 'summary', header: 'Summary', render: (a) => a.summary },
  {
    key: 'outcome',
    header: 'Outcome',
    // What an approved action ended in, as it stands now (task-338), linked to
    // what it acted on. Nobody is notified: following up is the deliveries
    // screen's job, not the approver's.
    render: (a) => (
      <span className="chips">
        <StatusChip status={a.status} />
        {a.outcome && (
          <>
            <span className="sr-only"> — </span>
            {subjectLink(a) ? <Link to={subjectLink(a)!}>{a.outcome}</Link> : a.outcome}
          </>
        )}
      </span>
    ),
  },
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

  const filters = (
    <div className="filters">
      <Choice
        label="Action"
        pulldown
        options={[
          { id: ANY, name: history ? 'Any action' : 'All' },
          ...(options.data?.actions ?? []).map((a) => ({ id: a.key, name: a.label })),
        ]}
        selected={action}
        onChange={(v) => set('action', v)}
      />
      <Choice
        label="Requested by"
        pulldown
        options={[
          { id: ANY, name: history ? 'Anyone' : 'All' },
          ...(options.data?.requesters ?? []).map((r) => ({
            id: `${r.type}:${r.id ?? ''}`,
            name: `${r.name} (${r.type})`,
          })),
        ]}
        selected={requesterKey}
        onChange={(v) => set('requester', v)}
      />
    </div>
  )

  if (!history) return <WaitingList query={approvals} rows={rows} filtered={filtered} filters={filters} />

  return (
    // One wide table, no details column (task-372, decision 14, 2026-10-17).
    <div className="wide-page">
      <div className="list-head">
        <BackTo to="/approvals" label="Waiting for a decision" />
        <h1>Decision history</h1>
      </div>
      {filters}
      <div className="wide-body">
        <ScreenState query={approvals}>
          <DataTable
            label="Decided requests"
            columns={historyColumns}
            items={rows}
            emptyMessage={filtered ? 'No request matches these filters.' : 'Nothing has been decided yet.'}
            onRowAction={(a) => navigate(`/approvals/${a.id}`)}
          />
        </ScreenState>
      </div>
      <div className="list-foot list-foot--end">
        {/* The server's total (ADR-185): Older is disabled exactly on the last page. */}
        <Pager page={approvals.data} />
      </div>
    </div>
  )
}

/**
 * Column 2 of the inbox (task-372; docs/design/HANDOFF.md section 6): the title
 * and its count, the filters, the requests as rows, and at the foot the
 * decision history and the pager. **No actions in the list**: deciding happens
 * in the details. Opening a request keeps the list's filters and page in the
 * address, so the list beside it does not silently widen.
 *
 * The open request is the list's single selection (HANDOFF section 7's first
 * option): React Aria then marks its row aria-selected for assistive
 * technology, which a class alone did not.
 */
function WaitingList({
  query,
  rows,
  filtered,
  filters,
}: {
  query: ReturnType<typeof useApprovals>
  rows: PendingActionRow[]
  filtered: boolean
  filters: React.ReactNode
}) {
  const navigate = useNavigate()
  const location = useLocation()
  const open = useMatch('/approvals/:id')?.params.id
  const total = query.data?.total ?? 0

  return (
    <>
      <div className="list-head">
        <h1>Approvals</h1>
        {query.data && (
          <p className="list-count">
            {filtered ? `${total} match these filters` : `${total} waiting for a decision`}
          </p>
        )}
      </div>
      {filters}
      <ScreenState query={query}>
        <GridList
          aria-label="Waiting for a decision"
          className="react-aria-GridList item-list"
          items={rows}
          selectionMode="single"
          selectionBehavior="replace"
          selectedKeys={open !== undefined ? [Number(open)] : []}
          onSelectionChange={(keys) => {
            const [key] = keys === 'all' ? [] : [...keys]
            if (key !== undefined && String(key) !== open)
              navigate({ pathname: `/approvals/${key}`, search: location.search })
          }}
          renderEmptyState={() => (
            <p className="list-empty muted">
              {filtered ? 'No request matches these filters.' : 'Nothing is waiting for a decision.'}
            </p>
          )}
        >
          {(a) => (
            <GridListItem id={a.id} textValue={a.label} className="react-aria-GridListItem item">
              <span className="item-title">{a.label}</span>
              <span className="item-summary">{a.summary}</span>
              <span className="item-meta">
                {/* The requester with their kind (ADR-166 point 3), in an element of its own. */}
                <span>{requester(a)}</span>
                <span>{deadline(a.expires_at)}</span>
              </span>
              {a.requester_allowed === false && (
                // Said before anyone decides (task-331): approving such a request
                // withdraws it and nothing runs.
                <span className="item-flag">
                  <AlertTriangle size={13} strokeWidth={2} aria-hidden="true" />
                  no longer allowed; approving withdraws it
                </span>
              )}
            </GridListItem>
          )}
        </GridList>
      </ScreenState>
      <div className="list-foot">
        <Link to="/approvals/history" className="list-foot__link">
          <History size={14} strokeWidth={1.75} aria-hidden="true" />
          Decision history
        </Link>
        {/* The server's total (ADR-185): Older is disabled exactly on the last page. */}
        <Pager page={query.data} />
      </div>
    </>
  )
}

/**
 * The inbox as a split (task-372): the list in column 2, the open request in
 * column 3, the address saying which (`/approvals/:id`, so links, reload and
 * the back button work as before). The inbox is the home screen (ADR-169).
 */
export function ApprovalsSplit() {
  return (
    <div className="split">
      <section className="col-list" aria-label="Requests">
        <Approvals />
      </section>
      <section className="col-detail">
        <Outlet />
      </section>
    </div>
  )
}

/** The details column before a request is chosen. */
export function NoRequestOpen() {
  return <p className="detail-placeholder muted">Select a request to review it.</p>
}
