import { Check, Ellipsis, Loader, X, type LucideIcon } from 'lucide-react'
import { Link, useNavigate } from 'react-router'

import { useMonitoring, type MonitoredCampaign } from '../api/resources'
import DataTable, { type DataColumn } from '../components/DataTable'
import Pager, { useOffset } from '../components/Pager'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'

/** The server's state keys, in words and a glyph (task-372). Labels only: the states are the server's. */
const STATE: Record<string, { label: string; chip: string; icon: LucideIcon }> = {
  in_flight: { label: 'In flight', chip: 'chip-run', icon: Loader },
  in_preparation: { label: 'In preparation', chip: '', icon: Ellipsis },
  sent: { label: 'Sent', chip: 'chip-ok', icon: Check },
}

/** The state as chips: a glyph and a word, never colour alone; failures as a chip of their own. */
function StateChips({ c }: { c: MonitoredCampaign }) {
  const state = STATE[c.state]
  const Icon = state?.icon
  return (
    <span className="chips">
      <span className={`chip ${state?.chip ?? ''}`}>
        {Icon && <Icon size={12} strokeWidth={2} aria-hidden="true" />}
        {state?.label ?? c.state}
      </span>
      {c.has_failures && (
        <>
          {/* Read as one phrase, "In flight — with failures", as before. */}
          <span className="sr-only"> — </span>
          <span className="chip chip-bad">
            <X size={12} strokeWidth={2} aria-hidden="true" />
            with failures
          </span>
        </>
      )}
    </span>
  )
}

/** A variant's stage in words; the content screen's "used in" reads it too (task-267). */
export const STAGE_LABEL: Record<string, string> = {
  sending: 'sending',
  scheduled: 'scheduled',
  planned: 'send planned',
  snapshotted: 'approved, not planned',
  sent: 'sent',
  composing: 'composing',
}

const columns: DataColumn<MonitoredCampaign>[] = [
  { key: 'name', header: 'Campaign', isRowHeader: true, render: (c) => <Link to={`/campaigns/${c.id}`}>{c.name}</Link> },
  { key: 'state', header: 'State', render: (c) => <StateChips c={c} /> },
  {
    key: 'variants',
    header: 'Variants',
    /**
     * Each variant's own stage, because a variant is what gets planned and
     * sent (ADR-160 point 4): "in flight" says that something is moving, and
     * this says which part.
     */
    render: (c) =>
      c.variants
        .map((v) => `${v.name} (${v.channel}): ${STAGE_LABEL[v.stage] ?? v.stage}`)
        .join('; ') || '—',
  },
  { key: 'next', header: 'Next scheduled', render: (c) => formatDate(c.next_scheduled_at) },
  { key: 'last', header: 'Last sent', render: (c) => formatDate(c.last_sent_at) },
]

/**
 * Where are my campaigns (task-216).
 *
 * **Its own screen, not a column on the campaign list.** Manager Workflow
 * interview Q3.1 kept the list for *finding* a campaign and gave monitoring a
 * screen of its own -- a screen answers one question. Q5.4 kept it apart from
 * Deliveries too: this is campaign-level and includes campaigns that have sent
 * nothing; Deliveries is what one send did.
 *
 * In flight first, as the server orders it. A row opens the campaign.
 */
export default function Monitoring() {
  const monitoring = useMonitoring(useOffset())
  const navigate = useNavigate()

  return (
    // One wide table, no details column (task-372, decision 14, 2026-10-17):
    // the scan down each column is what this screen is for.
    <div className="wide-page">
      <div className="list-head">
        <h1>Monitoring</h1>
        <p className="list-count">Where are my campaigns? Open a row to go to its campaign.</p>
      </div>
      <div className="wide-body">
        <ScreenState query={monitoring}>
          <DataTable
            label="Campaign states"
            columns={columns}
            items={monitoring.data?.items ?? []}
            emptyMessage="No campaigns in this brand yet."
            onRowAction={(c) => navigate(`/campaigns/${c.id}`)}
          />
        </ScreenState>
      </div>
      <div className="list-foot">
        <span className="muted list-legend">No counts here: figures are on each campaign.</span>
        <Pager page={monitoring.data} />
      </div>
    </div>
  )
}
