import { NavLink } from 'react-router'

/**
 * The screens in the first cut, in the order `docs/react-screen-inventory.md`
 * puts them: the core loop first, supporting screens after, administration last.
 */
const SCREENS = [
  { to: '/approvals', label: 'Approvals' },
  { to: '/campaigns', label: 'Campaigns' },
  { to: '/monitoring', label: 'Monitoring' },
  { to: '/content', label: 'Content' },
  { to: '/audiences', label: 'Audiences' },
  { to: '/deliveries', label: 'Deliveries' },
  // Supporting, read-mostly screens after the core loop.
  { to: '/decision-slots', label: 'Decision slots' },
  // Administration last, as the inventory orders it.
  { to: '/settings', label: 'Settings' },
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
