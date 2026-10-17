import { AlertTriangle } from 'lucide-react'
import { Button } from 'react-aria-components'
import { Link, useParams } from 'react-router'

import { useDelivery, useDeliveryExecutions, useReleaseDelivery, type DeliveryExecution } from '../api/resources'
import { HttpError } from '../api/session'
import DataTable, { type DataColumn } from '../components/DataTable'
import DetailSection from '../components/DetailSection'
import Fact from '../components/Fact'
import { SearchBox, useSearch } from '../components/RecipientSearch'
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
    // Column 3 of the deliveries (task-372, renders 29 and 30).
    <div className="detail">
      <div className="detail-scroll">
        <ScreenState query={delivery}>
          {delivery.data && (
            <>
              <div className="detail-head">
                <h2>{delivery.data.name}</h2>
              </div>
              {(delivery.data.status === 'draft' || delivery.data.status === 'scheduled') &&
                delivery.data.campaign_id != null &&
                delivery.data.variant_id != null && (
                  <p className="group group-body">
                    Not sent yet.{' '}
                    <Link
                      to={`/campaigns/${delivery.data.campaign_id}/variants/${delivery.data.variant_id}/send?send=${delivery.data.id}`}
                    >
                      Continue on the send screen
                    </Link>
                  </p>
                )}

              {delivery.data.stranded && (
                <section aria-labelledby="stranded-heading" className="detail-section">
                  <h3 id="stranded-heading" className="group-title">
                    This send looks stranded
                  </h3>
                  <div className="group card-rows group--attention">
                    <p className="notice">
                      <AlertTriangle size={16} strokeWidth={1.75} aria-hidden="true" className="notice-icon" />
                      <span>
                        It is still marked sending, but nothing has happened since{' '}
                        {formatDate(delivery.data.last_activity_at)}. The process sending it may have stopped.
                        Releasing it marks it failed so it can be retried: a retry skips everyone already sent
                        to, marks the person in flight as uncertain (never sent again), and sends the rest.
                      </span>
                    </p>
                    <div>
                      <Button onPress={() => release.mutate()} isDisabled={release.isPending}>
                        Release this send
                      </Button>
                    </div>
                    {release.isError && (
                      <p role="alert">
                        Not released:{' '}
                        {release.error instanceof HttpError ? release.error.detail : 'the request failed.'}
                      </p>
                    )}
                  </div>
                </section>
              )}

              <dl className="group fact-list">
                <Fact label="Status">{delivery.data.status}</Fact>
                <Fact label="Audience">{delivery.data.audience_group_name ?? '—'}</Fact>
                <Fact label="Provider">{delivery.data.provider ?? '—'}</Fact>
                <Fact label="From">{delivery.data.from_address ?? '—'}</Fact>
                <Fact label="Scheduled">{formatDate(delivery.data.scheduled_at)}</Fact>
                <Fact label="Recipients">{delivery.data.execution_count}</Fact>
                <Fact label="Sent">{delivery.data.sent_count}</Fact>
                <Fact label="Failed">{delivery.data.failed_count}</Fact>
                <Fact label="Excluded">{delivery.data.excluded_count}</Fact>
                {Object.entries(delivery.data.exclusions_by_stage).map(([stage, count]) => (
                  <Fact key={stage} label={`Excluded: ${stage}`}>
                    {count}
                  </Fact>
                ))}
              </dl>

              <DetailSection id="recipients-heading" title="Recipients" className="recipients-card">
                <SearchBox label="Find a recipient (identifier or address)" compact />
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
              </DetailSection>
            </>
          )}
        </ScreenState>
      </div>
    </div>
  )
}
