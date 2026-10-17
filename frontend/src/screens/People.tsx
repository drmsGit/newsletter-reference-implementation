import { useState, type FormEvent } from 'react'
import { Button, Checkbox, Input, Label, TextField } from 'react-aria-components'
import { useNavigate } from 'react-router'

import { useAdminBrands, useCreatePerson, usePeople, useRoles, type Person } from '../api/resources'
import { HttpError } from '../api/session'
import Choice from '../components/Choice'
import NewDialog, { DialogActions } from '../components/NewDialog'
import PartList from '../components/PartList'
import { formatDate } from './Campaigns'

export const PEOPLE = '/settings/users'

export function refused(error: unknown): string {
  if (error instanceof HttpError && error.status === 403) return 'you do not have permission to manage users.'
  return (error instanceof HttpError && error.detail) || 'the server refused it.'
}

/** "Manager on Acme, Viewer on Beta" — or just "Manager" when there is one brand (ADR-150 point 4). */
export function access(person: Person, multiBrand: boolean): string {
  if (person.grants.length === 0) return 'No role'
  return person.grants.map((g) => (multiBrand ? `${g.role_name} on ${g.brand_name}` : g.role_name)).join(', ')
}

/**
 * Who has an account and what they may do (task-358; ADR-150 addendum
 * 2026-10-16): the ADR-151 §5 review surface, now in the client.
 *
 * v2 (task-372, render 35): column 2 of the Settings drill-in, the person
 * beside it. No search box yet: the list does not search (TASK-390).
 */
export default function People() {
  const people = usePeople()
  const brands = useAdminBrands()
  const multiBrand = (brands.data?.length ?? 0) > 1
  return (
    <PartList
      base={PEOPLE}
      title="Users"
      note="Everyone with an account, and what they may do. Deactivating someone signs them out at once."
      newButton={<NewDialog label="New user">{(close) => <NewPerson multiBrand={multiBrand} onCancel={close} />}</NewDialog>}
      label="Users"
      query={people}
      items={people.data ?? []}
      dependencies={[multiBrand]}
      empty="Nobody has an account yet."
      textValue={(p) => p.display_name || p.email}
      row={(p) => (
        <>
          <span className="item-title">
            {p.display_name || p.email}
            {p.is_you && <span className="muted"> · you</span>}
            {p.is_external && <span className="muted"> · external</span>}
            {!p.is_active && <span className="muted"> · deactivated</span>}
          </span>
          {p.display_name && <span className="item-summary muted">{p.email}</span>}
          <span className="item-summary muted">
            <span>{access(p, multiBrand)}</span> · last sign-in{' '}
            {p.last_login_at ? formatDate(p.last_login_at) : 'never'}
          </span>
        </>
      )}
    />
  )
}

/** "New user" (render 45): the fields the inline form had, in a dialog. */
function NewPerson({ multiBrand, onCancel }: { multiBrand: boolean; onCancel: () => void }) {
  const create = useCreatePerson()
  const roles = useRoles()
  const brands = useAdminBrands()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [external, setExternal] = useState(false)
  const [role, setRole] = useState('viewer')
  const [brand, setBrand] = useState('')
  function submit(event: FormEvent) {
    event.preventDefault()
    create.mutate(
      { email: email.trim(), display_name: name.trim(), is_external: external, role_key: role,
        ...(brand ? { brand_id: Number(brand) } : {}) },
      { onSuccess: (person) => navigate(`${PEOPLE}/${person.id}`) },
    )
  }
  return (
    <form className="dialog-form" onSubmit={submit} aria-label="Create a user">
      <TextField value={email} onChange={setEmail} type="email" isRequired autoFocus>
        <Label>Email address</Label>
        <Input />
      </TextField>
      <TextField value={name} onChange={setName}>
        <Label>Name (optional)</Label>
        <Input />
      </TextField>
      <Checkbox isSelected={external} onChange={setExternal}>From outside the company (an agency, a freelancer)</Checkbox>
      <Choice label="Role" options={(roles.data ?? []).map((r) => ({ id: r.key, name: r.name }))} selected={role} onChange={setRole} />
      {multiBrand && (
        <Choice label="On brand" options={(brands.data ?? []).map((b) => ({ id: String(b.id), name: b.name }))}
          selected={brand} onChange={setBrand} placeholder="The default brand" />
      )}
      {create.error != null && <p role="alert">Not created: {refused(create.error)}</p>}
      <DialogActions onCancel={onCancel}>
        <Button type="submit" isDisabled={!email.trim() || create.isPending}>Create</Button>
      </DialogActions>
    </form>
  )
}
