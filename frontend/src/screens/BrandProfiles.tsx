import { useState, type FormEvent } from 'react'
import { Button, Dialog, Heading, Input, Label, Modal, ModalOverlay, TextField } from 'react-aria-components'
import { useNavigate } from 'react-router'

import {
  useBrandProfileStructure,
  useBrandProfiles,
  useCreateBrandProfile,
  type BrandProfileSummary,
  type ProfileField,
} from '../api/resources'
import { HttpError } from '../api/session'
import DataTable, { type DataColumn } from '../components/DataTable'
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

function columns(structure: ProfileField[] | undefined): DataColumn<BrandProfileSummary>[] {
  return [
    { key: 'name', header: 'Profile', isRowHeader: true, render: (p) => p.name },
    { key: 'default', header: 'Default', render: (p) => (p.is_default ? 'Default' : '') },
    { key: 'language', header: 'Language', render: (p) => p.language },
    { key: 'kind', header: 'Kind', render: (p) => p.kind },
    {
      key: 'state',
      header: 'Ready to send',
      // In words, not a colour (CONSTRAINTS: nothing conveyed by colour alone).
      render: (p) => (p.complete ? 'Complete' : `Missing: ${fieldLabels(p.missing, structure)}`),
    },
  ]
}

/**
 * The working brand's profiles (task-350; ADR-194): its looks, texts and legal
 * details. The default comes first; each row says what it still lacks before
 * an email may use it. Which fields a profile has comes from the
 * installation's setup file, so this screen names none of them itself.
 */
export default function BrandProfiles() {
  const profiles = useBrandProfiles(useOffset())
  const structure = useBrandProfileStructure()
  const navigate = useNavigate()

  return (
    <>
      <h1>Brand profiles</h1>
      <p className="muted">
        A profile is one look of this brand for its emails, with the legal details every email carries. Each
        variant picks one; new variants start on the default.
      </p>
      <NewProfile />
      <ScreenState query={profiles}>
        <DataTable
          label="Brand profiles"
          columns={columns(structure.data)}
          items={profiles.data?.items ?? []}
          emptyMessage="This brand has no profiles yet."
          onRowAction={(p) => navigate(`${BRAND_PROFILES}/${p.id}`)}
        />
        <Pager page={profiles.data} />
      </ScreenState>
    </>
  )
}

/** "New profile": a name, then the profile's page, where its fields are filled. */
function NewProfile() {
  const [open, setOpen] = useState(false)
  useShortcut('n', 'New brand profile', () => setOpen(true))
  return (
    <>
      <Button onPress={() => setOpen(true)}>
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
    <form className="create-form" onSubmit={submit}>
      <Heading slot="title">New brand profile</Heading>
      <TextField value={name} onChange={setName} isRequired autoFocus>
        <Label>Name</Label>
        <Input />
      </TextField>
      <p className="muted">
        It starts empty, in English, for marketing. To start from another profile, open that one and duplicate it.
      </p>
      <Button type="submit" isDisabled={create.isPending || !name.trim()}>
        {create.isPending ? 'Creating…' : 'Create'}
      </Button>{' '}
      <Button onPress={onCancel}>Cancel</Button>
      {create.isError && (
        <p role="alert">
          {create.error instanceof HttpError && create.error.status === 403
            ? 'You do not have permission to manage brand profiles in this brand.'
            : `Not created: ${(create.error instanceof HttpError && create.error.detail) || 'the server refused it.'}`}
        </p>
      )}
    </form>
  )
}
