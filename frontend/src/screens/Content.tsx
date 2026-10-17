import { GridList, GridListItem } from 'react-aria-components'
import { useLocation, useMatch, useNavigate, useSearchParams } from 'react-router'

import { useContentFields, useContentList } from '../api/resources'
import BackTo from '../components/BackTo'
import CategoryChoice from '../components/CategoryChoice'
import Choice from '../components/Choice'
import Pager, { useOffset } from '../components/Pager'
import { SearchBox, useSearch } from '../components/RecipientSearch'
import ScreenState from '../components/ScreenState'
import ContentCreate from './ContentCreate'

/**
 * The records: column 2 of Content's drill-in (task-372, render 27). A row
 * opens the record beside the list, keeping the search and filters in the
 * address; the open record is the list's single selection.
 */
export default function Content() {
  const [params, setParams] = useSearchParams()
  // Content's own status vocabulary (`CONTENT_STATUSES`); the server refuses others.
  const status = (params.get('status') ?? '') as '' | 'active' | 'inactive'
  // One category, assigned directly; the server then orders by fit (ADR-175
  // addendum 2026-10-04, task-270). The same choice the bind picker offers.
  const category = Number(params.get('category')) || null
  // Marked ready for one channel (ADR-174, task-286). The channels offered are
  // the ones the field definitions name, as the record page's sections are.
  const ready = params.get('ready')
  const channels = [...new Set((useContentFields().data ?? []).flatMap((f) => (f.channel ? [f.channel] : [])))]
  const search = useSearch()
  const content = useContentList(useOffset(), search, status || undefined, category, ready)
  const filtered = Boolean(search || status || category || ready)
  const navigate = useNavigate()
  const location = useLocation()
  // `/content/records` matches the pattern too: only a number is a record.
  const openId = Number(useMatch('/content/:id')?.params.id)
  const open = Number.isInteger(openId) ? openId : undefined

  function setFilter(key: string, value: string | null) {
    const next = new URLSearchParams(params)
    if (value === null) next.delete(key)
    else next.set(key, value)
    next.delete('offset')
    setParams(next)
  }

  return (
    <>
      <div className="list-head">
        <BackTo to="/content" label="Content" />
        <div className="list-head__row">
          <h1>Records</h1>
          <ContentCreate />
        </div>
      </div>
      <SearchBox label="Find content by title or description" compact />
      <div className="filters">
        <Choice
          label="Status"
          pulldown
          options={[
            { id: 'any', name: 'Any status' },
            { id: 'active', name: 'Active' },
            { id: 'inactive', name: 'Inactive' },
          ]}
          selected={status || 'any'}
          onChange={(v) => setFilter('status', v === 'any' ? null : v)}
        />
        <CategoryChoice
          pulldown
          selected={category}
          onChange={(id) => setFilter('category', id == null ? null : String(id))}
        />
        <Choice
          label="Ready for"
          pulldown
          options={[
            { id: 'any', name: 'Any channel' },
            ...channels.map((c) => ({ id: c, name: c.charAt(0).toUpperCase() + c.slice(1) })),
          ]}
          selected={ready && channels.includes(ready) ? ready : 'any'}
          onChange={(v) => setFilter('ready', v === 'any' ? null : v)}
        />
      </div>
      <ScreenState query={content}>
        <GridList
          aria-label="Content records"
          className="react-aria-GridList item-list"
          items={content.data?.items ?? []}
          selectionMode="single"
          selectionBehavior="replace"
          selectedKeys={open !== undefined ? [open] : []}
          onSelectionChange={(keys) => {
            const [key] = keys === 'all' ? [] : [...keys]
            if (key !== undefined && Number(key) !== open)
              navigate({ pathname: `/content/${key}`, search: location.search })
          }}
          renderEmptyState={() => (
            // With a filter set, an empty page says nothing about the brand.
            <p className="list-empty muted">
              {filtered ? 'No content matches these filters.' : 'No content in this brand yet.'}
            </p>
          )}
        >
          {(r) => (
            <GridListItem id={r.id} textValue={r.title} className="react-aria-GridListItem item">
              <span className="item-title">{r.title}</span>
              <span className="item-summary">{r.description || <span className="muted">—</span>}</span>
              <span className="item-meta">
                <span>{r.status ?? '—'}</span>
              </span>
            </GridListItem>
          )}
        </GridList>
      </ScreenState>
      <div className="list-foot list-foot--end">
        <Pager page={content.data} />
      </div>
    </>
  )
}
