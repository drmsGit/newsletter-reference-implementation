import { GridList, GridListItem } from 'react-aria-components'
import { Outlet, useLocation, useMatch, useNavigate } from 'react-router'

import { useDecisionSlots } from '../api/resources'
import Pager, { useOffset } from '../components/Pager'
import ScreenState from '../components/ScreenState'

/**
 * Every decision slot in the brand and what it has done (inventory B21) --
 * the Jinja "Decision Monitoring" page, read-only. A slot is configured where
 * it lives, on its variant; this screen is for seeing what slots pick.
 *
 * v2 (task-372, render 32): column 2, the open slot beside it. No search box
 * yet: the list does not search on the server (decision 21 is TASK-390).
 */
export default function DecisionSlots() {
  const slots = useDecisionSlots(useOffset())
  const navigate = useNavigate()
  const location = useLocation()
  const openId = Number(useMatch('/decision-slots/:id')?.params.id)
  const open = Number.isInteger(openId) ? openId : undefined

  return (
    <>
      <div className="list-head">
        <h1>Decision slots</h1>
        <p className="muted list-note">Read-only: slots are configured on their variant.</p>
      </div>
      <ScreenState query={slots}>
        <GridList
          aria-label="Decision slots"
          className="react-aria-GridList item-list"
          items={slots.data?.items ?? []}
          selectionMode="single"
          selectionBehavior="replace"
          selectedKeys={open !== undefined ? [open] : []}
          onSelectionChange={(keys) => {
            const [key] = keys === 'all' ? [] : [...keys]
            if (key !== undefined && Number(key) !== open)
              navigate({ pathname: `/decision-slots/${key}`, search: location.search })
          }}
          renderEmptyState={() => <p className="list-empty muted">No decision slots in this brand yet.</p>}
        >
          {(s) => (
            <GridListItem id={s.id} textValue={s.name} className="react-aria-GridListItem item">
              <span className="item-title">{s.name}</span>
              <span className="item-summary">
                <span>{s.campaign_name}</span> / <span>{s.variant_name}</span>
              </span>
              <span className="item-meta">
                <span>{s.decision_strategy}</span>
                <span>
                  {s.resolution_count.toLocaleString()} pick{s.resolution_count === 1 ? '' : 's'}
                </span>
              </span>
            </GridListItem>
          )}
        </GridList>
      </ScreenState>
      <div className="list-foot list-foot--end">
        <Pager page={slots.data} />
      </div>
    </>
  )
}

/** The slots as a split (task-372): the list in column 2, the open slot in column 3. */
export function DecisionSlotsSplit() {
  return (
    <div className="split">
      <section className="col-list" aria-label="Slot list">
        <DecisionSlots />
      </section>
      <section className="col-detail">
        <Outlet />
      </section>
    </div>
  )
}

/** The details column before a slot is chosen. */
export function NoSlotOpen() {
  return <p className="detail-placeholder muted">Select a slot to see what it picks.</p>
}
