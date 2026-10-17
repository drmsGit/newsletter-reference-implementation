import type { ReactNode } from 'react'
import { GridList, GridListItem } from 'react-aria-components'
import { useMatch, useNavigate } from 'react-router'

import BackTo from './BackTo'
import ScreenState from './ScreenState'

/**
 * Column 2 of a Settings part that is a list (decision 19's drill-in): the way
 * back to Settings, the title with its "New ..." button, what the part is,
 * and its records as rows, the open one the list's selection.
 */
export default function PartList<T extends { id: number }>({
  base,
  title,
  note,
  newButton,
  label,
  query,
  items,
  empty,
  row,
  textValue,
  dependencies,
}: {
  base: string
  title: string
  note: string
  newButton?: ReactNode
  label: string
  query: Parameters<typeof ScreenState>[0]['query']
  items: T[]
  empty: string
  row: (item: T) => ReactNode
  textValue: (item: T) => string
  /** What a row's drawing reads besides the item, so it redraws when that arrives. */
  dependencies?: unknown[]
}) {
  const navigate = useNavigate()
  const openId = Number(useMatch(`${base}/:id`)?.params.id)
  const open = Number.isInteger(openId) ? openId : undefined
  return (
    <>
      <div className="list-head">
        <BackTo to="/settings" label="Settings" />
        <div className="list-head__row">
          <h1>{title}</h1>
          {newButton}
        </div>
        <p className="muted list-note">{note}</p>
      </div>
      <ScreenState query={query}>
        <GridList
          aria-label={label}
          className="react-aria-GridList item-list"
          items={items}
          dependencies={dependencies}
          selectionMode="single"
          selectionBehavior="replace"
          selectedKeys={open !== undefined ? [open] : []}
          onSelectionChange={(keys) => {
            const [key] = keys === 'all' ? [] : [...keys]
            if (key !== undefined && Number(key) !== open) navigate(`${base}/${key}`)
          }}
          renderEmptyState={() => <p className="list-empty muted">{empty}</p>}
        >
          {(item: T) => (
            <GridListItem id={item.id} textValue={textValue(item)} className="react-aria-GridListItem item">
              {row(item)}
            </GridListItem>
          )}
        </GridList>
      </ScreenState>
    </>
  )
}

/** The details column before a record of a part is chosen. */
export function NothingChosen({ text }: { text: string }) {
  return <p className="detail-placeholder muted">{text}</p>
}
