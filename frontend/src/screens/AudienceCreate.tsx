import { useState, type FormEvent } from 'react'
import { Button, Dialog, Heading, Input, Label, Modal, ModalOverlay, TextField } from 'react-aria-components'
import { useNavigate } from 'react-router'

import { useCampaigns, useCreateAudience, useSuggestAudience } from '../api/resources'
import { HttpError } from '../api/session'
import { DialogActions } from '../components/NewDialog'
import { keyShortcuts, ShortcutHint, useShortcut } from '../shortcuts/Shortcuts'

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
      <Button className="btn-primary" ref={keyShortcuts('n')} onPress={() => setOpen(true)}>
        New audience <ShortcutHint keys="n" />
      </Button>
      <ModalOverlay isOpen={open} onOpenChange={setOpen} isDismissable className="preview-overlay">
        <Modal className="create-modal">
          <Dialog aria-labelledby="new-audience-title">
            <Heading slot="title" id="new-audience-title">New audience</Heading>
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
      { onSuccess: (group) => { onCancel(); navigate(`/audiences/${group.id}`) } },
    )
  }

  return (
    <form className="dialog-form" onSubmit={submit}>
      <TextField value={name} onChange={setName} isRequired autoFocus>
        <Label>Name</Label>
        <Input />
      </TextField>
      <TextField value={description} onChange={setDescription}>
        <Label>Description</Label>
        <Input />
      </TextField>
      <p className="muted">Its rules and people are added on its page.</p>
      {create.isError && <p role="alert">{refusal(create.error, 'create an audience')}</p>}
      <DialogActions onCancel={onCancel}>
        <Button type="submit" isDisabled={create.isPending || !name.trim()}>
          {create.isPending ? 'Creating…' : 'Create'}
        </Button>
      </DialogActions>
    </form>
  )
}

/**
 * "Suggest an audience…" on a variant (ADR-188 addendum 2026-10-18): the
 * topics of this variant's content, each rule limited to its language, so a
 * German and an English variant each get their own readers. Asked first
 * because it makes a group; it closes, then opens the new group.
 */
export function SuggestForVariant({ variantId, variantName, language }: {
  variantId: number
  variantName: string
  language: string | null | undefined
}) {
  const [open, setOpen] = useState(false)
  const suggest = useSuggestAudience()
  const navigate = useNavigate()
  const heading = `suggest-audience-${variantId}`
  return (
    <>
      <Button onPress={() => setOpen(true)}>Suggest an audience…</Button>
      <ModalOverlay isOpen={open} onOpenChange={setOpen} isDismissable className="preview-overlay">
        <Modal className="create-modal">
          <Dialog aria-labelledby={heading}>
            <Heading slot="title" id={heading}>Suggest an audience for {variantName}</Heading>
            <p className="muted">
              A new audience with one rule per main topic of this variant&apos;s content
              {language ? <>, each limited to readers whose language is {language}</> : null}. You can change or remove each one.
            </p>
            {suggest.isError && <p role="alert">{refusal(suggest.error, 'create an audience')}</p>}
            <DialogActions onCancel={() => setOpen(false)}>
              <Button
                isDisabled={suggest.isPending}
                onPress={() =>
                  suggest.mutate({ variant_id: variantId }, {
                    onSuccess: (group) => {
                      setOpen(false)
                      navigate(`/audiences/${group.id}`)
                    },
                  })
                }
              >
                {suggest.isPending ? 'Suggesting…' : 'Suggest'}
              </Button>
            </DialogActions>
          </Dialog>
        </Modal>
      </ModalOverlay>
    </>
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
              One rule per main topic of the campaign&apos;s content, across all its variants, with no language. You
              can change or remove each one. For one language, suggest from a variant on the campaign&apos;s page.
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
                    onPress={() => suggest.mutate({ campaign_id: c.id }, { onSuccess: (group) => { setOpen(false); navigate(`/audiences/${group.id}`) } })}
                  >
                    {c.name}
                  </Button>
                </li>
              ))}
              {campaigns.data?.items.length === 0 && <li className="muted">No campaign matches.</li>}
            </ul>
            {suggest.isError && <p role="alert">{refusal(suggest.error, 'create an audience')}</p>}
            <DialogActions onCancel={() => setOpen(false)} />
          </Dialog>
        </Modal>
      </ModalOverlay>
    </>
  )
}
