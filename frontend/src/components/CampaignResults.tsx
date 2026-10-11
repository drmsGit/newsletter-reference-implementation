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
    <details open>
      <summary>
        <h2 style={{ display: 'inline' }}>Results</h2>
      </summary>
      <DataTable label="Results by variant" columns={columns} items={rows} emptyMessage="Nothing sent yet." />
      <p className="muted">
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

function excluded(row: Row) {
  const stages = Object.entries(row.excluded_by_stage ?? {})
  if (row.excluded === 0 || stages.length === 0) return count(row.excluded)
  return `${row.excluded.toLocaleString()} (${stages.map(([stage, n]) => `${stage} ${n}`).join(', ')})`
}

const columns: DataColumn<Row>[] = [
  {
    key: 'name',
    header: 'Variant',
    isRowHeader: true,
    render: (r) => (r.channel ? `${r.name} (${r.channel})` : r.name),
  },
  { key: 'recipients', header: 'Recipients', render: (r) => count(r.recipients) },
  { key: 'sent', header: 'Sent', render: (r) => count(r.sent) },
  { key: 'delivered', header: 'Delivered', render: (r) => count(r.delivered) },
  { key: 'failed', header: 'Failed', render: (r) => count(r.failed) },
  { key: 'excluded', header: 'Excluded', render: excluded },
  { key: 'bounced', header: 'Bounced', render: (r) => count(r.bounced) },
  { key: 'complaints', header: 'Complaints', render: (r) => count(r.complaints) },
  { key: 'clicks', header: 'Clicks', render: (r) => count(r.clicks_total) },
  { key: 'clickers', header: 'Unique clickers', render: (r) => count(r.unique_clickers) },
  { key: 'rate', header: 'Click rate', render: (r) => percent(r.click_rate) },
  { key: 'unsubscribes', header: 'Unsubscribes', render: (r) => count(r.unsubscribes) },
]
