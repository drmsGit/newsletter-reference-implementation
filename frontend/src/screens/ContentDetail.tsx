import { Link, useParams } from 'react-router'

import { useCampaignsUsing, useContentRecord } from '../api/resources'
import ScreenState from '../components/ScreenState'
import { STAGE_LABEL } from './Monitoring'

export default function ContentDetail() {
  const { id } = useParams()
  const record = useContentRecord(Number(id))

  return (
    <>
      <p>
        <Link to="/content">← Content</Link>
      </p>
      <ScreenState query={record}>
        {record.data && (
          <>
            <h1>{record.data.title}</h1>
            {record.data.description && <p>{record.data.description}</p>}

            <dl className="facts">
              <dt>Status</dt>
              <dd>{record.data.status ?? '—'}</dd>
            </dl>

            <h2>Fields</h2>
            {/*
              **`content` is an open object and is rendered generically.**

              The API types it as a dictionary, not a fixed shape, because what
              a content record carries depends on its type -- and ADR-165 made
              the core channel-neutral, so a client that hard-coded "headline"
              and "body_medium" would be an email-shaped client again. Whatever
              the server sends is what is shown.
            */}
            <dl className="facts">
              {Object.entries(record.data.content ?? {}).map(([field, value]) => (
                <div key={field} style={{ display: 'contents' }}>
                  <dt>{field}</dt>
                  <dd>{typeof value === 'string' ? value : JSON.stringify(value)}</dd>
                </div>
              ))}
            </dl>

            <UsedIn recordId={record.data.id} />
          </>
        )}
      </ScreenState>
    </>
  )
}

/**
 * Where the record is used (task-267): every campaign with a module bound to
 * it, each variant that uses it linked to its editor and marked with its
 * stage, so a sent one reads as sent. Bound modules only, as the composer's
 * reach count counts them — a slot picks at send time, so it is not "using"
 * the record until then.
 */
function UsedIn({ recordId }: { recordId: number }) {
  const used = useCampaignsUsing(recordId)
  return (
    <section aria-labelledby="used-in-heading">
      <h2 id="used-in-heading">Used in</h2>
      <ScreenState query={used}>
        {used.data && used.data.items.length === 0 ? (
          <p className="muted">No campaign has a module bound to this record.</p>
        ) : (
          <ul className="used-in">
            {used.data?.items.map((campaign) => (
              <li key={campaign.id}>
                <Link to={`/campaigns/${campaign.id}`}>{campaign.name}</Link>:{' '}
                {campaign.variants.map((variant, index) => (
                  <span key={variant.id}>
                    {index > 0 && ', '}
                    <Link to={`/campaigns/${campaign.id}/variants/${variant.id}`}>{variant.name}</Link>{' '}
                    <span className={variant.stage === 'sent' ? 'used-in__sent' : 'muted'}>
                      ({variant.channel}, {STAGE_LABEL[variant.stage] ?? variant.stage})
                    </span>
                  </span>
                ))}
              </li>
            ))}
          </ul>
        )}
        {used.data && used.data.total > used.data.items.length && (
          <p className="muted">
            Showing {used.data.items.length} of {used.data.total} campaigns.
          </p>
        )}
        <p className="muted">A decision slot that may pick this record when it sends is not listed.</p>
      </ScreenState>
    </section>
  )
}
