import { NavLink, Outlet } from 'react-router'

/**
 * Content and its parts as subpages under one menu entry (task-359), by the
 * same rule as Settings: the records, the shared category taxonomy, and the
 * category graph where the detail lives.
 */
const PARTS = [
  // `end`: Records is only /content and a record, not the other parts.
  { to: '/content', label: 'Records', end: true },
  { to: '/content/categories', label: 'Categories', end: false },
  { to: '/content/graph', label: 'Graph', end: false },
]

export default function ContentLayout() {
  return (
    <>
      <nav className="subnav" aria-label="Content">
        <ul>
          {PARTS.map((part) => (
            <li key={part.to}>
              <NavLink to={part.to} end={part.end}>
                {part.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <Outlet />
    </>
  )
}
