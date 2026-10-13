import { Button } from 'react-aria-components'
import { Link, useParams } from 'react-router'

import { useDelivery, useDeliveryExecutions, useReleaseDelivery, type DeliveryExecution } from '../api/resources'
import { HttpError } from '../api/session'
import DataTable, { type DataColumn } from '../components/DataTable'
import RecipientSearch, { useSearch } from '../components/RecipientSearch'
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
  const q = useSearch()
  const executions = useDeliveryExecutions(id, q)
  const release = useReleaseDelivery(id)

  return (
    <>
      <p>
        <Link to="/deliveries">← Deliveries</Link>
      </p>
      <ScreenState query={delivery}>
        {delivery.data && (
          <>
            <h1>{delivery.data.name}</h1>
            {(delivery.data.status === 'draft' || delivery.data.status === 'scheduled') &&
              delivery.data.campaign_id != null &&
              delivery.data.variant_id != null && (
                <p>
                  Not sent yet.{' '}
                  <Link
                    to={`/campaigns/${delivery.data.campaign_id}/variants/${delivery.data.variant_id}/send?send=${delivery.data.id}`}
                  >
                    Continue on the send screen
                  </Link>
                </p>
              )}
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

            {delivery.data.stranded && (
              <section aria-labelledby="stranded-heading">
                <h2 id="stranded-heading">This send looks stranded</h2>
                <p>
                  It is still marked sending, but nothing has happened since{' '}
                  {formatDate(delivery.data.last_activity_at)}. The process sending it may have stopped.
                  Releasing it marks it failed so it can be retried: a retry skips everyone already sent
                  to, marks the person in flight as uncertain (never sent again), and sends the rest.
                </p>
                <Button onPress={() => release.mutate()} isDisabled={release.isPending}>
                  Release this send
                </Button>
                {release.isError && (
                  <p role="alert">
                    Not released:{' '}
                    {release.error instanceof HttpError ? release.error.detail : 'the request failed.'}
                  </p>
                )}
              </section>
            )}

            <h2>Recipients</h2>
            <RecipientSearch />
            <ScreenState query={executions}>
              <DataTable
                label="Recipients of this send"
                columns={executionColumns(id)}
                items={executions.data?.items ?? []}
                emptyMessage="This send has no recipients."
              />
              {executions.data && (
                <p className="muted" role="status">
                  {q
                    ? `${executions.data.total} matching “${q}”, showing ${executions.data.items.length}.`
                    : `Showing ${executions.data.items.length} of ${executions.data.total}. Search to find someone.`}
                </p>
              )}
            </ScreenState>
          </>
        )}
      </ScreenState>
    </>
  )
}
