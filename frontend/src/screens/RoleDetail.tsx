import { useState } from 'react'
import { Button, Checkbox, CheckboxGroup, Label } from 'react-aria-components'
import { useNavigate, useParams } from 'react-router'

import { useDeleteRole, usePermissionCatalogue, useRoles, useSetRolePermissions, type Role } from '../api/resources'
import DetailSection from '../components/DetailSection'
import ScreenState from '../components/ScreenState'
import { refused } from './People'
import { ROLES } from './Roles'

/** One role's permissions, grouped by whether they are held per brand or everywhere. */
export default function RoleDetail() {
  const { id } = useParams()
  const roles = useRoles()
  const role = roles.data?.find((r) => r.id === Number(id))
  return (
    // Column 3 of the roles (task-372). Keyed by the role and what it holds:
    // ticks made on one role are not carried to the next (doc-33).
    <div className="detail">
      <div className="detail-scroll">
        <ScreenState query={roles}>
          {roles.data &&
            (role ? (
              <Page key={`${role.id}:${role.permissions.join()}`} role={role} />
            ) : (
              <p role="alert" className="quiet">This role does not exist.</p>
            ))}
        </ScreenState>
      </div>
    </div>
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
      <div className="detail-head">
        <h2>{role.name}</h2>
        <p className="muted">
          {role.is_builtin ? 'Shipped with the platform' : 'Your own role'} · held by {role.holders}{' '}
          {role.holders === 1 ? 'person' : 'people'}
        </p>
      </div>
      <DetailSection id="role-permissions" title="Permissions">
        <ScreenState query={catalogue}>
          {group(true, 'Per brand: held on the brand the role is given on')}
          {group(false, 'Everywhere: held on every brand at once')}
        </ScreenState>
        <div>
          <Button isDisabled={!changed || save.isPending} onPress={() => save.mutate(held)}>Save permissions</Button>
        </div>
        {save.error != null && <p role="alert">Not saved: {refused(save.error)}</p>}
      </DetailSection>
      {!role.is_builtin && (
        <DetailSection id="role-delete" title="Delete">
          <p>
            <Button
              className="btn-destructive"
              isDisabled={role.holders > 0}
              onPress={() => remove.mutate(undefined, { onSuccess: () => navigate(ROLES) })}
            >
              Delete {role.name}
            </Button>
            {role.holders > 0 && <span className="muted"> Nobody may hold it when it is deleted.</span>}
          </p>
          {remove.error != null && <p role="alert">Not deleted: {refused(remove.error)}</p>}
        </DetailSection>
      )}
    </>
  )
}
