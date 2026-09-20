import { useNavigate } from 'react-router'

import { useContentList, type ContentRecord } from '../api/resources'
import DataTable, { type DataColumn } from '../components/DataTable'
import ScreenState from '../components/ScreenState'

const columns: DataColumn<ContentRecord>[] = [
  { key: 'title', header: 'Title', isRowHeader: true, render: (r) => r.title },
  { key: 'status', header: 'Status', render: (r) => r.status ?? '—' },
  {
    key: 'description',
    header: 'Description',
    render: (r) => r.description || <span className="muted">—</span>,
  },
]

export default function Content() {
  const content = useContentList()
  const navigate = useNavigate()

  return (
    <>
      <h1>Content</h1>
      <ScreenState query={content}>
        <DataTable
          label="Content records"
          columns={columns}
          items={content.data ?? []}
          emptyMessage="No content in this brand yet."
          onRowAction={(r) => navigate(`/content/${r.id}`)}
        />
      </ScreenState>
    </>
  )
}
