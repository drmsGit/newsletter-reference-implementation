import { NavLink, Outlet } from 'react-router'

import { BRAND_PROFILES } from './BrandProfiles'
import { PERSONALISATION } from './Personalisation'
import { PEOPLE } from './People'
import { ROLES } from './Roles'
import { INTEGRATIONS } from './Integrations'
import { BRANDS } from './Brands'

/**
 * Settings and its parts (user, 2026-10-11): one menu entry, with its parts
 * as subpages rather than areas of their own. "General" is the deployment's
 * settings as they were; brand profiles are a brand's (ADR-194).
 */
const PARTS = [
  // `end`: General is only /settings itself, not every page below it.
  { to: '/settings', label: 'General', end: true },
  { to: BRAND_PROFILES, label: 'Brand profiles', end: false },
  { to: PERSONALISATION, label: 'Personalisation', end: false },
  // Administration (task-358; ADR-150 addendum 2026-10-16): parts of
  // Settings, not areas of their own.
  { to: PEOPLE, label: 'Users', end: false },
  { to: ROLES, label: 'Roles', end: false },
  { to: INTEGRATIONS, label: 'Integrations', end: false },
  { to: BRANDS, label: 'Brands', end: false },
]

export default function SettingsLayout() {
  return (
    <>
      <nav className="subnav" aria-label="Settings">
        <ul>
          {PARTS.map((part) => (
            <li key={part.to}>
              {/* aria-current="page" on the active part, as in the main menu. */}
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
