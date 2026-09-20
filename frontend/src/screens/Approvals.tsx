import { useNavigate } from 'react-router'

import { useApprovals, type PendingActionRow } from '../api/resources'
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

/**
 * The approval inbox.
 *
 * ADR-169 put this close to the manager's home screen, and ADR-168's addendum
 * is what makes it reachable at all -- approving requires a session-authenticated
 * person, and until that record the JSON plane had no way to carry one.
 *
 * **Read-only for now.** Approve and reject are writes and land with the rest
 * of the write surface; showing the buttons before they work would be worse
 * than not showing them.
 */
export default function Approvals() {
  const approvals = useApprovals()
  const navigate = useNavigate()

  return (
    <>
      <h1>Approvals</h1>
      <ScreenState query={approvals}>
        <DataTable
          label="Pending approvals"
          columns={columns}
          items={approvals.data ?? []}
          emptyMessage="Nothing is waiting for a decision."
          onRowAction={(a) => navigate(`/approvals/${a.id}`)}
        />
      </ScreenState>
    </>
  )
}
