import Choice from './Choice'
import { useCategories, useCategoryRelations, type Category, type CategoryRelation } from '../api/resources'

export type CategoryNode = { category: Category; depth: number }

/**
 * The taxonomy as one indented list, each category exactly once (task-269).
 *
 * The graph allows several parents per category and the service refuses
 * cycles, but rows written around it can hold one (the demo seed's
 * Beach <-> Family). So: roots first, each child under its first parent by
 * name, a visited set so a cycle cannot recurse, and anything no root reaches
 * listed afterwards as a root of its own rather than lost.
 */
export function categoryTree(categories: Category[], relations: CategoryRelation[]): CategoryNode[] {
  const byName = (a: Category, b: Category) => a.name.localeCompare(b.name) || a.id - b.id
  const byId = new Map(categories.map((c) => [c.id, c]))
  const children = new Map<number, Category[]>()
  const hasParent = new Set<number>()
  for (const r of relations) {
    const child = byId.get(r.child_category_id)
    if (!child || !byId.has(r.parent_category_id)) continue
    hasParent.add(child.id)
    children.set(r.parent_category_id, [...(children.get(r.parent_category_id) ?? []), child])
  }
  const out: CategoryNode[] = []
  const seen = new Set<number>()
  const visit = (category: Category, depth: number) => {
    if (seen.has(category.id)) return
    seen.add(category.id)
    out.push({ category, depth })
    for (const child of [...(children.get(category.id) ?? [])].sort(byName)) visit(child, depth + 1)
  }
  const sorted = [...categories].sort(byName)
  for (const root of sorted.filter((c) => !hasParent.has(c.id))) visit(root, 0)
  for (const rest of sorted) visit(rest, 0)
  return out
}

/**
 * One category, or any, chosen from the hierarchy (ADR-175 addendum
 * 2026-10-04): read-only, so nothing here creates or assigns a category.
 * Choosing a parent means records assigned to it directly, not its children.
 */
export default function CategoryChoice({
  selected,
  onChange,
  label = 'Category',
  noneLabel = 'Any category',
  exclude,
}: {
  selected: number | null
  onChange: (id: number | null) => void
  label?: string
  /** What choosing nothing is called: "Any category" for a filter. */
  noneLabel?: string
  /** Categories not to offer, e.g. those a record already has (task-280). */
  exclude?: ReadonlySet<number>
}) {
  const categories = useCategories()
  const relations = useCategoryRelations()
  const tree = categoryTree(categories.data ?? [], relations.data ?? []).filter(
    ({ category }) => !exclude?.has(category.id),
  )
  return (
    <Choice
      label={label}
      options={[
        { id: 'any', name: noneLabel },
        ...tree.map(({ category, depth }) => ({ id: String(category.id), name: category.name, indent: depth })),
      ]}
      selected={selected == null ? 'any' : String(selected)}
      onChange={(id) => onChange(id === 'any' ? null : Number(id))}
    />
  )
}
