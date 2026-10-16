import { useState, type FormEvent } from 'react'
import { Button, Input, Label, TextField } from 'react-aria-components'
import { useNavigate } from 'react-router'

import { useCreateIntegration, useIntegrations, type Integration } from '../api/resources'
import DataTable, { type DataColumn } from '../components/DataTable'
import ScreenState from '../components/ScreenState'
import { refused } from './People'

export const INTEGRATIONS = '/settings/integrations'

const COLUMNS: DataColumn<Integration>[] = [
  { key: 'name', header: 'Integration', isRowHeader: true, render: (i) => i.name },
  { key: 'state', header: 'State', render: (i) => (i.is_active ? 'Active' : 'Deactivated') },
  { key: 'keys', header: 'Live keys', render: (i) => `${i.live_keys}${i.expiring_soon ? ', one expiring soon' : ''}` },
  { key: 'grants', header: 'May', render: (i) => (i.grants.length ? i.grants.map((g) => g.permission).join(', ') : 'Nothing yet') },
]

/**
 * The systems that call this platform (task-358; ADR-166): a CRM syncing
 * contacts, an automation firing sends. Each has its own keys and its own
 * grants, per brand.
 */
export default function Integrations() {
  const integrations = useIntegrations()
  const navigate = useNavigate()
  return (
    <>
      <h1>Integrations</h1>
      <p className="muted">Other systems that call this platform, each with its own keys and what it may do.</p>
      <NewIntegration />
      <ScreenState query={integrations}>
        <DataTable label="Integrations" columns={COLUMNS} items={integrations.data ?? []}
          emptyMessage="No system calls this platform yet." onRowAction={(i) => navigate(`${INTEGRATIONS}/${i.id}`)} />
      </ScreenState>
    </>
  )
}

function NewIntegration() {
  const create = useCreateIntegration()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  function submit(event: FormEvent) {
    event.preventDefault()
    create.mutate({ name: name.trim(), ...(description.trim() ? { description: description.trim() } : {}) },
      { onSuccess: (integration) => navigate(`${INTEGRATIONS}/${integration.id}`) })
  }
  return (
    <form className="inline-form" onSubmit={submit} aria-label="Create an integration">
      <TextField value={name} onChange={setName} isRequired>
        <Label>New integration</Label>
        <Input />
      </TextField>
      <TextField value={description} onChange={setDescription}>
        <Label>What it is for</Label>
        <Input />
      </TextField>
      <Button type="submit" isDisabled={!name.trim() || create.isPending}>Create</Button>
      {create.error != null && <p role="alert">Not created: {refused(create.error)}</p>}
    </form>
  )
}
