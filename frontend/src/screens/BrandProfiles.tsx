import { useState, type FormEvent } from 'react'
import {
  Button,
  Dialog,
  GridList,
  GridListItem,
  Heading,
  Input,
  Label,
  Modal,
  ModalOverlay,
  TextField,
} from 'react-aria-components'
import { useMatch, useNavigate } from 'react-router'

import {
  useBrandProfileStructure,
  useBrandProfiles,
  useCreateBrandProfile,
  type BrandProfileSummary,
  type ProfileField,
} from '../api/resources'
import { HttpError } from '../api/session'
import BackTo from '../components/BackTo'
import Pager, { useOffset } from '../components/Pager'
import ScreenState from '../components/ScreenState'
import { ShortcutHint, useShortcut } from '../shortcuts/Shortcuts'

/** Where the profiles live: a part of Settings, not an area of its own (user, 2026-10-11). */
export const BRAND_PROFILES = '/settings/brand-profiles'

/** "Legal company name, Imprint URL" from field names, by the setup file's labels. */
export function fieldLabels(names: string[], structure: ProfileField[] | undefined): string {
  const labels = new Map((structure ?? []).map((f) => [f.name, f.label]))
  return names.map((name) => labels.get(name) ?? name).join(', ')
}

/**
 * The working brand's profiles (task-350; ADR-194): its looks, texts and legal
 * details. The default comes first; each row says what it still lacks before
 * an email may use it. Which fields a profile has comes from the
 * installation's setup file, so this screen names none of them itself.
 *
 * v2 (task-372, render 34): column 2 of the Settings drill-in, the open
 * profile beside it. No search box yet: the list does not search (TASK-390).
 */
export default function BrandProfiles() {
  const profiles = useBrandProfiles(useOffset())
  const structure = useBrandProfileStructure()
  const navigate = useNavigate()
  const openId = Number(useMatch(`${BRAND_PROFILES}/:id`)?.params.id)
  const open = Number.isInteger(openId) ? openId : undefined

  return (
    <>
      <div className="list-head">
        <BackTo to="/settings" label="Settings" />
        <div className="list-head__row">
          <h1>Brand profiles</h1>
          <NewProfile />
        </div>
        <p className="muted list-note">
          A profile is one look of this brand for its emails, with the legal details every email carries. Each
          variant picks one; new variants start on the default.
        </p>
      </div>
      <ScreenState query={profiles}>
        <GridList
          aria-label="Brand profiles"
          className="react-aria-GridList item-list"
          items={profiles.data?.items ?? []}
          dependencies={[structure.data]}
          selectionMode="single"
          selectionBehavior="replace"
          selectedKeys={open !== undefined ? [open] : []}
          onSelectionChange={(keys) => {
            const [key] = keys === 'all' ? [] : [...keys]
            if (key !== undefined && Number(key) !== open) navigate(`${BRAND_PROFILES}/${key}`)
          }}
          renderEmptyState={() => <p className="list-empty muted">This brand has no profiles yet.</p>}
        >
          {(p: BrandProfileSummary) => (
            <GridListItem id={p.id} textValue={p.name} className="react-aria-GridListItem item">
              <span className="item-title">{p.name}</span>
              <span className="item-summary muted">
                {[p.is_default ? 'Default' : null, p.language, p.kind].filter(Boolean).join(' · ')}
              </span>
              {/* In words, not a colour (CONSTRAINTS: nothing conveyed by colour alone). */}
              <span className={p.complete ? 'item-state item-state--ok' : 'item-state item-state--missing'}>
                {p.complete ? 'Complete' : `Missing: ${fieldLabels(p.missing, structure.data)}`}
              </span>
            </GridListItem>
          )}
        </GridList>
      </ScreenState>
      <div className="list-foot list-foot--end">
        <Pager page={profiles.data} />
      </div>
    </>
  )
}

/** The details column before a profile is chosen. */
export function NoProfileOpen() {
  return <p className="detail-placeholder muted">Select a profile to see its look and legal details.</p>
}

/** "New profile": a name, then the profile's page, where its fields are filled. */
function NewProfile() {
  const [open, setOpen] = useState(false)
  useShortcut('n', 'New brand profile', () => setOpen(true))
  return (
    <>
      <Button className="btn-primary" onPress={() => setOpen(true)}>
        New profile <ShortcutHint keys="n" />
      </Button>
      <ModalOverlay isOpen={open} onOpenChange={setOpen} isDismissable className="preview-overlay">
        <Modal className="create-modal">
          <Dialog aria-label="New brand profile">
            <CreateForm onCancel={() => setOpen(false)} />
          </Dialog>
        </Modal>
      </ModalOverlay>
    </>
  )
}

function CreateForm({ onCancel }: { onCancel: () => void }) {
  const create = useCreateBrandProfile()
  const navigate = useNavigate()
  const [name, setName] = useState('')

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!name.trim() || create.isPending) return
    create.mutate({ name: name.trim() }, { onSuccess: (profile) => navigate(`${BRAND_PROFILES}/${profile.id}`) })
  }

  return (
    <form className="dialog-form" onSubmit={submit}>
      <Heading slot="title">New brand profile</Heading>
      <TextField value={name} onChange={setName} isRequired autoFocus>
        <Label>Name</Label>
        <Input />
      </TextField>
      <p className="muted">
        It starts empty, in English, for marketing. To start from another profile, open that one and duplicate it.
      </p>
      {create.isError && (
        <p role="alert">
          {create.error instanceof HttpError && create.error.status === 403
            ? 'You do not have permission to manage brand profiles in this brand.'
            : `Not created: ${(create.error instanceof HttpError && create.error.detail) || 'the server refused it.'}`}
        </p>
      )}
      <div className="dialog-actions">
        <Button onPress={onCancel}>Cancel</Button>
        <Button type="submit" isDisabled={create.isPending || !name.trim()}>
          {create.isPending ? 'Creating…' : 'Create'}
        </Button>
      </div>
    </form>
  )
}
