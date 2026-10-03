import { Route, Routes } from 'react-router'

import ApprovalDetail from './screens/ApprovalDetail'
import Approvals from './screens/Approvals'
import AudienceDetail from './screens/AudienceDetail'
import Audiences from './screens/Audiences'
import CampaignDetail from './screens/CampaignDetail'
import Campaigns from './screens/Campaigns'
import Content from './screens/Content'
import ContentDetail from './screens/ContentDetail'
import Monitoring from './screens/Monitoring'
import Settings from './screens/Settings'
import Deliveries from './screens/Deliveries'
import DeliveryAsSent from './screens/DeliveryAsSent'
import DeliveryDetail from './screens/DeliveryDetail'
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
        {/*
          The approval inbox is the home screen. ADR-169 put it close to one,
          and it is the screen that answers "is anything waiting for me" --
          which is what a manager opens this client to find out.
        */}
        <Route path="/" element={<Approvals />} />
        <Route path="/approvals" element={<Approvals />} />
        <Route path="/approvals/:id" element={<ApprovalDetail />} />
        <Route path="/campaigns" element={<Campaigns />} />
        <Route path="/campaigns/:id" element={<CampaignDetail />} />
        <Route path="/monitoring" element={<Monitoring />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/content" element={<Content />} />
        <Route path="/content/:id" element={<ContentDetail />} />
        <Route path="/audiences" element={<Audiences />} />
        <Route path="/audiences/:id" element={<AudienceDetail />} />
        <Route path="/deliveries" element={<Deliveries />} />
        <Route path="/deliveries/:id" element={<DeliveryDetail />} />
        <Route
          path="/deliveries/:id/executions/:executionId"
          element={<DeliveryAsSent />}
        />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

function NotFound() {
  return (
    <>
      <h1>Not found</h1>
      <p>That screen does not exist in this client yet.</p>
    </>
  )
}
