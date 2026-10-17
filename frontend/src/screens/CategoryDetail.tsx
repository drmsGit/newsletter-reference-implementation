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
import DetailSection from '../components/DetailSection'
import Fact from '../components/Fact'
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
    // Column 3 of the categories (task-372, render 28); the list sits beside it.
    <div className="detail">
      <div className="detail-scroll">
        <ScreenState query={detail}>
          {detail.data && <Page key={detail.data.category.id} detail={detail.data} />}
        </ScreenState>
      </div>
    </div>
  )
}

export function Page({ detail }: { detail: Detail }) {
  const { category } = detail
  return (
    <>
      <div className="detail-head">
        <h2>{category.name}</h2>
      </div>
      <Rename id={category.id} name={category.name} type={category.type} />
      <Relations detail={detail} />
      <DetailSection id="category-records" title="This brand's records in it">
        <DataTable
          label="Records in this category"
          columns={RECORD_COLUMNS}
          items={detail.assigned_content.map((r) => ({ ...r, id: r.content_id }))}
          emptyMessage="No record of this brand is in this category."
        />
      </DetailSection>
      <DetailSection id="category-signal" title="Signal">
        <dl className="fact-list">
          <Fact label="Updates to interests">{detail.impact.update_count}</Fact>
          <Fact label="Total">{detail.impact.total_delta}</Fact>
          <Fact label="Average">{detail.impact.avg_delta}</Fact>
        </dl>
      </DetailSection>
      <DetailSection id="category-delete" title="Delete">
        <Delete id={category.id} name={category.name} />
      </DetailSection>
    </>
  )
}

function Rename({ id, name: current, type: currentType }: { id: number; name: string; type: string }) {
  const change = useChangeCategory(id)
  const [name, setName] = useState(current)
  const [type, setType] = useState(currentType)
  const unchanged = name.trim() === current && type === currentType
  return (
    <DetailSection id="category-name" title="Name and type">
      <form
        className="card-rows"
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
        <div>
          <Choice label="Type" options={TYPES} selected={type} onChange={setType} />
          <p className="muted field-note">Shared by every brand: a new name shows everywhere.</p>
        </div>
        <div>
          <Button type="submit" isDisabled={unchanged || !name.trim() || change.isPending}>
            Save
          </Button>
        </div>
        {change.error != null && <p role="alert">Not saved: {refusal(change.error)}</p>}
      </form>
    </DetailSection>
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
      <ul aria-label={label} className="link-list">
        {items.map((c) => (
          <li key={c.id}>
            <Link to={`${CATEGORIES}/${c.id}`}>{c.name}</Link>{' '}
            <Button className="btn-plain btn-sm" onPress={() => c.relation_id != null && remove.mutate(c.relation_id)}>
              Remove link
            </Button>
          </li>
        ))}
      </ul>
    )

  return (
    <DetailSection id="category-relations" title="Where it sits">
      <div>
        <h4 className="row-title">Under</h4>
        {list(detail.parents, 'Under')}
      </div>
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
      <div>
        <h4 className="row-title">Subcategories</h4>
        {list(detail.children, 'Subcategories')}
      </div>
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
    </DetailSection>
  )
}

/** Delete asks first; when records or links would go with it, it says how many and asks again. */
function Delete({ id, name }: { id: number; name: string }) {
  const remove = useDeleteCategory(id)
  const navigate = useNavigate()
  const [asking, setAsking] = useState(false)
  const blocked = remove.error instanceof HttpError && remove.error.status === 409
  const done = { onSuccess: () => navigate(CATEGORIES) }
  if (!asking)
    return (
      <div>
        <Button className="btn-destructive" onPress={() => setAsking(true)}>
          Delete category…
        </Button>
      </div>
    )
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
