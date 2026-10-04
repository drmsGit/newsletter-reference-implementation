import { NavLink, useNavigate } from 'react-router'

import { useShortcut } from '../shortcuts/Shortcuts'

/**
 * The screens in the first cut, in the order `docs/react-screen-inventory.md`
 * puts them: the core loop first, supporting screens after, administration last.
 *
 * `go` is the second key of each screen's "g then …" shortcut (task-266):
 * declared here, beside the link, so the menu and the keys come from one list.
 */
export const SCREENS = [
  { to: '/approvals', label: 'Approvals', go: 'a' },
  { to: '/campaigns', label: 'Campaigns', go: 'c' },
  { to: '/monitoring', label: 'Monitoring', go: 'm' },
  { to: '/content', label: 'Content', go: 't' },
  { to: '/audiences', label: 'Audiences', go: 'u' },
  { to: '/deliveries', label: 'Deliveries', go: 'd' },
  // Supporting, read-mostly screens after the core loop.
  { to: '/decision-slots', label: 'Decision slots', go: 's' },
  // Administration last, as the inventory orders it.
  { to: '/settings', label: 'Settings', go: ',' },
]

/** "g then a" goes to Approvals, and so on: one shortcut per screen. */
export function GoToShortcuts() {
  const navigate = useNavigate()
  return (
    <>
      {SCREENS.map((screen) => (
        <GoTo key={screen.to} keys={`g ${screen.go}`} label={screen.label} go={() => navigate(screen.to)} />
      ))}
    </>
  )
}

function GoTo({ keys, label, go }: { keys: string; label: string; go: () => void }) {
  useShortcut(keys, label, go, 'Go to')
  return null
}

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
