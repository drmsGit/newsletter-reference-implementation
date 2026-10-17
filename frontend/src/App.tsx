import { Route, Routes } from 'react-router'

import ApprovalDetail from './screens/ApprovalDetail'
import Approvals, { ApprovalsSplit, NoRequestOpen } from './screens/Approvals'
import AudienceDetail from './screens/AudienceDetail'
import { AudiencesSplit, NoAudienceOpen } from './screens/Audiences'
import CampaignDetail from './screens/CampaignDetail'
import { CampaignsSplit, NoCampaignOpen } from './screens/Campaigns'
import Content from './screens/Content'
import RecipientDetail from './screens/RecipientDetail'
import { NoRecipientOpen, RecipientsSplit } from './screens/Recipients'
import DecisionSlotDetail from './screens/DecisionSlotDetail'
import { DecisionSlotsSplit, NoSlotOpen } from './screens/DecisionSlots'
import ContentDetail from './screens/ContentDetail'
import Monitoring from './screens/Monitoring'
import VariantEditor from './screens/VariantEditor'
import SendVariant from './screens/SendVariant'
import Settings from './screens/Settings'
import BrandProfileDetail from './screens/BrandProfileDetail'
import { ContentMenu, ContentSplit, GraphPage, NothingOpen, RECORDS } from './screens/ContentLayout'
import Categories from './screens/Categories'
import CategoryGraph from './screens/CategoryGraph'
import CategoryDetail from './screens/CategoryDetail'
import People, { PEOPLE } from './screens/People'
import PersonDetail from './screens/PersonDetail'
import Roles, { ROLES } from './screens/Roles'
import RoleDetail from './screens/RoleDetail'
import Integrations, { INTEGRATIONS } from './screens/Integrations'
import IntegrationDetail from './screens/IntegrationDetail'
import Brands from './screens/Brands'
import Personalisation, { NoEntryOpen, PERSONALISATION, PersonalisationEntry } from './screens/Personalisation'
import BrandProfiles, { BRAND_PROFILES, NoProfileOpen } from './screens/BrandProfiles'
import { DeliveriesSplit, NoSendOpen } from './screens/Deliveries'
import { SettingsMenu, SettingsSplit } from './screens/SettingsLayout'
import { NothingChosen } from './components/PartList'
import { AI_PROMPTS, AiPromptDetail, AiPromptsSplit, NoTaskOpen } from './screens/AiPrompts'
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
        {/* The list beside the open request (task-372): one layout, the
            request in the address as before. */}
        <Route element={<ApprovalsSplit />}>
          <Route path="/" element={<NoRequestOpen />} />
          <Route path="/approvals" element={<NoRequestOpen />} />
          <Route path="/approvals/:id" element={<ApprovalDetail />} />
        </Route>
        {/* Static before dynamic is how React Router ranks these anyway; listed
            apart so the reader sees "history" is not an approval id. */}
        <Route path="/approvals/history" element={<Approvals mode="history" />} />
        <Route element={<CampaignsSplit />}>
          <Route path="/campaigns" element={<NoCampaignOpen />} />
          <Route path="/campaigns/:id" element={<CampaignDetail />} />
        </Route>
        <Route path="/campaigns/:id/variants/:variantId" element={<VariantEditor />} />
        <Route path="/campaigns/:id/variants/:variantId/send" element={<SendVariant />} />
        <Route path="/monitoring" element={<Monitoring />} />
        {/* Settings and its parts as subpages, under one menu entry. */}
        {/* Settings as a drill-in (task-372, decisions 19 and 23): the parts
            beside General, a part's list beside what is open. */}
        <Route path="/settings" element={<SettingsSplit label="Settings parts" list={<SettingsMenu />} />}>
          <Route index element={<Settings />} />
          <Route path="brands" element={<Brands />} />
        </Route>
        <Route element={<SettingsSplit label="Brand profile list" list={<BrandProfiles />} />}>
          <Route path={BRAND_PROFILES} element={<NoProfileOpen />} />
          <Route path={`${BRAND_PROFILES}/:id`} element={<BrandProfileDetail />} />
        </Route>
        <Route element={<SettingsSplit label="Entry list" list={<Personalisation />} />}>
          <Route path={PERSONALISATION} element={<NoEntryOpen />} />
          <Route path={`${PERSONALISATION}/:id`} element={<PersonalisationEntry />} />
        </Route>
        <Route element={<SettingsSplit label="User list" list={<People />} />}>
          <Route path={PEOPLE} element={<NothingChosen text="Select a person to see their access." />} />
          <Route path={`${PEOPLE}/:id`} element={<PersonDetail />} />
        </Route>
        <Route element={<SettingsSplit label="Role list" list={<Roles />} />}>
          <Route path={ROLES} element={<NothingChosen text="Select a role to see its permissions." />} />
          <Route path={`${ROLES}/:id`} element={<RoleDetail />} />
        </Route>
        <Route element={<SettingsSplit label="Integration list" list={<Integrations />} />}>
          <Route path={INTEGRATIONS} element={<NothingChosen text="Select an integration to see its keys." />} />
          <Route path={`${INTEGRATIONS}/:id`} element={<IntegrationDetail />} />
        </Route>
        <Route element={<AiPromptsSplit />}>
          <Route path={AI_PROMPTS} element={<NoTaskOpen />} />
          <Route path={`${AI_PROMPTS}/:key`} element={<AiPromptDetail />} />
        </Route>
        {/* Content and its parts as subpages (task-359), like Settings. */}
        {/* A drill-in (task-372, decision 20): the parts, then a part's list
            beside what is open; the graph full width. A record keeps its
            address, /content/:id, with the records beside it. */}
        <Route path="/content" element={<ContentSplit label="Content parts" list={<ContentMenu />} />}>
          <Route index element={<NothingOpen text="Choose records, categories or the graph." />} />
        </Route>
        <Route element={<ContentSplit label="Records" list={<Content />} />}>
          <Route path={RECORDS} element={<NothingOpen text="Select a record to see it." />} />
          <Route path="/content/:id" element={<ContentDetail />} />
        </Route>
        <Route element={<ContentSplit label="Categories" list={<Categories />} />}>
          <Route path="/content/categories" element={<NothingOpen text="Select a category to see it." />} />
          <Route path="/content/categories/:id" element={<CategoryDetail />} />
        </Route>
        <Route path="/content/graph" element={<GraphPage><CategoryGraph /></GraphPage>} />
        <Route element={<AudiencesSplit />}>
          <Route path="/audiences" element={<NoAudienceOpen />} />
          <Route path="/audiences/:id" element={<AudienceDetail />} />
        </Route>
        <Route element={<RecipientsSplit />}>
          <Route path="/recipients" element={<NoRecipientOpen />} />
          <Route path="/recipients/:id" element={<RecipientDetail />} />
        </Route>
        <Route element={<DecisionSlotsSplit />}>
          <Route path="/decision-slots" element={<NoSlotOpen />} />
          <Route path="/decision-slots/:id" element={<DecisionSlotDetail />} />
        </Route>
        <Route element={<DeliveriesSplit />}>
          <Route path="/deliveries" element={<NoSendOpen />} />
          <Route path="/deliveries/:id" element={<DeliveryDetail />} />
          <Route path="/deliveries/:id/executions/:executionId" element={<DeliveryAsSent />} />
        </Route>
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
