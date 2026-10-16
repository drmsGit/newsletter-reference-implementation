import { useState } from 'react'
import { Button, Checkbox, CheckboxGroup, Label } from 'react-aria-components'
import { Link, useNavigate, useParams } from 'react-router'

import { useDeleteRole, usePermissionCatalogue, useRoles, useSetRolePermissions, type Role } from '../api/resources'
import ScreenState from '../components/ScreenState'
import { refused } from './People'
import { ROLES } from './Roles'

/** One role's permissions, grouped by whether they are held per brand or everywhere. */
export default function RoleDetail() {
  const { id } = useParams()
  const roles = useRoles()
  const role = roles.data?.find((r) => r.id === Number(id))
  return (
    <ScreenState query={roles}>
      {roles.data && (role ? <Page key={role.permissions.join()} role={role} /> : <p role="alert">This role does not exist.</p>)}
    </ScreenState>
  )
}

function Page({ role }: { role: Role }) {
  const catalogue = usePermissionCatalogue()
  const save = useSetRolePermissions(role.id)
  const remove = useDeleteRole(role.id)
  const navigate = useNavigate()
  const [held, setHeld] = useState<string[]>(role.permissions)
  const changed = [...held].sort().join() !== [...role.permissions].sort().join()
  const group = (brandScoped: boolean, label: string) => (
    <CheckboxGroup value={held} onChange={setHeld} className="permission-group">
      <Label>{label}</Label>
      {(catalogue.data ?? []).filter((p) => p.brand_scoped === brandScoped).map((p) => (
        <Checkbox key={p.key} value={p.key} isDisabled={p.key === 'view'}>
          <code>{p.key}</code> — {p.description}
        </Checkbox>
      ))}
    </CheckboxGroup>
  )
  return (
    <>
      <p><Link to={ROLES}>← Roles</Link></p>
      <h1>{role.name}</h1>
      <p className="muted">
        {role.is_builtin ? 'Shipped with the platform' : 'Your own role'} · held by {role.holders}{' '}
        {role.holders === 1 ? 'person' : 'people'}
      </p>
      <ScreenState query={catalogue}>
        {group(true, 'Per brand: held on the brand the role is given on')}
        {group(false, 'Everywhere: held on every brand at once')}
      </ScreenState>
      <p>
        <Button isDisabled={!changed || save.isPending} onPress={() => save.mutate(held)}>Save permissions</Button>
      </p>
      {save.error != null && <p role="alert">Not saved: {refused(save.error)}</p>}
      {!role.is_builtin && (
        <p>
          <Button isDisabled={role.holders > 0} onPress={() => remove.mutate(undefined, { onSuccess: () => navigate(ROLES) })}>
            Delete {role.name}
          </Button>
          {role.holders > 0 && <span className="muted"> Nobody may hold it when it is deleted.</span>}
        </p>
      )}
      {remove.error != null && <p role="alert">Not deleted: {refused(remove.error)}</p>}
    </>
  )
}
