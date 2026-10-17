import { useState, type FormEvent } from 'react'
import { Button, Input, Label, TextField } from 'react-aria-components'
import { useNavigate } from 'react-router'

import { useCreateIntegration, useIntegrations, type Integration } from '../api/resources'
import NewDialog, { DialogActions } from '../components/NewDialog'
import PartList from '../components/PartList'
import { refused } from './People'

export const INTEGRATIONS = '/settings/integrations'

/**
 * The systems that call this platform (task-358; ADR-166): a CRM syncing
 * contacts, an automation firing sends. Each has its own keys and its own
 * grants, per brand.
 *
 * v2 (task-372, render 36): column 2 of the Settings drill-in.
 */
export default function Integrations() {
  const integrations = useIntegrations()
  return (
    <PartList
      base={INTEGRATIONS}
      title="Integrations"
      note="Other systems that call this platform, each with its own keys and what it may do."
      newButton={<NewDialog label="New integration">{(close) => <NewIntegration onCancel={close} />}</NewDialog>}
      label="Integrations"
      query={integrations}
      items={integrations.data ?? []}
      empty="No system calls this platform yet."
      textValue={(i) => i.name}
      row={(i: Integration) => (
        <>
          <span className="item-title">{i.name}</span>
          <span className="item-summary muted">
            {i.is_active ? 'Active' : 'Deactivated'} · {i.live_keys} live key{i.live_keys === 1 ? '' : 's'}
            {i.expiring_soon ? ', one expiring soon' : ''}
          </span>
          <span className="item-summary muted">
            {i.grants.length ? [...new Set(i.grants.map((g) => g.permission))].join(', ') : 'Nothing yet'}
          </span>
        </>
      )}
    />
  )
}

/** "New integration" (render 45): the fields the inline form had, in a dialog. */
function NewIntegration({ onCancel }: { onCancel: () => void }) {
  const create = useCreateIntegration()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  function submit(event: FormEvent) {
    event.preventDefault()
    create.mutate({ name: name.trim(), ...(description.trim() ? { description: description.trim() } : {}) },
      { onSuccess: (integration) => { onCancel(); navigate(`${INTEGRATIONS}/${integration.id}`) } })
  }
  return (
    <form className="dialog-form" onSubmit={submit} aria-label="Create an integration">
      <TextField value={name} onChange={setName} isRequired autoFocus>
        <Label>New integration</Label>
        <Input />
      </TextField>
      <TextField value={description} onChange={setDescription}>
        <Label>What it is for</Label>
        <Input />
      </TextField>
      {create.error != null && <p role="alert">Not created: {refused(create.error)}</p>}
      <DialogActions onCancel={onCancel}>
        <Button type="submit" isDisabled={!name.trim() || create.isPending}>Create</Button>
      </DialogActions>
    </form>
  )
}
