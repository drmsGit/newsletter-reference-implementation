import {
  Activity,
  CircleCheck,
  CircleUser,
  FileText,
  Mail,
  Send,
  Settings,
  SlidersHorizontal,
  Users,
  type LucideIcon,
} from 'lucide-react'
import { NavLink, useNavigate } from 'react-router'

import { ShortcutHint, useShortcut } from '../shortcuts/Shortcuts'

/**
 * The screens in the first cut, in the order `docs/react-screen-inventory.md`
 * puts them: the core loop first, supporting screens after, administration last.
 *
 * `go` is the second key of each screen's "g then …" shortcut (task-266):
 * declared here, beside the link, so the menu and the keys come from one list.
 * `icon` is its Lucide icon (task-372, decided 2026-10-17); `gap` puts space
 * before it, as the navigation board does before Settings.
 */
export const SCREENS: { to: string; label: string; go: string; icon: LucideIcon; gap?: boolean }[] = [
  { to: '/approvals', label: 'Approvals', go: 'a', icon: CircleCheck },
  { to: '/campaigns', label: 'Campaigns', go: 'c', icon: Send },
  { to: '/monitoring', label: 'Monitoring', go: 'm', icon: Activity },
  { to: '/content', label: 'Content', go: 't', icon: FileText },
  { to: '/audiences', label: 'Audiences', go: 'u', icon: Users },
  { to: '/recipients', label: 'Recipients', go: 'r', icon: CircleUser },
  { to: '/deliveries', label: 'Deliveries', go: 'd', icon: Mail },
  // Supporting, read-mostly screens after the core loop.
  { to: '/decision-slots', label: 'Decision slots', go: 's', icon: SlidersHorizontal },
  // Administration last, as the inventory orders it.
  // Brand profiles are a part of Settings, reached from there (SettingsLayout).
  { to: '/settings', label: 'Settings', go: ',', icon: Settings, gap: true },
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
      <ul className="nav-list">
        {SCREENS.map(({ to, label, go, icon: Icon, gap }) => (
          <li key={to} className={gap ? 'nav-gap-before' : undefined}>
            {/*
              NavLink sets aria-current="page" on the active link by itself,
              which is what tells a screen reader where in the application the
              reader currently is. A plain link would look identical and say
              nothing.
            */}
            <NavLink to={to} className="nav-item">
              <Icon size={16} strokeWidth={1.75} aria-hidden="true" />
              {/* Visually hidden in the rail, never removed: the link keeps its name. */}
              <span className="nav-label">{label}</span>
              <ShortcutHint keys={`g ${go}`} />
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
