import { useState, type FormEvent } from 'react'
import { Button, Input, Label, TextField } from 'react-aria-components'
import { useNavigate } from 'react-router'

import { useCreateRole, useRoles, type Role } from '../api/resources'
import Choice from '../components/Choice'
import NewDialog, { DialogActions } from '../components/NewDialog'
import PartList from '../components/PartList'
import { refused } from './People'

export const ROLES = '/settings/roles'

/** "Shipped", "Shipped, edited" or "Your own". */
function kind(r: Role): string {
  return r.is_builtin ? (r.is_customised ? 'Shipped, edited' : 'Shipped') : 'Your own'
}

/**
 * The roles and what each may do (task-358): the whole access policy in one place.
 *
 * v2 (task-372; not drawn, it follows Users): column 2 of the drill-in.
 */
export default function Roles() {
  const roles = useRoles()
  return (
    <PartList
      base={ROLES}
      title="Roles"
      note="A role is a set of permissions; a person holds a role on a brand. Every role can read."
      newButton={<NewDialog label="New role">{(close) => <NewRole roles={roles.data ?? []} onCancel={close} />}</NewDialog>}
      label="Roles"
      query={roles}
      items={roles.data ?? []}
      empty="There are no roles."
      textValue={(r) => r.name}
      row={(r) => (
        <>
          <span className="item-title">{r.name}</span>
          <span className="item-meta">
            <span>
              {kind(r)} · {r.permissions.length} permission{r.permissions.length === 1 ? '' : 's'}
            </span>
            <span>
              {r.holders} {r.holders === 1 ? 'person' : 'people'}
            </span>
          </span>
        </>
      )}
    />
  )
}

/** "New role" (render 45): the fields the inline form had, in a dialog. */
function NewRole({ roles, onCancel }: { roles: Role[]; onCancel: () => void }) {
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
    <form className="dialog-form" onSubmit={submit} aria-label="Create a role">
      <TextField value={key} onChange={setKey} isRequired autoFocus>
        <Label>Key (lower case, no spaces)</Label>
        <Input />
      </TextField>
      <TextField value={name} onChange={setName}>
        <Label>Name</Label>
        <Input />
      </TextField>
      <Choice label="Start from" options={roles.map((r) => ({ id: String(r.id), name: r.name }))} selected={from}
        onChange={setFrom} placeholder="Nothing (only reading)" />
      {create.error != null && <p role="alert">Not created: {refused(create.error)}</p>}
      <DialogActions onCancel={onCancel}>
        <Button type="submit" isDisabled={!key.trim() || create.isPending}>Create</Button>
      </DialogActions>
    </form>
  )
}
