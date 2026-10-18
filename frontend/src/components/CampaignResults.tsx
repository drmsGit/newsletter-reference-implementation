import { useState, type ReactNode } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { Button } from 'react-aria-components'

import { useCampaignResults, type VariantResults } from '../api/resources'

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
 * One table, its figures in two groups, Delivery and Engagement, each half
 * open from the start (Diede, 2026-10-18; it replaces task-372 decision 15's
 * two tables): a group shows its key figures, and a problem figure (failed,
 * bounced, complaints) whenever it is not zero, so a problem never hides;
 * opening a group shows every figure in it. The variant column stays put
 * when the table is wider than the card.
 */
export default function CampaignResults({ campaignId }: { campaignId: number }) {
  const results = useCampaignResults(campaignId)
  const [open, setOpen] = useState<Record<Group, boolean>>({ delivery: false, engagement: false })
  if (results.isError) return <p role="alert">The results could not be loaded.</p>
  const data = results.data
  if (!data || !data.campaign || data.variants.length === 0) return null

  const whole: Row = { ...data.campaign, id: 0, name: 'Whole campaign', channel: '' }
  const rows: Row[] = [whole, ...data.variants]
  const since = new Date(data.unsubscribes_counted_since).toLocaleDateString(undefined, { dateStyle: 'medium' })
  const shown = (column: Column) =>
    open[column.group] || column.key || (column.problem != null && rows.some((r) => (column.problem!(r) ?? 0) > 0))
  const groups = (['delivery', 'engagement'] as const).map((group) => {
    const all = COLUMNS.filter((c) => c.group === group)
    return { group, visible: all.filter(shown), folded: all.length - all.filter(shown).length }
  })

  return (
    <details open className="results">
      <summary>
        <ChevronDown size={16} strokeWidth={1.75} aria-hidden="true" className="results-chevron" />
        <h3>Results</h3>
      </summary>
      <div className="group results-card">
        <table className="results-table" aria-label="Results by variant">
          <thead>
            <tr className="results-groups">
              <td className="results-variant" aria-hidden="true" />
              {groups.map(({ group, visible, folded }) => (
                <th key={group} scope="colgroup" colSpan={visible.length}
                  className={group === 'engagement' ? 'results-group results-sep' : 'results-group'}>
                  <Button className="results-toggle" aria-expanded={open[group]}
                    onPress={() => setOpen({ ...open, [group]: !open[group] })}>
                    {open[group] ? <ChevronDown size={14} aria-hidden="true" /> : <ChevronRight size={14} aria-hidden="true" />}
                    {GROUP_NAME[group]}
                    {!open[group] && folded > 0 && <span className="results-folded" aria-hidden="true">+{folded}</span>}
                  </Button>
                </th>
              ))}
            </tr>
            <tr>
              <th scope="col" className="results-variant">Variant</th>
              {groups.flatMap(({ group, visible }) =>
                visible.map((c, index) => (
                  <th key={c.name} scope="col" className={cell(group, index)}>{c.name}</th>
                )),
              )}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className={r.id === 0 ? 'row-total' : undefined}>
                <th scope="row" className="results-variant">{r.channel ? `${r.name} (${r.channel})` : r.name}</th>
                {groups.flatMap(({ group, visible }) =>
                  visible.map((c, index) => (
                    <td key={c.name} className={cell(group, index)}>{c.render(r)}</td>
                  )),
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted results-note">
        Counted per delivery. Click rate is unique clickers over sent. Opens are not counted.
        {data.unsubscribes_partial && ` Unsubscribes made before ${since} are not counted.`}
      </p>
    </details>
  )
}

type Row = VariantResults
type Group = 'delivery' | 'engagement'
type Column = {
  name: string
  group: Group
  render: (row: Row) => ReactNode
  /** Shown while the group is half open. */
  key?: boolean
  /** A count that means something went wrong: shown, though folded, when not zero. */
  problem?: (row: Row) => number | null | undefined
}

const GROUP_NAME: Record<Group, string> = { delivery: 'Delivery', engagement: 'Engagement' }

/** A figure's cell: right-aligned, the engagement group set off by a line. */
function cell(group: Group, index: number) {
  return group === 'engagement' && index === 0 ? 'num results-sep' : 'num'
}

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

/** In order; the key figures are the ones a group shows half open (Diede, 2026-10-18). */
const COLUMNS: Column[] = [
  { name: 'Recipients', group: 'delivery', render: (r) => count(r.recipients) },
  { name: 'Sent', group: 'delivery', key: true, render: (r) => count(r.sent) },
  { name: 'Delivered', group: 'delivery', key: true, render: (r) => count(r.delivered) },
  { name: 'Failed', group: 'delivery', problem: (r) => r.failed, render: (r) => count(r.failed) },
  { name: 'Excluded', group: 'delivery', render: excluded },
  { name: 'Bounced', group: 'delivery', problem: (r) => r.bounced, render: (r) => count(r.bounced) },
  { name: 'Complaints', group: 'delivery', problem: (r) => r.complaints, render: (r) => count(r.complaints) },
  { name: 'Click rate', group: 'engagement', key: true, render: (r) => percent(r.click_rate) },
  { name: 'Clicks', group: 'engagement', render: (r) => count(r.clicks_total) },
  { name: 'Unique clickers', group: 'engagement', render: (r) => count(r.unique_clickers) },
  { name: 'Unsubscribes', group: 'engagement', key: true, render: (r) => count(r.unsubscribes) },
]
