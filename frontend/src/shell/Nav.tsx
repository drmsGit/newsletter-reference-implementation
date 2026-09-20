import { NavLink } from 'react-router'

/**
 * The screens in the first cut, in the order `docs/react-screen-inventory.md`
 * puts them: the core loop first, supporting screens after, administration last.
 *
 * Deliveries is absent rather than disabled. Its read surface is snapshot-scoped
 * only -- there is no route that lists sends, and none that fetches one by id --
 * so the screen cannot be built yet and is logged with C8 rather than shown as
 * something broken.
 */
const SCREENS = [
  { to: '/approvals', label: 'Approvals' },
  { to: '/campaigns', label: 'Campaigns' },
  { to: '/content', label: 'Content' },
  { to: '/audiences', label: 'Audiences' },
]

export default function Nav() {
  return (
    <nav className="nav" aria-label="Main">
      <ul>
        {SCREENS.map((screen) => (
          <li key={screen.to}>
            {/*
              NavLink sets aria-current="page" on the active link by itself,
              which is what tells a screen reader where in the application the
              reader currently is. A plain link would look identical and say
              nothing.
            */}
            <NavLink to={screen.to}>{screen.label}</NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
