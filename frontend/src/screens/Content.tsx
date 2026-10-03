import { useNavigate, useSearchParams } from 'react-router'

import { useContentList, type ContentRecord } from '../api/resources'
import DataTable, { type DataColumn } from '../components/DataTable'
import Choice from '../components/Choice'
import Pager, { useOffset } from '../components/Pager'
import { SearchBox, useSearch } from '../components/RecipientSearch'
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
  const [params, setParams] = useSearchParams()
  // Content's own status vocabulary (`CONTENT_STATUSES`); the server refuses others.
  const status = (params.get('status') ?? '') as '' | 'active' | 'inactive'
  const content = useContentList(useOffset(), useSearch(), status || undefined)
  const navigate = useNavigate()

  return (
    <>
      <h1>Content</h1>
      <div className="filters">
        <SearchBox label="Find content by title" />
        <Choice
          label="Status"
          options={[
            { id: 'any', name: 'Any status' },
            { id: 'active', name: 'Active' },
            { id: 'inactive', name: 'Inactive' },
          ]}
          selected={status || 'any'}
          onChange={(v) => {
            const next = new URLSearchParams(params)
            if (v === 'any') next.delete('status')
            else next.set('status', v)
            next.delete('offset')
            setParams(next)
          }}
        />
      </div>
      <ScreenState query={content}>
        <DataTable
          label="Content records"
          columns={columns}
          items={content.data?.items ?? []}
          emptyMessage="No content in this brand yet."
          onRowAction={(r) => navigate(`/content/${r.id}`)}
        />
        <Pager page={content.data} />
      </ScreenState>
    </>
  )
}
