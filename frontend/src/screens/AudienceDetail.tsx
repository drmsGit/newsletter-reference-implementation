import { Link, useParams, useSearchParams } from 'react-router'

import { useAudienceGroup, useAudiencePreview, useSettings } from '../api/resources'
import Choice from '../components/Choice'
import DataTable from '../components/DataTable'
import RecipientSearch, { useSearch } from '../components/RecipientSearch'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'

export default function AudienceDetail() {
  const { id } = useParams()
  const group = useAudienceGroup(Number(id))

  return (
    <>
      <p>
        <Link to="/audiences">← Audiences</Link>
      </p>
      <ScreenState query={group}>
        {group.data && (
          <>
            <h1>{group.data.name}</h1>
            {group.data.description && <p>{group.data.description}</p>}

            <dl className="facts">
              <dt>Created</dt>
              <dd>{formatDate(group.data.created_at)}</dd>
              <dt>Updated</dt>
              <dd>{formatDate(group.data.updated_at)}</dd>
            </dl>

            <Reach groupId={group.data.id} />
          </>
        )}
      </ScreenState>
    </>
  )
}

type Arithmetic = NonNullable<ReturnType<typeof useAudiencePreview>['data']>['arithmetic']

/**
 * How the audience on one channel is arrived at (task-213; Manager Workflow
 * interview Q4.3): the working, not just the total, so a manager can see where
 * people went — a hand-add an exclusion overrode included (ADR-176 point 1).
 * The server's terms add up to the total; "not agreed" is a count only.
 */
function Working({ arithmetic: a, channel }: { arithmetic: Arithmetic; channel: string }) {
  const rows: [string, string, string?][] = [
    ['Match the rules', String(a.matched_rules)],
    [`Not agreed to ${channel}`, `−${a.not_agreed}`],
    ['Added by hand', `+${a.added_by_hand}`],
    ['Removed by exclusion segments', `−${a.removed_by_exclusion}`,
      a.removed_hand_added > 0 ? ` (${a.removed_hand_added} of them added by hand)` : undefined],
    [`Added by hand, not agreed to ${channel}`, `−${a.dropped_by_consent}`],
    ['In the audience', String(a.total)],
  ]
  return (
    <table className="working" aria-label={`How the audience on ${channel} is arrived at`}>
      <tbody>
        {rows.map(([label, value, note]) => (
          <tr key={label}>
            <th scope="row">
              {label}
              {note && <span className="muted">{note}</span>}
            </th>
            <td>{value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/**
 * Who a send to this group would reach, on one channel (2026-10-03).
 *
 * **There is no channel-less answer** (ADR-176 point 5): a group resolves to
 * different people per channel, so the channel is chosen first, from the
 * deployment's switched-on channels as the server lists them.
 *
 * The counts are the server's -- resolved, reachable, why the rest drop, by
 * stage. Below them, **a sample and a search, not a paged list**, decided with
 * the user: twenty reachable recipients, or the ones matching what the manager
 * typed (identifier or address), and how many match. Resolving and the search
 * both happen on the server, so a segment of thousands is searched whole.
 */
function Reach({ groupId }: { groupId: number }) {
  const [params, setParams] = useSearchParams()
  const settings = useSettings()
  const channels = (settings.data?.channels ?? []).filter((c) => c.available).map((c) => c.name)
  const channel = params.get('channel') ?? channels[0] ?? 'email'
  const q = useSearch()
  const preview = useAudiencePreview(groupId, channel, q)

  return (
    <section aria-labelledby="reach">
      <h2 id="reach">Who a send reaches</h2>
      {channels.length > 1 && (
        <Choice
          label="Channel"
          options={channels.map((c) => ({ id: c, name: c }))}
          selected={channel}
          onChange={(next) => {
            const updated = new URLSearchParams(params)
            updated.set('channel', next)
            setParams(updated)
          }}
        />
      )}
      <RecipientSearch />
      <ScreenState query={preview}>
        {preview.data && (
          <>
            <Working arithmetic={preview.data.arithmetic} channel={channel} />
            <p className="muted">As of now: a send works this out again when it goes out.</p>
            <dl className="facts">
              <dt>Reachable on {channel}</dt>
              <dd>{preview.data.reachable_count}</dd>
              {Object.entries(preview.data.dropped_by_stage).map(([stage, count]) => (
                <div key={stage} style={{ display: 'contents' }}>
                  <dt>Not reachable: {stage}</dt>
                  <dd>{count}</dd>
                </div>
              ))}
            </dl>
            <DataTable
              label={`Reachable on ${channel}`}
              columns={[
                { key: 'who', header: 'Recipient', isRowHeader: true, render: (r) => r.external_id },
                { key: 'address', header: 'Address', render: (r) => r.address ?? '—' },
                { key: 'language', header: 'Language', render: (r) => r.language ?? '—' },
              ]}
              items={preview.data.sample.map((r) => ({ ...r, id: r.recipient_id }))}
              emptyMessage={q ? 'Nobody reachable matches that.' : 'Nobody in this group is reachable on this channel.'}
            />
            <p className="muted" role="status">
              {q
                ? `${preview.data.sample_matching} matching “${q}”, showing ${preview.data.sample.length}.`
                : `Showing ${preview.data.sample.length} of ${preview.data.reachable_count}. Search to find someone.`}
            </p>
          </>
        )}
      </ScreenState>
    </section>
  )
}
