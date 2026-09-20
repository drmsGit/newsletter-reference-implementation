import { Route, Routes } from 'react-router'

import RequireSession from './routes/RequireSession'
import SignIn from './screens/SignIn'
import Shell from './shell/Shell'

/**
 * The route table. ADR-170 point 1: routing is something this application
 * calls, not a framework that calls this application -- so the routes are
 * declared here and nothing is derived from the filesystem.
 *
 * Screens arrive per `docs/react-screen-inventory.md`'s cut. Sign-in is first
 * because nothing is reachable without it; the core loop follows in Phase 2.
 */
export default function App() {
  return (
    <Routes>
      <Route path="/sign-in" element={<SignIn />} />
      <Route
        element={
          <RequireSession>
            <Shell />
          </RequireSession>
        }
      >
        <Route path="/" element={<Home />} />
      </Route>
    </Routes>
  )
}

function Home() {
  return (
    <>
      <h1>Signed in</h1>
      <p>The core loop screens land in Phase 2.</p>
    </>
  )
}
