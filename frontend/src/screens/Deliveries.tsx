import { GridList, GridListItem } from 'react-aria-components'
import { useMatch, useNavigate, useSearchParams } from 'react-router'

import { useDeliveries } from '../api/resources'
import DetailOutlet from '../components/DetailOutlet'
import Pager, { useOffset } from '../components/Pager'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'

/**
 * The deliveries list: what has been sent, across campaigns (task-28, B23).
 *
 * **Read-only, deliberately.** Planning and firing a send are writes with their
 * own permissions (`sends.plan`, `sends.execute`) and land with the rest of the
 * write surface. Where campaigns stand, including ones that have sent nothing,
 * is a different question -- task-216's monitoring view, not this one.
 *
 * v2 (task-372, renders 29 to 31): column 2, the open send (or one
 * recipient's message as sent) beside it. No search box yet: the list does
 * not search on the server (decision 21 is TASK-390).
 */
export default function Deliveries() {
  const deliveries = useDeliveries(useOffset())
  const navigate = useNavigate()
  const [params] = useSearchParams()
  // The send that is open, also while one recipient's message is.
  const openId = Number(useMatch('/deliveries/:id/*')?.params.id)
  const open = Number.isInteger(openId) ? openId : undefined

  return (
    <>
      <div className="list-head">
        <h1>Deliveries</h1>
      </div>
      <ScreenState query={deliveries}>
        <GridList
          aria-label="Sends"
          className="react-aria-GridList item-list"
          items={deliveries.data?.items ?? []}
          selectionMode="single"
          selectionBehavior="replace"
          selectedKeys={open !== undefined ? [open] : []}
          onSelectionChange={(keys) => {
            const [key] = keys === 'all' ? [] : [...keys]
            if (key === undefined || Number(key) === open) return
            // The list's page only: `?q=` is the open send's recipient search,
            // and must not follow into the next send.
            const offset = params.get('offset')
            navigate({ pathname: `/deliveries/${key}`, search: offset ? `?offset=${offset}` : '' })
          }}
          renderEmptyState={() => (
            <p className="list-empty muted">Nothing has been planned or sent in this brand yet.</p>
          )}
        >
          {(s) => (
            <GridListItem id={s.id} textValue={s.name} className="react-aria-GridListItem item">
              <span className="item-title">{s.name}</span>
              <span className="item-summary">
                {[s.campaign_name, s.variant_name].filter(Boolean).join(' / ') || '—'}
              </span>
              <span className="item-meta">
                <span>
                  {s.status} ·{' '}
                  {/*
                    The server's counts, as it gives them. They read 0 until a
                    send has run, and a draft showing "0 / 0 / 0" is the truth
                    about a draft -- so nothing here hides or recomputes them.
                  */}
                  <span>{`${s.sent_count} / ${s.failed_count} / ${s.excluded_count}`}</span>
                </span>
                <span>{formatDate(s.scheduled_at ?? s.created_at)}</span>
              </span>
            </GridListItem>
          )}
        </GridList>
      </ScreenState>
      <div className="list-foot">
        <span className="muted list-legend">Sent / failed / excluded</span>
        <Pager page={deliveries.data} />
      </div>
    </>
  )
}

/** The deliveries as a split (task-372): the list in column 2, the open send in column 3. */
export function DeliveriesSplit() {
  return (
    <div className="split">
      <section className="col-list" aria-label="Send list">
        <Deliveries />
      </section>
      <section className="col-detail">
        <DetailOutlet />
      </section>
    </div>
  )
}

/** The details column before a send is chosen. */
export function NoSendOpen() {
  return <p className="detail-placeholder muted">Select a send to see who it reached.</p>
}
