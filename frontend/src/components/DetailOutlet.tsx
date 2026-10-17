import { Outlet, useLocation } from 'react-router'

/**
 * Column 3 of a list beside its details (task-372): what is open, started
 * afresh for each item. Beside its list the details column would otherwise
 * stay mounted from one item to the next, and whatever was typed, chosen,
 * refused or reported on one would show on the next when that one is cached
 * (Codex doc-33 and doc-34). Keyed by the path, so the list's own search and
 * page (the query) do not remount it.
 */
export default function DetailOutlet() {
  const { pathname } = useLocation()
  return <Outlet key={pathname} />
}
