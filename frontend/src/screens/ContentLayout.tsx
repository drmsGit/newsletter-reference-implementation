import type { ReactNode } from 'react'
import { NavLink } from 'react-router'

import BackTo from '../components/BackTo'
import DetailOutlet from '../components/DetailOutlet'

/**
 * Content and its parts as subpages under one menu entry (task-359), by the
 * same rule as Settings: the records, the shared category taxonomy, and the
 * category graph where the detail lives.
 *
 * v2 (task-372, decision 20, 2026-10-17): a drill-in, like Settings. Column 2
 * shows the parts; choosing Records or Categories replaces them with that
 * list and a way back, and the graph, a drawing, takes the whole width.
 */
export const RECORDS = '/content/records'

const PARTS = [
  { to: RECORDS, label: 'Records' },
  { to: '/content/categories', label: 'Categories' },
  { to: '/content/graph', label: 'Graph' },
]

/** `/content`: the parts, as Settings lists its own. */
export function ContentMenu() {
  return (
    <>
      <div className="list-head">
        <h1>Content</h1>
      </div>
      <nav aria-label="Content" className="menu">
        <ul className="item-list">
          {PARTS.map((part) => (
            <li key={part.to}>
              <NavLink to={part.to} className="menu-item">
                {part.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </>
  )
}

/** A part's list in column 2 and what is open in column 3, the address saying which. */
export function ContentSplit({ list, label }: { list: ReactNode; label: string }) {
  return (
    <div className="split">
      <section className="col-list" aria-label={label}>
        {list}
      </section>
      <section className="col-detail">
        <DetailOutlet />
      </section>
    </div>
  )
}

/** The details column before anything is chosen. */
export function NothingOpen({ text }: { text: string }) {
  return <p className="detail-placeholder muted">{text}</p>
}

/** The graph, full width (decision 20): it does not fit a list's column. */
export function GraphPage({ children }: { children: ReactNode }) {
  return (
    <>
      <BackTo to="/content" label="Content" />
      {children}
    </>
  )
}
