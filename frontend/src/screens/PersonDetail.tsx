import { useState } from 'react'
import { Button } from 'react-aria-components'
import { useParams } from 'react-router'

import { useAddGrant, useAdminBrands, usePeople, useRemoveGrant, useRoles, useSetPersonActive, type Person } from '../api/resources'
import Choice from '../components/Choice'
import DetailSection from '../components/DetailSection'
import Fact from '../components/Fact'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'
import { refused } from './People'

/** One person: their grants, role by brand, and whether they may sign in. */
export default function PersonDetail() {
  const { id } = useParams()
  const people = usePeople()
  const person = people.data?.find((p) => p.id === Number(id))
  return (
    // Column 3 of the users (task-372, render 35). Keyed by the person: a
    // role chosen for one is not carried to the next (doc-33).
    <div className="detail">
      <div className="detail-scroll">
        <ScreenState query={people}>
          {people.data &&
            (person ? (
              <Page key={person.id} person={person} />
            ) : (
              <p role="alert" className="quiet">This person has no account here.</p>
            ))}
        </ScreenState>
      </div>
    </div>
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
      <div className="detail-head">
        <h2>{person.display_name || person.email}</h2>
      </div>
      <dl className="group fact-list">
        <Fact label="Email">{person.email}</Fact>
        <Fact label="Account">
          {person.is_active ? 'Active' : 'Deactivated'}
          {person.is_external ? ', from outside the company' : ''}
        </Fact>
        <Fact label="Last sign-in">{person.last_login_at ? formatDate(person.last_login_at) : 'Never'}</Fact>
        <Fact label="Signed in now">
          {person.live_sessions} {person.live_sessions === 1 ? 'session' : 'sessions'}
        </Fact>
      </dl>

      <DetailSection id="person-access" title="Access">
        {person.grants.length === 0 ? (
          <p className="muted">No role yet: they can sign in but see nothing.</p>
        ) : (
          <ul aria-label="Roles" className="link-list">
            {person.grants.map((g) => (
              <li key={g.id}>
                {multiBrand ? `${g.role_name} on ${g.brand_name}` : g.role_name}{' '}
                <Button className="btn-plain btn-sm" onPress={() => remove.mutate(g.id)}>
                  Remove
                </Button>
              </li>
            ))}
          </ul>
        )}
        <div className="inline-form">
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
        </div>
      </DetailSection>

      <DetailSection id="person-account" title="Sign-in">
        {person.is_you ? (
          <p className="muted">This is you. Someone else who manages users can deactivate your account.</p>
        ) : person.is_active ? (
          <div>
            <Button className="btn-destructive" onPress={() => active.mutate(false)}>
              Deactivate (signs them out now)
            </Button>
          </div>
        ) : (
          <div>
            <Button onPress={() => active.mutate(true)}>Reactivate</Button>
          </div>
        )}
      </DetailSection>
      {error != null && <p role="alert">Not changed: {refused(error)}</p>}
    </>
  )
}
