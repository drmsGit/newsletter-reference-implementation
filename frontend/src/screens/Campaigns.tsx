import { useState } from 'react'
import { Button, Dialog, GridList, GridListItem, Heading, Modal, ModalOverlay } from 'react-aria-components'
import { useLocation, useMatch, useNavigate } from 'react-router'

import { useCampaigns, useCreateCampaign } from '../api/resources'
import DetailOutlet from '../components/DetailOutlet'
import NameAndChannel from '../components/NameAndChannel'
import Pager, { useOffset } from '../components/Pager'
import { SearchBox, useSearch } from '../components/RecipientSearch'
import ScreenState from '../components/ScreenState'

/**
 * The campaign list: column 2 of the campaigns screen (task-372, render 20).
 * A row opens the campaign beside the list, variant by variant; the search and
 * page stay in the address, so the list beside it does not change underneath.
 *
 * The open campaign is the list's single selection, as on the approvals list:
 * React Aria marks its row aria-selected for assistive technology.
 */
export default function Campaigns() {
  const search = useSearch()
  const campaigns = useCampaigns(useOffset(), search)
  const navigate = useNavigate()
  const location = useLocation()
  const open = useMatch('/campaigns/:id')?.params.id

  return (
    <>
      <div className="list-head list-head--action">
        <h1>Campaigns</h1>
        <NewCampaign />
      </div>
      <SearchBox label="Find a campaign by name" compact />
      <ScreenState query={campaigns}>
        <GridList
          aria-label="Campaigns"
          className="react-aria-GridList item-list"
          items={campaigns.data?.items ?? []}
          selectionMode="single"
          selectionBehavior="replace"
          selectedKeys={open !== undefined ? [Number(open)] : []}
          onSelectionChange={(keys) => {
            const [key] = keys === 'all' ? [] : [...keys]
            if (key !== undefined && String(key) !== open)
              navigate({ pathname: `/campaigns/${key}`, search: location.search })
          }}
          renderEmptyState={() => (
            <p className="list-empty muted">
              {search ? 'No campaign matches this search.' : 'No campaigns in this brand yet.'}
            </p>
          )}
        >
          {(c) => (
            <GridListItem id={c.id} textValue={c.name} className="react-aria-GridListItem item">
              <span className="item-title">{c.name}</span>
              <span className="item-meta">
                <span>{c.status ?? '—'}</span>
                <span>{formatDate(c.updated_at)}</span>
              </span>
            </GridListItem>
          )}
        </GridList>
      </ScreenState>
      <div className="list-foot list-foot--end">
        <Pager page={campaigns.data} />
      </div>
    </>
  )
}

/**
 * "New campaign" in the list's header opens a dialog (task-372, decision 22;
 * render 45). A new campaign opens straight in the editor of its first
 * variant, which the server creates with it: pick the channel and the editor
 * opens empty (Manager Workflow interview Q4). Enter creates, Esc closes.
 */
function NewCampaign() {
  const [open, setOpen] = useState(false)
  const create = useCreateCampaign()
  const navigate = useNavigate()
  return (
    <>
      <Button className="btn-primary" onPress={() => setOpen(true)}>
        New campaign
      </Button>
      <ModalOverlay isOpen={open} onOpenChange={setOpen} isDismissable className="preview-overlay">
        <Modal className="create-modal">
          <Dialog aria-labelledby="new-campaign-title">
            <Heading slot="title" id="new-campaign-title">
              New campaign
            </Heading>
            <NameAndChannel
              nameLabel="Name"
              submitLabel="Create campaign"
              pending={create.isPending}
              error={create.error}
              onCancel={() => setOpen(false)}
              onSubmit={(value) =>
                create.mutate(value, {
                  onSuccess: (created) =>
                    navigate(`/campaigns/${created.id}/variants/${created.variants[0].id}`),
                })
              }
            />
          </Dialog>
        </Modal>
      </ModalOverlay>
    </>
  )
}

/**
 * The campaigns screen as a split (task-372): the list in column 2, the open
 * campaign in column 3, the address saying which (`/campaigns/:id`, so links,
 * reload and the back button work as before). The variant editor and the send
 * steps are screens of their own, outside it.
 */
export function CampaignsSplit() {
  return (
    <div className="split">
      <section className="col-list" aria-label="Campaign list">
        <Campaigns />
      </section>
      <section className="col-detail">
        <DetailOutlet />
      </section>
    </div>
  )
}

/** The details column before a campaign is chosen. */
export function NoCampaignOpen() {
  return <p className="detail-placeholder muted">Select a campaign to see it.</p>
}

/**
 * Dates come back as ISO strings and are rendered in the reader's own locale.
 *
 * **Not the brand's locale and not the server's.** A timestamp is a moment,
 * and the person reading it is in one timezone -- theirs. The brand's language
 * governs what is sent to recipients, which is a different question answered
 * elsewhere.
 */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString()
}
