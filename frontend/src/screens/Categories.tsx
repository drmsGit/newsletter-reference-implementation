import { useState, type FormEvent } from 'react'
import {
  Button,
  Dialog,
  GridList,
  GridListItem,
  Heading,
  Input,
  Label,
  Modal,
  ModalOverlay,
  TextField,
} from 'react-aria-components'
import { useMatch, useNavigate } from 'react-router'

import { useCategories, useCategoryRelations, useCreateCategory, type Category } from '../api/resources'
import { HttpError } from '../api/session'
import BackTo from '../components/BackTo'
import Choice from '../components/Choice'
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
 *
 * v2 (task-372, render 28): column 2 of Content's drill-in, the open category
 * beside it. No search box yet: the list does not search (decision 21 is
 * TASK-390).
 */
export default function Categories() {
  const categories = useCategories()
  const relations = useCategoryRelations()
  const navigate = useNavigate()
  const openId = Number(useMatch(`${CATEGORIES}/:id`)?.params.id)
  const open = Number.isInteger(openId) ? openId : undefined
  const names = new Map((categories.data ?? []).map((c) => [c.id, c.name]))
  const parentsOf = (id: number) =>
    (relations.data ?? []).filter((r) => r.child_category_id === id).map((r) => names.get(r.parent_category_id))
  const childrenOf = (id: number) => (relations.data ?? []).filter((r) => r.parent_category_id === id).length
  const sorted = [...(categories.data ?? [])].sort((a, b) => a.type.localeCompare(b.type) || a.name.localeCompare(b.name))

  return (
    <>
      <div className="list-head">
        <BackTo to="/content" label="Content" />
        <div className="list-head__row">
          <h1>Categories</h1>
          <NewCategory />
        </div>
        <p className="muted list-note">
          The categories content is sorted into, and what a recipient&apos;s interests are counted in. They are
          shared by every brand: a change here reaches all of them.
        </p>
      </div>
      <ScreenState query={categories}>
        <GridList
          aria-label="Categories"
          className="react-aria-GridList item-list"
          items={sorted}
          // Rows are cached by item: redraw them when the links arrive, or a
          // row drawn first says "0 subcategories" for good.
          dependencies={[relations.data]}
          selectionMode="single"
          selectionBehavior="replace"
          selectedKeys={open !== undefined ? [open] : []}
          onSelectionChange={(keys) => {
            const [key] = keys === 'all' ? [] : [...keys]
            if (key !== undefined && Number(key) !== open) navigate(`${CATEGORIES}/${key}`)
          }}
          renderEmptyState={() => <p className="list-empty muted">There are no categories yet.</p>}
        >
          {(c: Category) => {
            const under = parentsOf(c.id).join(', ')
            const children = childrenOf(c.id)
            return (
              <GridListItem id={c.id} textValue={c.name} className="react-aria-GridListItem item">
                <span className="item-title">{c.name}</span>
                <span className="item-meta">
                  <span>
                    {c.type === 'main' ? 'Main' : 'Sub'}
                    {under && ` · under ${under}`}
                  </span>
                  <span>
                    {children} subcategor{children === 1 ? 'y' : 'ies'}
                  </span>
                </span>
              </GridListItem>
            )
          }}
        </GridList>
      </ScreenState>
    </>
  )
}

/** "New category" opens a dialog (task-372, decision 22; render 45). Enter creates, Esc closes. */
function NewCategory() {
  const [open, setOpen] = useState(false)
  return (
    <>
      <Button className="btn-primary" onPress={() => setOpen(true)}>
        New category
      </Button>
      <ModalOverlay isOpen={open} onOpenChange={setOpen} isDismissable className="preview-overlay">
        <Modal className="create-modal">
          <Dialog aria-labelledby="new-category-title">
            <Heading slot="title" id="new-category-title">
              New category
            </Heading>
            <CreateForm onCancel={() => setOpen(false)} />
          </Dialog>
        </Modal>
      </ModalOverlay>
    </>
  )
}

function CreateForm({ onCancel }: { onCancel: () => void }) {
  const create = useCreateCategory()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [type, setType] = useState('main')
  function submit(event: FormEvent) {
    event.preventDefault()
    if (!name.trim() || create.isPending) return
    create.mutate({ name: name.trim(), type }, { onSuccess: (c) => navigate(`${CATEGORIES}/${c.id}`) })
  }
  return (
    <form className="dialog-form" onSubmit={submit} aria-label="Create a category">
      <TextField value={name} onChange={setName} autoFocus>
        <Label>New category</Label>
        <Input />
      </TextField>
      <Choice label="Type" options={TYPES} selected={type} onChange={setType} />
      {create.error != null && <p role="alert">Not created: {refusal(create.error)}</p>}
      <div className="dialog-actions">
        <Button onPress={onCancel}>Cancel</Button>
        <Button type="submit" isDisabled={!name.trim() || create.isPending}>
          Create
        </Button>
      </div>
    </form>
  )
}
