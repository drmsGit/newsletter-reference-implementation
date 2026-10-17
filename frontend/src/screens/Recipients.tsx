import { GridList, GridListItem } from 'react-aria-components'
import { useMatch, useNavigate, useSearchParams } from 'react-router'

import { useRecipients } from '../api/resources'
import DetailOutlet from '../components/DetailOutlet'
import Pager, { useOffset } from '../components/Pager'
import { SearchBox, useSearch } from '../components/RecipientSearch'
import ScreenState from '../components/ScreenState'

/**
 * Look one person up (task-292; Manager Workflow interview Q4.5): the list is
 * only the way in to "why did this person get this". Read-only — the CRM owns
 * the person (ADR-120).
 *
 * v2 (task-372, render 38): column 2, the person beside it. Opening another
 * person keeps the list's search and page, not the open person's channel.
 */
export default function Recipients() {
  const search = useSearch()
  const recipients = useRecipients(useOffset(), search)
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const openId = Number(useMatch('/recipients/:id')?.params.id)
  const open = Number.isInteger(openId) ? openId : undefined

  function openPerson(id: number) {
    const keep = new URLSearchParams()
    for (const name of ['q', 'offset']) {
      const value = params.get(name)
      if (value) keep.set(name, value)
    }
    navigate({ pathname: `/recipients/${id}`, search: keep.toString() ? `?${keep}` : '' })
  }

  return (
    <>
      <div className="list-head">
        <h1>Recipients</h1>
      </div>
      <SearchBox label="Find a recipient by identifier or address" compact />
      <ScreenState query={recipients}>
        <GridList
          aria-label="Recipients"
          className="react-aria-GridList item-list"
          items={recipients.data?.items ?? []}
          selectionMode="single"
          selectionBehavior="replace"
          selectedKeys={open !== undefined ? [open] : []}
          onSelectionChange={(keys) => {
            const [key] = keys === 'all' ? [] : [...keys]
            if (key !== undefined && Number(key) !== open) openPerson(Number(key))
          }}
          renderEmptyState={() => <p className="list-empty muted">Nobody matches.</p>}
        >
          {(r) => (
            <GridListItem id={r.id} textValue={r.external_id} className="react-aria-GridListItem item">
              <span className="item-title">{r.external_id}</span>
              <span className="item-meta">
                <span>Reachable on {r.addresses.map((a) => a.channel).join(', ') || '—'}</span>
                <span>
                  {r.language ?? '—'} · {r.status}
                </span>
              </span>
            </GridListItem>
          )}
        </GridList>
      </ScreenState>
      <div className="list-foot list-foot--end">
        <Pager page={recipients.data} />
      </div>
    </>
  )
}

/** The recipients as a split (task-372): the list in column 2, the person in column 3. */
export function RecipientsSplit() {
  return (
    <div className="split">
      <section className="col-list" aria-label="Recipient list">
        <Recipients />
      </section>
      <section className="col-detail">
        <DetailOutlet />
      </section>
    </div>
  )
}

/** The details column before a person is chosen. */
export function NoRecipientOpen() {
  return <p className="detail-placeholder muted">Select a person to see why they got what they got.</p>
}
