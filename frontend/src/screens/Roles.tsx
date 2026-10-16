import { useState, type FormEvent } from 'react'
import { Button, Input, Label, TextField } from 'react-aria-components'
import { useNavigate } from 'react-router'

import { useCreateRole, useRoles, type Role } from '../api/resources'
import Choice from '../components/Choice'
import DataTable, { type DataColumn } from '../components/DataTable'
import ScreenState from '../components/ScreenState'
import { refused } from './People'

export const ROLES = '/settings/roles'

const COLUMNS: DataColumn<Role>[] = [
  { key: 'name', header: 'Role', isRowHeader: true, render: (r) => r.name },
  { key: 'kind', header: 'Kind', render: (r) => (r.is_builtin ? (r.is_customised ? 'Shipped, edited' : 'Shipped') : 'Your own') },
  { key: 'permissions', header: 'Permissions', render: (r) => String(r.permissions.length) },
  { key: 'holders', header: 'Held by', render: (r) => `${r.holders} ${r.holders === 1 ? 'person' : 'people'}` },
]

/** The roles and what each may do (task-358): the whole access policy in one place. */
export default function Roles() {
  const roles = useRoles()
  const navigate = useNavigate()
  return (
    <>
      <h1>Roles</h1>
      <p className="muted">A role is a set of permissions; a person holds a role on a brand. Every role can read.</p>
      <NewRole roles={roles.data ?? []} />
      <ScreenState query={roles}>
        <DataTable label="Roles" columns={COLUMNS} items={roles.data ?? []} emptyMessage="There are no roles."
          onRowAction={(r) => navigate(`${ROLES}/${r.id}`)} />
      </ScreenState>
    </>
  )
}

function NewRole({ roles }: { roles: Role[] }) {
  const create = useCreateRole()
  const navigate = useNavigate()
  const [key, setKey] = useState('')
  const [name, setName] = useState('')
  const [from, setFrom] = useState('')
  function submit(event: FormEvent) {
    event.preventDefault()
    create.mutate({ key: key.trim(), name: name.trim(), ...(from ? { copy_from: Number(from) } : {}) },
      { onSuccess: (role) => navigate(`${ROLES}/${role.id}`) })
  }
  return (
    <details className="new-entry">
      <summary>New role</summary>
      <form onSubmit={submit} aria-label="Create a role">
        <TextField value={key} onChange={setKey} isRequired>
          <Label>Key (lower case, no spaces)</Label>
          <Input />
        </TextField>
        <TextField value={name} onChange={setName}>
          <Label>Name</Label>
          <Input />
        </TextField>
        <Choice label="Start from" options={roles.map((r) => ({ id: String(r.id), name: r.name }))} selected={from}
          onChange={setFrom} placeholder="Nothing (only reading)" />
        <Button type="submit" isDisabled={!key.trim() || create.isPending}>Create</Button>
        {create.error != null && <p role="alert">Not created: {refused(create.error)}</p>}
      </form>
    </details>
  )
}
