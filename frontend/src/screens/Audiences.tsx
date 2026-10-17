import { GridList, GridListItem } from 'react-aria-components'
import { useMatch, useNavigate, useSearchParams } from 'react-router'

import { useAudienceGroups } from '../api/resources'
import DetailOutlet from '../components/DetailOutlet'
import Pager, { useOffset } from '../components/Pager'
import { SearchBox, useSearch } from '../components/RecipientSearch'
import ScreenState from '../components/ScreenState'
import { NewAudience, SuggestFromCampaign } from './AudienceCreate'
import { formatDate } from './Campaigns'

/**
 * The audience groups: column 2 of the audiences screen (task-372, render
 * 37), the open group beside it. Opening another group keeps the list's
 * search and page, and nothing of the open group's own (its channel, its
 * people's page, its recipient search).
 */
export default function Audiences() {
  const search = useSearch()
  const groups = useAudienceGroups(useOffset(), search)
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const openId = Number(useMatch('/audiences/:id')?.params.id)
  const open = Number.isInteger(openId) ? openId : undefined

  function openGroup(id: number) {
    const keep = new URLSearchParams()
    for (const name of ['q', 'offset']) {
      const value = params.get(name)
      if (value) keep.set(name, value)
    }
    navigate({ pathname: `/audiences/${id}`, search: keep.toString() ? `?${keep}` : '' })
  }

  return (
    <>
      <div className="list-head">
        <h1>Audiences</h1>
        <p className="btnrow list-actions">
          <NewAudience /> <SuggestFromCampaign />
        </p>
      </div>
      <SearchBox label="Find an audience by name" compact />
      <ScreenState query={groups}>
        <GridList
          aria-label="Audience groups"
          className="react-aria-GridList item-list"
          items={groups.data?.items ?? []}
          selectionMode="single"
          selectionBehavior="replace"
          selectedKeys={open !== undefined ? [open] : []}
          onSelectionChange={(keys) => {
            const [key] = keys === 'all' ? [] : [...keys]
            if (key !== undefined && Number(key) !== open) openGroup(Number(key))
          }}
          renderEmptyState={() => (
            <p className="list-empty muted">
              {search ? 'No audience matches this search.' : 'No audience groups in this brand yet.'}
            </p>
          )}
        >
          {(g) => (
            <GridListItem id={g.id} textValue={g.name} className="react-aria-GridListItem item">
              <span className="item-title">{g.name}</span>
              <span className="item-summary">{g.description || <span className="muted">—</span>}</span>
              <span className="item-meta">
                <span>{formatDate(g.updated_at)}</span>
              </span>
            </GridListItem>
          )}
        </GridList>
      </ScreenState>
      <div className="list-foot list-foot--end">
        <Pager page={groups.data} />
      </div>
    </>
  )
}

/** The audiences as a split (task-372): the list in column 2, the open group in column 3. */
export function AudiencesSplit() {
  return (
    <div className="split">
      <section className="col-list" aria-label="Audience list">
        <Audiences />
      </section>
      <section className="col-detail">
        <DetailOutlet />
      </section>
    </div>
  )
}

/** The details column before a group is chosen. */
export function NoAudienceOpen() {
  return <p className="detail-placeholder muted">Select an audience to see who is in it.</p>
}
