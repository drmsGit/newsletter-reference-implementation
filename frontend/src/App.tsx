import { Routes, Route } from 'react-router'

/**
 * The route table. ADR-170 point 1: routing is something this application
 * calls, not a framework that calls this application -- so the routes are
 * declared here and nothing is derived from the filesystem.
 *
 * Screens arrive per `docs/react-screen-inventory.md`'s cut: sign-in first,
 * because nothing is reachable without it.
 */
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Placeholder />} />
    </Routes>
  )
}

function Placeholder() {
  return (
    <main style={{ padding: 'calc(var(--brand-space) * 4)' }}>
      <h1>Newsletter Manager</h1>
      <p>
        Scaffold only. The sign-in screen and the shell are the next thing to
        land.
      </p>
    </main>
  )
}
