import { Link, useNavigate, useParams } from 'react-router'

import {
  useDecisionSlotStats,
  useSlotCandidates,
  type SlotResolution,
  type SlotTopContent,
} from '../api/resources'
import DataTable, { type DataColumn } from '../components/DataTable'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'

const topColumns: DataColumn<SlotTopContent & { id: number }>[] = [
  { key: 'title', header: 'Content', isRowHeader: true, render: (c) => c.title },
  { key: 'version', header: 'Version', render: (c) => c.version_number ?? '—' },
  { key: 'count', header: 'Picks', render: (c) => c.selection_count },
  { key: 'share', header: 'Share', render: (c) => `${c.share}%` },
]

const latestColumns: DataColumn<SlotResolution>[] = [
  { key: 'when', header: 'When', isRowHeader: true, render: (r) => formatDate(r.created_at) },
  {
    key: 'recipient',
    header: 'Recipient',
    // No recipient means the strategy picks once for everyone.
    render: (r) => (r.recipient_id == null ? 'Everyone' : `#${r.recipient_id}`),
  },
  { key: 'content', header: 'Content', render: (r) => r.content_title },
  { key: 'score', header: 'Score', render: (r) => r.score ?? '—' },
  { key: 'reason', header: 'Reason', render: (r) => r.reason ?? '—' },
]

/**
 * One decision slot (inventory B22): how it is set up, what it could pick
 * from, and what it has picked.
 *
 * **Read-only, and nothing here causes a pick.** The candidate count comes
 * from its own GET (task-205), not from executing the slot, which would write
 * a resolution and change the numbers this screen shows. Editing the slot
 * comes with the rest of the campaign write surface.
 */
export default function DecisionSlotDetail() {
  const id = Number(useParams().id)
  const stats = useDecisionSlotStats(id)
  const navigate = useNavigate()

  return (
    <>
      <p>
        <Link to="/decision-slots">← Decision slots</Link>
      </p>
      <ScreenState query={stats}>
        {stats.data && (
          <>
            <h1>{stats.data.slot.name}</h1>
            <dl className="facts">
              <dt>Campaign</dt>
              <dd>
                <Link to={`/campaigns/${stats.data.campaign_id}`}>{stats.data.campaign_name}</Link>
              </dd>
              <dt>Variant</dt>
              <dd>{stats.data.variant_name}</dd>
              <dt>Decision type</dt>
              <dd>{stats.data.slot.decision_type}</dd>
              <dt>Strategy</dt>
              <dd>{stats.data.slot.decision_strategy}</dd>
              <dt>Shows up to</dt>
              <dd>{stats.data.slot.max_results}</dd>
            </dl>

            <h2>What it chooses from</h2>
            <Candidates id={id} />
            {/*
              Both settings are open objects whose keys the strategy declares,
              so they are rendered generically, as ContentDetail renders a
              record's fields: a new strategy needs no change here.
            */}
            <Settings title="Candidate filter" values={stats.data.slot.candidate_filter} />
            <Settings title="Strategy settings" values={stats.data.slot.strategy_config} />

            <h2>What it has picked</h2>
            <dl className="facts">
              <dt>Picks made</dt>
              <dd>{stats.data.summary.resolution_count}</dd>
              <dt>Distinct recipients</dt>
              <dd>{stats.data.summary.unique_recipient_count}</dd>
              <dt>Distinct content</dt>
              <dd>{stats.data.summary.unique_content_count}</dd>
              <dt>Score (min / avg / max)</dt>
              <dd>
                {stats.data.summary.min_score} / {stats.data.summary.avg_score} /{' '}
                {stats.data.summary.max_score}
              </dd>
              <dt>Last pick</dt>
              <dd>{formatDate(stats.data.summary.last_resolution_at)}</dd>
            </dl>

            <h3>Top content</h3>
            <DataTable
              label="Top content"
              columns={topColumns}
              // DataTable keys rows by `id`. A row is one record at one
              // version, so `content_id` repeats; the rank does not.
              items={stats.data.top_content.map((c, rank) => ({ ...c, id: rank }))}
              emptyMessage="Nothing picked yet."
              onRowAction={(c) => navigate(`/content/${c.content_id}`)}
            />

            <h3>Reasons given</h3>
            {stats.data.reasons.length === 0 ? (
              <p>No reasons recorded yet.</p>
            ) : (
              <ul>
                {stats.data.reasons.map((r) => (
                  <li key={r.reason ?? ''}>
                    {r.reason ?? 'No reason given'} — {r.count}
                  </li>
                ))}
              </ul>
            )}

            <h3>Latest picks</h3>
            <DataTable
              label="Latest picks"
              columns={latestColumns}
              items={stats.data.latest}
              emptyMessage="Nothing picked yet."
            />
          </>
        )}
      </ScreenState>
    </>
  )
}

function Candidates({ id }: { id: number }) {
  const candidates = useSlotCandidates(id)
  return (
    <ScreenState query={candidates}>
      {candidates.data && (
        <p>
          {candidates.data.candidate_count} active content{' '}
          {candidates.data.candidate_count === 1 ? 'record' : 'records'}{' '}
          {candidates.data.category_ids.length === 0
            ? 'in any category'
            : `in categories ${candidates.data.category_ids.map((c) => `#${c}`).join(', ')}`}
          .
          {candidates.data.requires_recipient &&
            ' This strategy picks per recipient, so one person may be offered fewer.'}
        </p>
      )}
    </ScreenState>
  )
}

function Settings({ title, values }: { title: string; values?: Record<string, unknown> | null }) {
  const entries = Object.entries(values ?? {})
  return (
    <>
      <h3>{title}</h3>
      {entries.length === 0 ? (
        <p>None set.</p>
      ) : (
        <dl className="facts">
          {entries.map(([key, value]) => (
            <div key={key} style={{ display: 'contents' }}>
              <dt>{key}</dt>
              <dd>{typeof value === 'string' ? value : JSON.stringify(value)}</dd>
            </div>
          ))}
        </dl>
      )}
    </>
  )
}
