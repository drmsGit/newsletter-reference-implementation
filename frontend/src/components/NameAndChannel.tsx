import { useState, type FormEvent } from 'react'
import { Button, Input, Label, TextField } from 'react-aria-components'

import { useSettings } from '../api/resources'
import { HttpError } from '../api/session'
import Choice from './Choice'

/**
 * A name and a channel, then one button: what creating a campaign and creating
 * a blank variant both ask (task-255). The channel is chosen here and never
 * again (ADR-160 point 5), from the channels this deployment has switched on;
 * the server refuses an unavailable one anyway (point 8), this just does not
 * offer it.
 */
export default function NameAndChannel({
  nameLabel,
  submitLabel,
  pending,
  error,
  onSubmit,
  onCancel,
}: {
  nameLabel: string
  submitLabel: string
  pending: boolean
  error: unknown
  onSubmit: (value: { name: string; channel: string }) => void
  /** In a create dialog (task-372, render 45): a Cancel beside the button. */
  onCancel?: () => void
}) {
  const settings = useSettings()
  const channels = (settings.data?.channels ?? [])
    .filter((c) => c.available)
    .map((c) => ({ id: c.name, name: c.name }))
  const [name, setName] = useState('')
  const [channel, setChannel] = useState('')
  const chosen = channel || channels[0]?.id || ''

  function submit(event: FormEvent) {
    event.preventDefault()
    if (name.trim() && chosen) onSubmit({ name: name.trim(), channel: chosen })
  }

  return (
    <form className={onCancel ? 'dialog-form' : 'create-form'} onSubmit={submit}>
      <TextField value={name} onChange={setName} isRequired autoFocus={onCancel !== undefined}>
        <Label>{nameLabel}</Label>
        <Input />
      </TextField>
      {channels.length > 0 && (
        <Choice label="Channel" options={channels} selected={chosen} onChange={setChannel} />
      )}
      {error != null && (
        <p role="alert">
          {error instanceof HttpError && error.status === 403
            ? 'You do not have permission to create this.'
            : `Not created: ${(error instanceof HttpError && error.detail) || 'the server refused it.'}`}
        </p>
      )}
      <div className={onCancel ? 'dialog-actions' : 'btnrow'}>
        {onCancel && <Button onPress={onCancel}>Cancel</Button>}
        <Button type="submit" isDisabled={pending || !name.trim() || !chosen}>
          {pending ? 'Creating…' : submitLabel}
        </Button>
      </div>
    </form>
  )
}
