import { useNavigate } from 'react-router'

import { useCampaigns, useCreateCampaign, type Campaign } from '../api/resources'
import DataTable, { type DataColumn } from '../components/DataTable'
import NameAndChannel from '../components/NameAndChannel'
import Pager, { useOffset } from '../components/Pager'
import { SearchBox, useSearch } from '../components/RecipientSearch'
import ScreenState from '../components/ScreenState'

const columns: DataColumn<Campaign>[] = [
  { key: 'name', header: 'Name', isRowHeader: true, render: (c) => c.name },
  { key: 'status', header: 'Status', render: (c) => c.status ?? '—' },
  { key: 'updated', header: 'Updated', render: (c) => formatDate(c.updated_at) },
]

/**
 * The campaign list. A row opens the campaign, variant by variant.
 *
 * A new campaign opens straight in the editor of its first variant, which the
 * server creates with it: pick the channel and the editor opens empty
 * (Manager Workflow interview Q4).
 */
export default function Campaigns() {
  const campaigns = useCampaigns(useOffset(), useSearch())
  const create = useCreateCampaign()
  const navigate = useNavigate()

  return (
    <>
      <h1>Campaigns</h1>
      <NameAndChannel
        nameLabel="New campaign"
        submitLabel="Create campaign"
        pending={create.isPending}
        error={create.error}
        onSubmit={(value) =>
          create.mutate(value, {
            onSuccess: (created) =>
              navigate(`/campaigns/${created.id}/variants/${created.variants[0].id}`),
          })
        }
      />
      <SearchBox label="Find a campaign by name" />
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
