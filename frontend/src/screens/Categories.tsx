import { useState, type FormEvent } from 'react'
import { Button, Input, Label, TextField } from 'react-aria-components'
import { useNavigate } from 'react-router'

import { useCategories, useCategoryRelations, useCreateCategory, type Category } from '../api/resources'
import { HttpError } from '../api/session'
import Choice from '../components/Choice'
import DataTable, { type DataColumn } from '../components/DataTable'
import ScreenState from '../components/ScreenState'

export const CATEGORIES = '/content/categories'
export const TYPES = [
  { id: 'main', name: 'Main' },
  { id: 'sub', name: 'Sub' },
]

export function refusal(error: unknown): string {
  if (error instanceof HttpError && error.status === 403) return 'you do not have permission to change categories.'
  return (error instanceof HttpError && error.detail) || 'the server refused it.'
}

/**
 * The category taxonomy (task-359): shared by every brand (ADR-150), so a
 * change here reaches all of them. Each row says where a category sits.
 */
export default function Categories() {
  const categories = useCategories()
  const relations = useCategoryRelations()
  const navigate = useNavigate()
  const names = new Map((categories.data ?? []).map((c) => [c.id, c.name]))
  const parentsOf = (id: number) =>
    (relations.data ?? []).filter((r) => r.child_category_id === id).map((r) => names.get(r.parent_category_id))
  const childrenOf = (id: number) => (relations.data ?? []).filter((r) => r.parent_category_id === id).length

  const columns: DataColumn<Category>[] = [
    { key: 'name', header: 'Category', isRowHeader: true, render: (c) => c.name },
    { key: 'type', header: 'Type', render: (c) => (c.type === 'main' ? 'Main' : 'Sub') },
    { key: 'parents', header: 'Under', render: (c) => parentsOf(c.id).join(', ') || '—' },
    { key: 'children', header: 'Subcategories', render: (c) => String(childrenOf(c.id)) },
  ]
  const sorted = [...(categories.data ?? [])].sort((a, b) => a.type.localeCompare(b.type) || a.name.localeCompare(b.name))

  return (
    <>
      <h1>Categories</h1>
      <p className="muted">
        The categories content is sorted into, and what a recipient's interests are counted in. They are shared by
        every brand: a change here reaches all of them.
      </p>
      <NewCategory />
      <ScreenState query={categories}>
        <DataTable
          label="Categories"
          columns={columns}
          items={sorted}
          emptyMessage="There are no categories yet."
          onRowAction={(c) => navigate(`${CATEGORIES}/${c.id}`)}
        />
      </ScreenState>
    </>
  )
}

function NewCategory() {
  const create = useCreateCategory()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [type, setType] = useState('main')
  function submit(event: FormEvent) {
    event.preventDefault()
    create.mutate({ name: name.trim(), type }, { onSuccess: (c) => navigate(`${CATEGORIES}/${c.id}`) })
  }
  return (
    <form className="inline-form" onSubmit={submit} aria-label="Create a category">
      <TextField value={name} onChange={setName}>
        <Label>New category</Label>
        <Input />
      </TextField>
      <Choice label="Type" options={TYPES} selected={type} onChange={setType} />
      <Button type="submit" isDisabled={!name.trim() || create.isPending}>
        Create
      </Button>
      {create.error != null && <p role="alert">Not created: {refusal(create.error)}</p>}
    </form>
  )
}
