import { useNavigate } from 'react-router'

import { useAudienceGroups, type AudienceGroup } from '../api/resources'
import DataTable, { type DataColumn } from '../components/DataTable'
import Pager, { useOffset } from '../components/Pager'
import { SearchBox, useSearch } from '../components/RecipientSearch'
import ScreenState from '../components/ScreenState'
import { NewAudience, SuggestFromCampaign } from './AudienceCreate'
import { formatDate } from './Campaigns'

const columns: DataColumn<AudienceGroup>[] = [
  { key: 'name', header: 'Name', isRowHeader: true, render: (g) => g.name },
  {
    key: 'description',
    header: 'Description',
    render: (g) => g.description || <span className="muted">—</span>,
  },
  { key: 'updated', header: 'Updated', render: (g) => formatDate(g.updated_at) },
]

export default function Audiences() {
  const groups = useAudienceGroups(useOffset(), useSearch())
  const navigate = useNavigate()

  return (
    <>
      <h1>Audiences</h1>
      <p>
        <NewAudience /> <SuggestFromCampaign />
      </p>
      <SearchBox label="Find an audience by name" />
      <ScreenState query={groups}>
        <DataTable
          label="Audience groups"
          columns={columns}
          items={groups.data?.items ?? []}
          emptyMessage="No audience groups in this brand yet."
          onRowAction={(g) => navigate(`/audiences/${g.id}`)}
        />
        <Pager page={groups.data} />
      </ScreenState>
    </>
  )
}
