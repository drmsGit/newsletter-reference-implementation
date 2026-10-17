import { useState, type FormEvent } from 'react'
import { Button, Input, Label, TextField } from 'react-aria-components'

import { useAdminBrands, useCreateBrand, useDeleteBrand, useRenameBrand, type AdminBrand } from '../api/resources'
import NewDialog, { DialogActions } from '../components/NewDialog'
import ScreenState from '../components/ScreenState'
import { refused } from './People'

export const BRANDS = '/settings/brands'

/**
 * The installation's brands (task-358): each one a scope of content, campaigns and access (ADR-150).
 *
 * v2 (task-372): beside the Settings menu, as General is, not a drill-in: a
 * list whose rows are forms and that has no details to open.
 */
export default function Brands() {
  const brands = useAdminBrands()
  const remove = useDeleteBrand()
  return (
    <div className="detail">
      <div className="detail-scroll">
        <div className="detail-head detail-head--bar">
          <div>
            <h2>Brands</h2>
            <p className="muted">
              A brand keeps its own content, campaigns, audiences and looks; people get roles per brand. Its key is
              permanent; its name can change. A brand is deleted only once nothing belongs to it.
            </p>
          </div>
          <NewDialog label="New brand">{(close) => <NewBrand onCancel={close} />}</NewDialog>
        </div>
        <ScreenState query={brands}>
          <ul className="group card-rows brand-list" aria-label="Brands">
            {(brands.data ?? []).map((brand) => (
              <li key={brand.id}>
                <BrandRow brand={brand} onDelete={() => remove.mutate(brand.id)} />
              </li>
            ))}
          </ul>
        </ScreenState>
        {remove.error != null && <p role="alert" className="quiet">Not deleted: {refused(remove.error)}</p>}
      </div>
    </div>
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
          <Button className="btn-destructive" onPress={onDelete}>
            Yes, delete {brand.name}
          </Button>{' '}
          <Button onPress={() => setAsking(false)}>Keep it</Button>
        </span>
      ) : (
        <Button className="btn-plain" onPress={() => setAsking(true)}>
          Delete {brand.name}…
        </Button>
      )}
      {rename.error != null && <p role="alert">Not renamed: {refused(rename.error)}</p>}
    </form>
  )
}

/** "New brand" (render 45): the fields the inline form had, in a dialog. */
function NewBrand({ onCancel }: { onCancel: () => void }) {
  const create = useCreateBrand()
  const [key, setKey] = useState('')
  const [name, setName] = useState('')
  function submit(event: FormEvent) {
    event.preventDefault()
    create.mutate({ key: key.trim(), name: name.trim() }, { onSuccess: onCancel })
  }
  return (
    <form className="dialog-form" onSubmit={submit} aria-label="Create a brand">
      <TextField value={key} onChange={setKey} isRequired autoFocus>
        <Label>New brand's key (permanent)</Label>
        <Input />
      </TextField>
      <TextField value={name} onChange={setName} isRequired>
        <Label>Its name</Label>
        <Input />
      </TextField>
      {create.error != null && <p role="alert">Not created: {refused(create.error)}</p>}
      <DialogActions onCancel={onCancel}>
        <Button type="submit" isDisabled={!key.trim() || !name.trim() || create.isPending}>Create</Button>
      </DialogActions>
    </form>
  )
}
