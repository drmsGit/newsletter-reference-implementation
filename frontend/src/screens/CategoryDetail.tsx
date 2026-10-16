import { useState } from 'react'
import { Button, Input, Label, TextField } from 'react-aria-components'
import { Link, useNavigate, useParams } from 'react-router'

import {
  useAddCategoryRelation,
  useCategories,
  useCategoryDetail,
  useChangeCategory,
  useDeleteCategory,
  useRemoveCategoryRelation,
  type CategoryDetail as Detail,
} from '../api/resources'
import { HttpError } from '../api/session'
import Choice from '../components/Choice'
import { figureColumns } from '../components/ContentFigures'
import DataTable, { type DataColumn } from '../components/DataTable'
import ScreenState from '../components/ScreenState'
import { CATEGORIES, TYPES, refusal } from './Categories'

type Record = Detail['assigned_content'][number] & { id: number }

const RECORD_COLUMNS: DataColumn<Record>[] = [
  { key: 'title', header: 'Record', isRowHeader: true, render: (r) => <Link to={`/content/${r.content_id}`}>{r.title}</Link> },
  { key: 'score', header: 'Fit (1–10)', render: (r) => String(r.score ?? '—') },
  ...figureColumns<Record>((r) => r.figures),
]

/**
 * One category (task-359): where it sits, this brand's records in it with
 * how each did, and the signal it carries for this brand's audience. The
 * category and its relations are shared by every brand (ADR-150).
 */
export default function CategoryDetail() {
  const { id } = useParams()
  const detail = useCategoryDetail(Number(id))
  return (
    <ScreenState query={detail}>
      {detail.data && <Page key={detail.data.category.id} detail={detail.data} />}
    </ScreenState>
  )
}

export function Page({ detail }: { detail: Detail }) {
  const { category } = detail
  return (
    <>
      <p>
        <Link to={CATEGORIES}>← Categories</Link>
      </p>
      <h1>{category.name}</h1>
      <Rename id={category.id} name={category.name} type={category.type} />
      <Relations detail={detail} />
      <section aria-labelledby="category-records">
        <h2 id="category-records">This brand's records in it</h2>
        <DataTable
          label="Records in this category"
          columns={RECORD_COLUMNS}
          items={detail.assigned_content.map((r) => ({ ...r, id: r.content_id }))}
          emptyMessage="No record of this brand is in this category."
        />
      </section>
      <section aria-labelledby="category-signal">
        <h2 id="category-signal">Signal</h2>
        <dl className="facts">
          <dt>Updates to interests</dt>
          <dd>{detail.impact.update_count}</dd>
          <dt>Total</dt>
          <dd>{detail.impact.total_delta}</dd>
          <dt>Average</dt>
          <dd>{detail.impact.avg_delta}</dd>
        </dl>
      </section>
      <Delete id={category.id} name={category.name} />
    </>
  )
}

function Rename({ id, name: current, type: currentType }: { id: number; name: string; type: string }) {
  const change = useChangeCategory(id)
  const [name, setName] = useState(current)
  const [type, setType] = useState(currentType)
  const unchanged = name.trim() === current && type === currentType
  return (
    <form
      className="inline-form"
      aria-label="Name and type"
      onSubmit={(event) => {
        event.preventDefault()
        change.mutate({ name: name.trim(), type })
      }}
    >
      <TextField value={name} onChange={setName}>
        <Label>Name</Label>
        <Input />
      </TextField>
      <Choice label="Type" options={TYPES} selected={type} onChange={setType} />
      <Button type="submit" isDisabled={unchanged || !name.trim() || change.isPending}>
        Save
      </Button>
      <span className="muted"> Shared by every brand: a new name shows everywhere.</span>
      {change.error != null && <p role="alert">Not saved: {refusal(change.error)}</p>}
    </form>
  )
}

function Relations({ detail }: { detail: Detail }) {
  const categories = useCategories()
  const add = useAddCategoryRelation()
  const remove = useRemoveCategoryRelation()
  const self = detail.category.id
  const linked = new Set([self, ...detail.parents.map((p) => p.id), ...detail.children.map((c) => c.id)])
  const others = (categories.data ?? [])
    .filter((c) => !linked.has(c.id))
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((c) => ({ id: String(c.id), name: c.name }))
  const [parent, setParent] = useState('')
  const [child, setChild] = useState('')
  const error = add.error ?? remove.error

  const list = (items: Detail['parents'], label: string) =>
    items.length === 0 ? (
      <p className="muted">None.</p>
    ) : (
      <ul aria-label={label}>
        {items.map((c) => (
          <li key={c.id}>
            <Link to={`${CATEGORIES}/${c.id}`}>{c.name}</Link>{' '}
            <Button onPress={() => c.relation_id != null && remove.mutate(c.relation_id)}>Remove link</Button>
          </li>
        ))}
      </ul>
    )

  return (
    <section aria-labelledby="category-relations">
      <h2 id="category-relations">Where it sits</h2>
      <h3>Under</h3>
      {list(detail.parents, 'Under')}
      <div className="inline-form">
        <Choice label="Put it under" options={others} selected={parent} onChange={setParent}
          placeholder="Choose a category" />
        <Button
          isDisabled={!parent || add.isPending}
          onPress={() => add.mutate({ parent_category_id: Number(parent), child_category_id: self }, { onSuccess: () => setParent('') })}
        >
          Add
        </Button>
      </div>
      <h3>Subcategories</h3>
      {list(detail.children, 'Subcategories')}
      <div className="inline-form">
        <Choice label="Add a subcategory" options={others} selected={child} onChange={setChild}
          placeholder="Choose a category" />
        <Button
          isDisabled={!child || add.isPending}
          onPress={() => add.mutate({ parent_category_id: self, child_category_id: Number(child) }, { onSuccess: () => setChild('') })}
        >
          Add
        </Button>
      </div>
      {error != null && <p role="alert">Not changed: {refusal(error)}</p>}
    </section>
  )
}

/** Delete asks first; when records or links would go with it, it says how many and asks again. */
function Delete({ id, name }: { id: number; name: string }) {
  const remove = useDeleteCategory(id)
  const navigate = useNavigate()
  const [asking, setAsking] = useState(false)
  const blocked = remove.error instanceof HttpError && remove.error.status === 409
  const done = { onSuccess: () => navigate(CATEGORIES) }
  if (!asking) return <Button onPress={() => setAsking(true)}>Delete category…</Button>
  return (
    <div role="group" aria-label={`Delete ${name}?`}>
      {blocked ? (
        <>
          <p role="alert">
            {name} still has records or links to other categories. Deleting it removes those too, for every
            brand.
          </p>
          <Button onPress={() => remove.mutate(true, done)}>Delete it with them</Button>{' '}
        </>
      ) : (
        <>
          <p>Delete {name} for every brand?</p>
          <Button onPress={() => remove.mutate(false, done)}>Delete {name}</Button>{' '}
        </>
      )}
      <Button
        onPress={() => {
          setAsking(false)
          remove.reset()
        }}
      >
        Keep it
      </Button>
      {remove.error != null && !blocked && <p role="alert">Not deleted: {refusal(remove.error)}</p>}
    </div>
  )
}
