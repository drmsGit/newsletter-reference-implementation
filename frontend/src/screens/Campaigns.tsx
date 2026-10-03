import { useNavigate } from 'react-router'

import { useCampaigns, type Campaign } from '../api/resources'
import DataTable, { type DataColumn } from '../components/DataTable'
import Pager, { useOffset } from '../components/Pager'
import ScreenState from '../components/ScreenState'

const columns: DataColumn<Campaign>[] = [
  { key: 'name', header: 'Name', isRowHeader: true, render: (c) => c.name },
  { key: 'status', header: 'Status', render: (c) => c.status ?? '—' },
  { key: 'updated', header: 'Updated', render: (c) => formatDate(c.updated_at) },
]

/**
 * The campaign list. A row opens the campaign, variant by variant.
 */
export default function Campaigns() {
  const campaigns = useCampaigns(useOffset())
  const navigate = useNavigate()

  return (
    <>
      <h1>Campaigns</h1>
      <ScreenState query={campaigns}>
        <DataTable
          label="Campaigns"
          columns={columns}
          items={campaigns.data?.items ?? []}
          emptyMessage="No campaigns in this brand yet."
          onRowAction={(c) => navigate(`/campaigns/${c.id}`)}
        />
        <Pager page={campaigns.data} />
      </ScreenState>
    </>
  )
}

/**
 * Dates come back as ISO strings and are rendered in the reader's own locale.
 *
 * **Not the brand's locale and not the server's.** A timestamp is a moment,
 * and the person reading it is in one timezone -- theirs. The brand's language
 * governs what is sent to recipients, which is a different question answered
 * elsewhere.
 */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString()
}
