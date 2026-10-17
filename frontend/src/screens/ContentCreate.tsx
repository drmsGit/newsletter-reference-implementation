import { useState, type FormEvent } from 'react'
import { Button, Dialog, Heading, Input, Label, Modal, ModalOverlay, TextField } from 'react-aria-components'
import { useNavigate } from 'react-router'

import { useCreateContent } from '../api/resources'
import { HttpError } from '../api/session'
import { DialogActions } from '../components/NewDialog'
import { ShortcutHint, useShortcut } from '../shortcuts/Shortcuts'

/**
 * "New record" on the Content list (task-281; Content Write Surface pass,
 * decision 6): a title, required, and a description, then the new record's
 * page, where every field autosaves. One way to fill fields, not two — so no
 * field is asked for here, and nothing else is required (ADR-177 point 4).
 * Keyboard-first (VE): `n` opens it, Enter creates, Esc closes.
 */
export default function ContentCreate() {
  const [open, setOpen] = useState(false)
  useShortcut('n', 'New content record', () => setOpen(true))
  return (
    <>
      <Button className="btn-primary" onPress={() => setOpen(true)}>
        New record <ShortcutHint keys="n" />
      </Button>
      <ModalOverlay isOpen={open} onOpenChange={setOpen} isDismissable className="preview-overlay">
        <Modal className="create-modal">
          <Dialog aria-labelledby="new-record-title">
            <Heading slot="title" id="new-record-title">New content record</Heading>
            <CreateForm onCancel={() => setOpen(false)} />
          </Dialog>
        </Modal>
      </ModalOverlay>
    </>
  )
}

function CreateForm({ onCancel }: { onCancel: () => void }) {
  const create = useCreateContent()
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!title.trim() || create.isPending) return
    create.mutate(
      { title: title.trim(), description: description.trim() },
      { onSuccess: (record) => navigate(`/content/${record.id}`) },
    )
  }

  return (
    <form className="dialog-form" onSubmit={submit}>
      <TextField value={title} onChange={setTitle} isRequired autoFocus>
        <Label>Title</Label>
        <Input />
      </TextField>
      <TextField value={description} onChange={setDescription}>
        <Label>Description</Label>
        <Input />
      </TextField>
      <p className="muted">The fields are filled on the record&apos;s page, where they save as you go.</p>
      {create.isError && (
        <p role="alert">
          {create.error instanceof HttpError && create.error.status === 403
            ? 'You do not have permission to create content in this brand.'
            : `Not created: ${(create.error instanceof HttpError && create.error.detail) || 'the server refused it.'}`}
        </p>
      )}
      <DialogActions onCancel={onCancel}>
        <Button type="submit" isDisabled={create.isPending || !title.trim()}>
          {create.isPending ? 'Creating…' : 'Create'}
        </Button>
      </DialogActions>
    </form>
  )
}
