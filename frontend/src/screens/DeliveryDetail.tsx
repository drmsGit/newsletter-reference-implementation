import { Link, useParams } from 'react-router'

import { useDelivery, useDeliveryExecutions, type DeliveryExecution } from '../api/resources'
import DataTable, { type DataColumn } from '../components/DataTable'
import Pager, { useOffset } from '../components/Pager'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'

function executionColumns(sendId: number): DataColumn<DeliveryExecution>[] {
  return [
    {
      key: 'recipient',
      header: 'Recipient',
      isRowHeader: true,
      render: (e) => e.recipient_external_id ?? `#${e.recipient_id}`,
    },
    { key: 'status', header: 'Status', render: (e) => e.status },
    { key: 'reason', header: 'Not sent because', render: (e) => e.exclusion_reason ?? '—' },
    { key: 'sent_at', header: 'Sent', render: (e) => formatDate(e.sent_at) },
    {
      key: 'as_sent',
      header: 'What they got',
      /**
       * **A link only where there is something to show.**
       *
       * ADR-183 reconstructs a message from its delivery record, and only a sent
       * execution has one; the server answers 409 for the rest. A link on every
       * row would invite a click that can only end in "nothing to show", so an
       * excluded or failed row says so here instead.
       */
      render: (e) =>
        e.status === 'sent' ? (
          <Link to={`/deliveries/${sendId}/executions/${e.id}`}>As sent</Link>
        ) : (
          '—'
        ),
    },
  ]
}

/**
 * One send, and what explains the gap between what it planned and what it sent
 * -- the Manager Workflow interview's question 5.5.
 *
 * Every send re-resolves its audience before it fires (ADR-176 point 4), so
 * exclusions are routine rather than an edge case. The counts by stage are the
 * server's; this screen does not recount them from the executions, which would
 * be a second answer free to disagree with the first.
 */
export default function DeliveryDetail() {
  const id = Number(useParams().id)
  const delivery = useDelivery(id)
  const executions = useDeliveryExecutions(id, useOffset())

  return (
    <>
      <p>
        <Link to="/deliveries">← Deliveries</Link>
      </p>
      <ScreenState query={delivery}>
        {delivery.data && (
          <>
            <h1>{delivery.data.name}</h1>
            <dl className="facts">
              <dt>Status</dt>
              <dd>{delivery.data.status}</dd>
              <dt>Audience</dt>
              <dd>{delivery.data.audience_group_name ?? '—'}</dd>
              <dt>Provider</dt>
              <dd>{delivery.data.provider ?? '—'}</dd>
              <dt>From</dt>
              <dd>{delivery.data.from_address ?? '—'}</dd>
              <dt>Scheduled</dt>
              <dd>{formatDate(delivery.data.scheduled_at)}</dd>
              <dt>Recipients</dt>
              <dd>{delivery.data.execution_count}</dd>
              <dt>Sent</dt>
              <dd>{delivery.data.sent_count}</dd>
              <dt>Failed</dt>
              <dd>{delivery.data.failed_count}</dd>
              <dt>Excluded</dt>
              <dd>{delivery.data.excluded_count}</dd>
              {Object.entries(delivery.data.exclusions_by_stage).map(([stage, count]) => (
                <div key={stage} style={{ display: 'contents' }}>
                  <dt>Excluded: {stage}</dt>
                  <dd>{count}</dd>
                </div>
              ))}
            </dl>

            <h2>Recipients</h2>
            <ScreenState query={executions}>
              <DataTable
                label="Recipients of this send"
                columns={executionColumns(id)}
                items={executions.data?.items ?? []}
                emptyMessage="This send has no recipients."
              />
              <Pager page={executions.data} />
            </ScreenState>
          </>
        )}
      </ScreenState>
    </>
  )
}
