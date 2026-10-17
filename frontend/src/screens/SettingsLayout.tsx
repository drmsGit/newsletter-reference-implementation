import type { ReactNode } from 'react'
import { NavLink, Outlet } from 'react-router'

import { AI_PROMPTS } from './AiPrompts'
import { BRAND_PROFILES } from './BrandProfiles'
import { BRANDS } from './Brands'
import { INTEGRATIONS } from './Integrations'
import { PEOPLE } from './People'
import { PERSONALISATION } from './Personalisation'
import { ROLES } from './Roles'

/**
 * Settings and its parts (user, 2026-10-11): one menu entry, with its parts
 * as subpages rather than areas of their own. "General" is the deployment's
 * settings as they were; brand profiles are a brand's (ADR-194).
 *
 * v2 (task-372, decision 19): a drill-in. Column 2 shows the parts and
 * General sits beside them; choosing a part that is a list replaces the parts
 * with that list and a way back. AI prompts is a part of its own (decision 23).
 */
const PARTS = [
  // `end`: General is only /settings itself, not every page below it.
  { to: '/settings', label: 'General', end: true },
  { to: BRAND_PROFILES, label: 'Brand profiles', end: false },
  { to: PERSONALISATION, label: 'Personalisation', end: false },
  { to: AI_PROMPTS, label: 'AI prompts', end: false },
  // Administration (task-358; ADR-150 addendum 2026-10-16): parts of
  // Settings, not areas of their own.
  { to: PEOPLE, label: 'Users', end: false },
  { to: ROLES, label: 'Roles', end: false },
  { to: INTEGRATIONS, label: 'Integrations', end: false },
  { to: BRANDS, label: 'Brands', end: false },
]

/** Column 2 of `/settings`: the parts. */
export function SettingsMenu() {
  return (
    <>
      <div className="list-head">
        <h1>Settings</h1>
      </div>
      <nav aria-label="Settings" className="menu">
        <ul className="item-list">
          {PARTS.map((part) => (
            <li key={part.to}>
              {/* aria-current="page" on the active part, as in the main menu. */}
              <NavLink to={part.to} end={part.end} className="menu-item">
                {part.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </>
  )
}

/** A Settings screen: what column 2 holds, and what is open in column 3. */
export function SettingsSplit({ list, label }: { list: ReactNode; label: string }) {
  return (
    <div className="split">
      <section className="col-list" aria-label={label}>
        {list}
      </section>
      <section className="col-detail">
        <Outlet />
      </section>
    </div>
  )
}

/** A part not yet drawn as a drill-in, shown beside the menu with the page's own padding. */
export function Legacy({ children }: { children: ReactNode }) {
  return <div className="detail-legacy">{children}</div>
}
