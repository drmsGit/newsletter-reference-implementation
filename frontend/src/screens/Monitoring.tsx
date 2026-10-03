import { useNavigate } from 'react-router'

import { useMonitoring, type MonitoredCampaign } from '../api/resources'
import DataTable, { type DataColumn } from '../components/DataTable'
import Pager, { useOffset } from '../components/Pager'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'

/** The server's state keys, in words. Labels only: the states are the server's. */
const STATE_LABEL: Record<string, string> = {
  in_flight: 'In flight',
  in_preparation: 'In preparation',
  sent: 'Sent',
}

const STAGE_LABEL: Record<string, string> = {
  sending: 'sending',
  scheduled: 'scheduled',
  planned: 'send planned',
  snapshotted: 'approved, not planned',
  sent: 'sent',
  composing: 'composing',
}

const columns: DataColumn<MonitoredCampaign>[] = [
  { key: 'name', header: 'Campaign', isRowHeader: true, render: (c) => c.name },
  {
    key: 'state',
    header: 'State',
    render: (c) => `${STATE_LABEL[c.state] ?? c.state}${c.has_failures ? ' — with failures' : ''}`,
  },
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
    <>
      <h1>Monitoring</h1>
      <ScreenState query={monitoring}>
        <DataTable
          label="Campaign states"
          columns={columns}
          items={monitoring.data?.items ?? []}
          emptyMessage="No campaigns in this brand yet."
          onRowAction={(c) => navigate(`/campaigns/${c.id}`)}
        />
        <Pager page={monitoring.data} />
      </ScreenState>
    </>
  )
}
