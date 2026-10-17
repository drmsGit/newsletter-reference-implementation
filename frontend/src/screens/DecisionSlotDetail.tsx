import { Link, useNavigate, useParams } from 'react-router'

import {
  useDecisionSlotStats,
  useSlotCandidates,
  type SlotResolution,
  type SlotTopContent,
} from '../api/resources'
import DataTable, { type DataColumn } from '../components/DataTable'
import DetailSection from '../components/DetailSection'
import Fact from '../components/Fact'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'

const topColumns: DataColumn<SlotTopContent & { id: number }>[] = [
  { key: 'title', header: 'Content', isRowHeader: true, render: (c) => c.title },
  { key: 'version', header: 'Version', render: (c) => c.version_number ?? '—' },
  { key: 'count', header: 'Picks', numeric: true, render: (c) => c.selection_count },
  { key: 'share', header: 'Share', numeric: true, render: (c) => `${c.share}%` },
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
  { key: 'score', header: 'Score', numeric: true, render: (r) => r.score ?? '—' },
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
    // Column 3 of the slots (task-372, render 32); the list sits beside it.
    <div className="detail">
      <div className="detail-scroll">
        <ScreenState query={stats}>
          {stats.data && (
            <>
              <div className="detail-head">
                <h2>{stats.data.slot.name}</h2>
              </div>
              <dl className="group fact-list">
                <Fact label="Campaign">
                  <Link to={`/campaigns/${stats.data.campaign_id}`}>{stats.data.campaign_name}</Link>
                </Fact>
                <Fact label="Variant">{stats.data.variant_name}</Fact>
                <Fact label="Decision type">{stats.data.slot.decision_type}</Fact>
                <Fact label="Strategy">{stats.data.slot.decision_strategy}</Fact>
                <Fact label="Shows up to">{stats.data.slot.max_results}</Fact>
              </dl>

              <DetailSection id="slot-chooses" title="What it chooses from">
                <Candidates id={id} />
                {/*
                  Both settings are open objects whose keys the strategy declares,
                  so they are rendered generically, as ContentDetail renders a
                  record's fields: a new strategy needs no change here.
                */}
                <Settings title="Candidate filter" values={stats.data.slot.candidate_filter} />
                <Settings title="Strategy settings" values={stats.data.slot.strategy_config} />
              </DetailSection>

              <DetailSection id="slot-picked" title="What it has picked">
                <dl className="fact-list">
                  <Fact label="Picks made">{stats.data.summary.resolution_count}</Fact>
                  <Fact label="Distinct recipients">{stats.data.summary.unique_recipient_count}</Fact>
                  <Fact label="Distinct content">{stats.data.summary.unique_content_count}</Fact>
                  <Fact label="Score (min / avg / max)">
                    {stats.data.summary.min_score} / {stats.data.summary.avg_score} / {stats.data.summary.max_score}
                  </Fact>
                  <Fact label="Last pick">{formatDate(stats.data.summary.last_resolution_at)}</Fact>
                </dl>
              </DetailSection>

              <div className="group table-card">
                <h4 className="table-card__title">Top content</h4>
                <DataTable
                  label="Top content"
                  columns={topColumns}
                  // DataTable keys rows by `id`. A row is one record at one
                  // version, so `content_id` repeats; the rank does not.
                  items={stats.data.top_content.map((c, rank) => ({ ...c, id: rank }))}
                  emptyMessage="Nothing picked yet."
                  onRowAction={(c) => navigate(`/content/${c.content_id}`)}
                />
              </div>

              <div className="group card-rows">
                <h4 className="row-title">Reasons given</h4>
                {stats.data.reasons.length === 0 ? (
                  <p>No reasons recorded yet.</p>
                ) : (
                  stats.data.reasons.map((r) => (
                    <p key={r.reason ?? ''}>
                      {r.reason ?? 'No reason given'} — {r.count}
                    </p>
                  ))
                )}
              </div>

              <div className="group table-card">
                <h4 className="table-card__title">Latest picks</h4>
                <DataTable
                  label="Latest picks"
                  columns={latestColumns}
                  items={stats.data.latest}
                  emptyMessage="Nothing picked yet."
                />
              </div>
            </>
          )}
        </ScreenState>
      </div>
    </div>
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
    <div>
      <h4 className="row-title">{title}</h4>
      {entries.length === 0 ? (
        <p className="muted">None set.</p>
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
    </div>
  )
}
