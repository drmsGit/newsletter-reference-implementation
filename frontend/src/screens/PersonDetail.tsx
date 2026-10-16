import { useState } from 'react'
import { Button } from 'react-aria-components'
import { Link, useParams } from 'react-router'

import { useAddGrant, useAdminBrands, usePeople, useRemoveGrant, useRoles, useSetPersonActive, type Person } from '../api/resources'
import Choice from '../components/Choice'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'
import { PEOPLE, refused } from './People'

/** One person: their grants, role by brand, and whether they may sign in. */
export default function PersonDetail() {
  const { id } = useParams()
  const people = usePeople()
  const person = people.data?.find((p) => p.id === Number(id))
  return (
    <ScreenState query={people}>
      {people.data && (person ? <Page person={person} /> : <p role="alert">This person has no account here.</p>)}
    </ScreenState>
  )
}

function Page({ person }: { person: Person }) {
  const roles = useRoles()
  const brands = useAdminBrands()
  const add = useAddGrant(person.id)
  const remove = useRemoveGrant(person.id)
  const active = useSetPersonActive(person.id)
  const multiBrand = (brands.data?.length ?? 0) > 1
  const [role, setRole] = useState('')
  const [brand, setBrand] = useState('')
  const error = add.error ?? remove.error ?? active.error
  return (
    <>
      <p><Link to={PEOPLE}>← Users</Link></p>
      <h1>{person.display_name || person.email}</h1>
      <dl className="facts">
        <dt>Email</dt>
        <dd>{person.email}</dd>
        <dt>Account</dt>
        <dd>
          {person.is_active ? 'Active' : 'Deactivated'}
          {person.is_external ? ', from outside the company' : ''}
        </dd>
        <dt>Last sign-in</dt>
        <dd>{person.last_login_at ? formatDate(person.last_login_at) : 'Never'}</dd>
        <dt>Signed in now</dt>
        <dd>{person.live_sessions} {person.live_sessions === 1 ? 'session' : 'sessions'}</dd>
      </dl>

      <section aria-labelledby="person-access">
        <h2 id="person-access">Access</h2>
        {person.grants.length === 0 ? (
          <p className="muted">No role yet: they can sign in but see nothing.</p>
        ) : (
          <ul aria-label="Roles">
            {person.grants.map((g) => (
              <li key={g.id}>
                {multiBrand ? `${g.role_name} on ${g.brand_name}` : g.role_name}{' '}
                <Button onPress={() => remove.mutate(g.id)}>Remove</Button>
              </li>
            ))}
          </ul>
        )}
        <p className="inline-form">
          <Choice label="Give a role" options={(roles.data ?? []).map((r) => ({ id: String(r.id), name: r.name }))}
            selected={role} onChange={setRole} placeholder="Choose a role" />
          {multiBrand && (
            <Choice label="On brand" options={(brands.data ?? []).map((b) => ({ id: String(b.id), name: b.name }))}
              selected={brand} onChange={setBrand} placeholder="The default brand" />
          )}
          <Button isDisabled={!role || add.isPending}
            onPress={() => add.mutate({ role_id: Number(role), ...(brand ? { brand_id: Number(brand) } : {}) },
              { onSuccess: () => setRole('') })}>
            Give
          </Button>
        </p>
      </section>

      <section aria-labelledby="person-account">
        <h2 id="person-account">Sign-in</h2>
        {person.is_you ? (
          <p className="muted">This is you. Someone else who manages users can deactivate your account.</p>
        ) : person.is_active ? (
          <Button onPress={() => active.mutate(false)}>Deactivate (signs them out now)</Button>
        ) : (
          <Button onPress={() => active.mutate(true)}>Reactivate</Button>
        )}
      </section>
      {error != null && <p role="alert">Not changed: {refused(error)}</p>}
    </>
  )
}
