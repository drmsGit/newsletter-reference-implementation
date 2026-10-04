import { useNavigate, useSearchParams } from 'react-router'

import { useContentList, type ContentRecord } from '../api/resources'
import CategoryChoice from '../components/CategoryChoice'
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
  // One category, assigned directly; the server then orders by fit (ADR-175
  // addendum 2026-10-04, task-270). The same choice the bind picker offers.
  const category = Number(params.get('category')) || null
  const search = useSearch()
  const content = useContentList(useOffset(), search, status || undefined, category)
  const filtered = Boolean(search || status || category)
  const navigate = useNavigate()

  function setFilter(key: string, value: string | null) {
    const next = new URLSearchParams(params)
    if (value === null) next.delete(key)
    else next.set(key, value)
    next.delete('offset')
    setParams(next)
  }

  return (
    <>
      <h1>Content</h1>
      <div className="filters">
        <SearchBox label="Find content by title or description" />
        <Choice
          label="Status"
          options={[
            { id: 'any', name: 'Any status' },
            { id: 'active', name: 'Active' },
            { id: 'inactive', name: 'Inactive' },
          ]}
          selected={status || 'any'}
          onChange={(v) => setFilter('status', v === 'any' ? null : v)}
        />
        <CategoryChoice selected={category} onChange={(id) => setFilter('category', id == null ? null : String(id))} />
      </div>
      <ScreenState query={content}>
        <DataTable
          label="Content records"
          columns={columns}
          items={content.data?.items ?? []}
          // With a filter set, an empty page says nothing about the brand.
          emptyMessage={filtered ? 'No content matches these filters.' : 'No content in this brand yet.'}
          onRowAction={(r) => navigate(`/content/${r.id}`)}
        />
        <Pager page={content.data} />
      </ScreenState>
    </>
  )
}
