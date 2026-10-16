import { useState, type FormEvent } from 'react'
import { Button, Input, Label, TextField } from 'react-aria-components'

import { useAdminBrands, useCreateBrand, useDeleteBrand, useRenameBrand, type AdminBrand } from '../api/resources'
import ScreenState from '../components/ScreenState'
import { refused } from './People'

export const BRANDS = '/settings/brands'

/** The installation's brands (task-358): each one a scope of content, campaigns and access (ADR-150). */
export default function Brands() {
  const brands = useAdminBrands()
  const remove = useDeleteBrand()
  return (
    <>
      <h1>Brands</h1>
      <p className="muted">
        A brand keeps its own content, campaigns, audiences and looks; people get roles per brand. Its key is
        permanent; its name can change. A brand is deleted only once nothing belongs to it.
      </p>
      <NewBrand />
      <ScreenState query={brands}>
        <ul className="brand-list" aria-label="Brands">
          {(brands.data ?? []).map((brand) => (
            <li key={brand.id}>
              <BrandRow brand={brand} onDelete={() => remove.mutate(brand.id)} />
            </li>
          ))}
        </ul>
      </ScreenState>
      {remove.error != null && <p role="alert">Not deleted: {refused(remove.error)}</p>}
    </>
  )
}

function BrandRow({ brand, onDelete }: { brand: AdminBrand; onDelete: () => void }) {
  const rename = useRenameBrand()
  const [name, setName] = useState(brand.name)
  const [asking, setAsking] = useState(false)
  return (
    <form className="inline-form" aria-label={`Brand ${brand.name}`}
      onSubmit={(event) => { event.preventDefault(); rename.mutate({ id: brand.id, name: name.trim() }) }}>
      <TextField value={name} onChange={setName}>
        <Label>Name of {brand.key}</Label>
        <Input />
      </TextField>
      <Button type="submit" isDisabled={name.trim() === brand.name || !name.trim() || rename.isPending}>Rename</Button>{' '}
      {asking ? (
        <span role="group" aria-label={`Delete ${brand.name}?`}>
          <Button onPress={onDelete}>Yes, delete {brand.name}</Button>{' '}
          <Button onPress={() => setAsking(false)}>Keep it</Button>
        </span>
      ) : (
        <Button onPress={() => setAsking(true)}>Delete {brand.name}…</Button>
      )}
      {rename.error != null && <p role="alert">Not renamed: {refused(rename.error)}</p>}
    </form>
  )
}

function NewBrand() {
  const create = useCreateBrand()
  const [key, setKey] = useState('')
  const [name, setName] = useState('')
  function submit(event: FormEvent) {
    event.preventDefault()
    create.mutate({ key: key.trim(), name: name.trim() }, { onSuccess: () => { setKey(''); setName('') } })
  }
  return (
    <form className="inline-form" onSubmit={submit} aria-label="Create a brand">
      <TextField value={key} onChange={setKey} isRequired>
        <Label>New brand's key (permanent)</Label>
        <Input />
      </TextField>
      <TextField value={name} onChange={setName} isRequired>
        <Label>Its name</Label>
        <Input />
      </TextField>
      <Button type="submit" isDisabled={!key.trim() || !name.trim() || create.isPending}>Create</Button>
      {create.error != null && <p role="alert">Not created: {refused(create.error)}</p>}
    </form>
  )
}
