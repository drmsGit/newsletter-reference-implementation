import { useCampaigns, type Campaign } from '../api/resources'
import DataTable, { type DataColumn } from '../components/DataTable'
import ScreenState from '../components/ScreenState'

const columns: DataColumn<Campaign>[] = [
  { key: 'name', header: 'Name', isRowHeader: true, render: (c) => c.name },
  { key: 'status', header: 'Status', render: (c) => c.status ?? '—' },
  { key: 'updated', header: 'Updated', render: (c) => formatDate(c.updated_at) },
]

/**
 * The campaign list.
 *
 * **Rows are not clickable, deliberately.** Campaign detail is inventory B11 --
 * the largest block of derived state in the application, scheduled with the
 * write surface -- so there is nothing to navigate to yet. A row that invites a
 * click and goes nowhere is worse than a row that does not invite one.
 */
export default function Campaigns() {
  const campaigns = useCampaigns()

  return (
    <>
      <h1>Campaigns</h1>
      <ScreenState query={campaigns}>
        <DataTable
          label="Campaigns"
          columns={columns}
          items={campaigns.data ?? []}
          emptyMessage="No campaigns in this brand yet."
        />
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
