import { useNavigate } from 'react-router'

import { useAudienceGroups, type AudienceGroup } from '../api/resources'
import DataTable, { type DataColumn } from '../components/DataTable'
import ScreenState from '../components/ScreenState'
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
  const groups = useAudienceGroups()
  const navigate = useNavigate()

  return (
    <>
      <h1>Audiences</h1>
      <ScreenState query={groups}>
        <DataTable
          label="Audience groups"
          columns={columns}
          items={groups.data ?? []}
          emptyMessage="No audience groups in this brand yet."
          onRowAction={(g) => navigate(`/audiences/${g.id}`)}
        />
      </ScreenState>
    </>
  )
}
