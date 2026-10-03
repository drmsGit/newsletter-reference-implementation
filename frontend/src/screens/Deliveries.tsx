import { useNavigate } from 'react-router'

import { useDeliveries, type SendInstanceListed } from '../api/resources'
import DataTable, { type DataColumn } from '../components/DataTable'
import Pager, { useOffset } from '../components/Pager'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'

const columns: DataColumn<SendInstanceListed>[] = [
  { key: 'name', header: 'Send', isRowHeader: true, render: (s) => s.name },
  {
    key: 'campaign',
    header: 'Campaign / variant',
    render: (s) => [s.campaign_name, s.variant_name].filter(Boolean).join(' / ') || '—',
  },
  { key: 'status', header: 'Status', render: (s) => s.status },
  {
    key: 'counts',
    header: 'Sent / failed / excluded',
    /**
     * The server's counts, as it gives them. They read 0 until a send has run,
     * and a draft showing "0 / 0 / 0" is the truth about a draft -- so nothing
     * here hides or recomputes them from the executions.
     */
    render: (s) => `${s.sent_count} / ${s.failed_count} / ${s.excluded_count}`,
  },
  { key: 'executions', header: 'Recipients', render: (s) => s.execution_count },
  {
    key: 'when',
    header: 'Scheduled / created',
    render: (s) => formatDate(s.scheduled_at ?? s.created_at),
  },
]

/**
 * The deliveries list: what has been sent, across campaigns (task-28, B23).
 *
 * **Read-only, deliberately.** Planning and firing a send are writes with their
 * own permissions (`sends.plan`, `sends.execute`) and land with the rest of the
 * write surface. Where campaigns stand, including ones that have sent nothing,
 * is a different question -- task-216's monitoring view, not this one.
 */
export default function Deliveries() {
  const deliveries = useDeliveries(useOffset())
  const navigate = useNavigate()

  return (
    <>
      <h1>Deliveries</h1>
      <ScreenState query={deliveries}>
        <DataTable
          label="Sends"
          columns={columns}
          items={deliveries.data?.items ?? []}
          emptyMessage="Nothing has been planned or sent in this brand yet."
          onRowAction={(s) => navigate(`/deliveries/${s.id}`)}
        />
        <Pager page={deliveries.data} />
      </ScreenState>
    </>
  )
}
