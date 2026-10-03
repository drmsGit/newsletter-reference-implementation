import { useNavigate } from 'react-router'

import { useDecisionSlots, type DecisionSlotListed } from '../api/resources'
import DataTable, { type DataColumn } from '../components/DataTable'
import Pager, { useOffset } from '../components/Pager'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'

const columns: DataColumn<DecisionSlotListed>[] = [
  { key: 'name', header: 'Slot', isRowHeader: true, render: (s) => s.name },
  { key: 'campaign', header: 'Campaign', render: (s) => s.campaign_name },
  { key: 'variant', header: 'Variant', render: (s) => s.variant_name },
  { key: 'strategy', header: 'Strategy', render: (s) => s.decision_strategy },
  { key: 'picks', header: 'Picks made', render: (s) => s.resolution_count },
  { key: 'unique', header: 'Distinct content', render: (s) => s.unique_content_count },
  { key: 'last', header: 'Last pick', render: (s) => formatDate(s.last_resolution_at) },
]

/**
 * Every decision slot in the brand and what it has done (inventory B21) --
 * the Jinja "Decision Monitoring" page, read-only. A slot is configured where
 * it lives, on its variant; this screen is for seeing what slots pick.
 */
export default function DecisionSlots() {
  const slots = useDecisionSlots(useOffset())
  const navigate = useNavigate()

  return (
    <>
      <h1>Decision slots</h1>
      <ScreenState query={slots}>
        <DataTable
          label="Decision slots"
          columns={columns}
          items={slots.data?.items ?? []}
          emptyMessage="No decision slots in this brand yet."
          onRowAction={(s) => navigate(`/decision-slots/${s.id}`)}
        />
        <Pager page={slots.data} />
      </ScreenState>
    </>
  )
}
