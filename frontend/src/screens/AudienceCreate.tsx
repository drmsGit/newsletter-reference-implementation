import { useState, type FormEvent } from 'react'
import { Button, Dialog, Heading, Input, Label, Modal, ModalOverlay, TextField } from 'react-aria-components'
import { useNavigate } from 'react-router'

import { useCampaigns, useCreateAudience, useSuggestAudience } from '../api/resources'
import { HttpError } from '../api/session'
import { ShortcutHint, useShortcut } from '../shortcuts/Shortcuts'

function refusal(error: unknown, what: string) {
  if (error instanceof HttpError && error.status === 403) return `You do not have permission to ${what} in this brand.`
  return `Not created: ${(error instanceof HttpError && error.detail) || 'the server refused it.'}`
}

/**
 * "New audience" on the list (task-297; Audience Write Surface decision 1): a
 * name and a description, then the empty group's page, which is the editor.
 * `n` opens it, Enter creates, Esc closes.
 */
export function NewAudience() {
  const [open, setOpen] = useState(false)
  useShortcut('n', 'New audience', () => setOpen(true))
  return (
    <>
      <Button className="btn-primary" onPress={() => setOpen(true)}>
        New audience <ShortcutHint keys="n" />
      </Button>
      <ModalOverlay isOpen={open} onOpenChange={setOpen} isDismissable className="preview-overlay">
        <Modal className="create-modal">
          <Dialog aria-label="New audience">
            <CreateForm onCancel={() => setOpen(false)} />
          </Dialog>
        </Modal>
      </ModalOverlay>
    </>
  )
}

function CreateForm({ onCancel }: { onCancel: () => void }) {
  const create = useCreateAudience()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!name.trim() || create.isPending) return
    create.mutate(
      { name: name.trim(), description: description.trim() },
      { onSuccess: (group) => navigate(`/audiences/${group.id}`) },
    )
  }

  return (
    <form className="create-form" onSubmit={submit}>
      <Heading slot="title">New audience</Heading>
      <TextField value={name} onChange={setName} isRequired autoFocus>
        <Label>Name</Label>
        <Input />
      </TextField>
      <TextField value={description} onChange={setDescription}>
        <Label>Description</Label>
        <Input />
      </TextField>
      <p className="muted">Its rules and people are added on its page.</p>
      <Button type="submit" isDisabled={create.isPending || !name.trim()}>
        {create.isPending ? 'Creating…' : 'Create'}
      </Button>{' '}
      <Button onPress={onCancel}>Cancel</Button>
      {create.isError && <p role="alert">{refusal(create.error, 'create an audience')}</p>}
    </form>
  )
}

/**
 * "Suggest from campaign" (Manager Workflow 4.1): a new group with one
 * include rule per top category of the campaign's content, each badged as
 * suggested and editable like any other.
 */
export function SuggestFromCampaign() {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const campaigns = useCampaigns(0, q.trim())
  const suggest = useSuggestAudience()
  const navigate = useNavigate()
  return (
    <>
      <Button onPress={() => setOpen(true)}>Suggest from campaign</Button>
      <ModalOverlay isOpen={open} onOpenChange={setOpen} isDismissable className="preview-overlay">
        <Modal className="create-modal">
          <Dialog aria-label="Suggest an audience from a campaign">
            <Heading slot="title">Suggest an audience from a campaign</Heading>
            <p className="muted">
              One rule per main topic of the campaign&apos;s content. You can change or remove each one.
            </p>
            <TextField value={q} onChange={setQ} autoFocus>
              <Label>Campaign</Label>
              <Input />
            </TextField>
            <ul className="bind__results">
              {(campaigns.data?.items ?? []).map((c) => (
                <li key={c.id}>
                  <Button
                    isDisabled={suggest.isPending}
                    onPress={() => suggest.mutate(c.id, { onSuccess: (group) => navigate(`/audiences/${group.id}`) })}
                  >
                    {c.name}
                  </Button>
                </li>
              ))}
              {campaigns.data?.items.length === 0 && <li className="muted">No campaign matches.</li>}
            </ul>
            <Button onPress={() => setOpen(false)}>Cancel</Button>
            {suggest.isError && <p role="alert">{refusal(suggest.error, 'create an audience')}</p>}
          </Dialog>
        </Modal>
      </ModalOverlay>
    </>
  )
}
