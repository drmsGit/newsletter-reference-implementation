import { ChevronDown } from 'lucide-react'

import { useCampaignResults, type VariantResults } from '../api/resources'
import DataTable, { type DataColumn } from './DataTable'

/**
 * How the campaign went — the one KPI view (task-58, ADR-196).
 *
 * One row per variant that has sent, and the whole campaign on top: its
 * totals, with the click rate pooled over every variant (unique clickers over
 * sent), so email and push compare like for like. The server counts all of
 * it; this section only shows it. Nothing appears until a send has gone out,
 * and it folds away, since the campaign page is also where the campaign is
 * built. Comparing campaigns is the analytics tool's job, not this page's.
 *
 * Twelve figures do not fit one table beside a list, so they are two
 * (task-372, decision 15): what reached people, then what they did with it.
 */
export default function CampaignResults({ campaignId }: { campaignId: number }) {
  const results = useCampaignResults(campaignId)
  if (results.isError) return <p role="alert">The results could not be loaded.</p>
  const data = results.data
  if (!data || !data.campaign || data.variants.length === 0) return null

  const whole: Row = { ...data.campaign, id: 0, name: 'Whole campaign', channel: '' }
  const rows: Row[] = [whole, ...data.variants]
  const since = new Date(data.unsubscribes_counted_since).toLocaleDateString(undefined, { dateStyle: 'medium' })

  return (
    <details open className="results">
      <summary>
        <ChevronDown size={16} strokeWidth={1.75} aria-hidden="true" className="results-chevron" />
        <h3>Results</h3>
      </summary>
      {/* Two tables in one card (task-372, decision 15): delivery, then engagement. */}
      <div className="group results-card">
        <DataTable
          label="Delivery by variant"
          columns={delivery}
          items={rows}
          emptyMessage="Nothing sent yet."
          rowClassName={(r) => (r.id === 0 ? 'row-total' : undefined)}
        />
        <DataTable
          label="Engagement by variant"
          columns={engagement}
          items={rows}
          emptyMessage="Nothing sent yet."
          rowClassName={(r) => (r.id === 0 ? 'row-total' : undefined)}
        />
      </div>
      <p className="muted results-note">
        Counted per delivery. Click rate is unique clickers over sent. Opens are not counted.
        {data.unsubscribes_partial && ` Unsubscribes made before ${since} are not counted.`}
      </p>
    </details>
  )
}

type Row = VariantResults

function count(value: number | null | undefined) {
  return value == null ? '—' : value.toLocaleString()
}

function percent(value: number | null | undefined) {
  return value == null ? '—' : `${(value * 100).toFixed(1)} %`
}

/** The excluded count, with the stages that excluded them on a line below. */
function excluded(row: Row) {
  const stages = Object.entries(row.excluded_by_stage ?? {})
  if (row.excluded === 0 || stages.length === 0) return count(row.excluded)
  return (
    <>
      {row.excluded.toLocaleString()}
      <span className="cell-sub">{stages.map(([stage, n]) => `${stage} ${n}`).join(', ')}</span>
    </>
  )
}

const variant: DataColumn<Row> = {
  key: 'name',
  header: 'Variant',
  isRowHeader: true,
  render: (r) => (r.channel ? `${r.name} (${r.channel})` : r.name),
}

const delivery: DataColumn<Row>[] = [
  variant,
  { key: 'recipients', header: 'Recipients', numeric: true, render: (r) => count(r.recipients) },
  { key: 'sent', header: 'Sent', numeric: true, render: (r) => count(r.sent) },
  { key: 'delivered', header: 'Delivered', numeric: true, render: (r) => count(r.delivered) },
  { key: 'failed', header: 'Failed', numeric: true, render: (r) => count(r.failed) },
  { key: 'excluded', header: 'Excluded', numeric: true, render: excluded },
  { key: 'bounced', header: 'Bounced', numeric: true, render: (r) => count(r.bounced) },
  { key: 'complaints', header: 'Complaints', numeric: true, render: (r) => count(r.complaints) },
]

const engagement: DataColumn<Row>[] = [
  variant,
  { key: 'clicks', header: 'Clicks', numeric: true, render: (r) => count(r.clicks_total) },
  { key: 'clickers', header: 'Unique clickers', numeric: true, render: (r) => count(r.unique_clickers) },
  { key: 'rate', header: 'Click rate', numeric: true, render: (r) => percent(r.click_rate) },
  { key: 'unsubscribes', header: 'Unsubscribes', numeric: true, render: (r) => count(r.unsubscribes) },
]
