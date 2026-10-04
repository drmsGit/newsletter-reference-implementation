import { describe, expect, it } from 'vitest'

import { categoryTree } from './CategoryChoice'

const c = (id: number, name: string) => ({ id, name, type: 'main' })
const r = (parent: number, child: number) => ({
  id: parent * 100 + child, parent_category_id: parent, child_category_id: child, relation_type: 'parent_child',
  created_at: '2026-10-04T10:00:00Z',
})
const shape = (tree: ReturnType<typeof categoryTree>) => tree.map((n) => `${'  '.repeat(n.depth)}${n.category.name}`)

describe('categoryTree (task-269)', () => {
  it('nests children under their parent, both sorted by name', () => {
    const tree = categoryTree(
      [c(1, 'Nature'), c(2, 'City'), c(3, 'Hiking'), c(4, 'Forest')],
      [r(1, 3), r(1, 4)],
    )
    expect(shape(tree)).toEqual(['City', 'Nature', '  Forest', '  Hiking'])
  })

  it('lists a category with two parents once, under the first by name', () => {
    const tree = categoryTree([c(1, 'Nature'), c(2, 'Family'), c(3, 'Camping')], [r(1, 3), r(2, 3)])
    expect(shape(tree)).toEqual(['Family', '  Camping', 'Nature'])
  })

  it('survives a cycle no root reaches, and loses nothing', () => {
    // The demo seed writes Beach -> Family and Family -> Beach directly.
    const tree = categoryTree([c(1, 'Beach'), c(2, 'Family'), c(3, 'City')], [r(1, 2), r(2, 1)])
    expect(shape(tree)).toEqual(['City', 'Beach', '  Family'])
  })

  it('ignores a relation to a category it was not given', () => {
    expect(shape(categoryTree([c(1, 'Beach')], [r(9, 1)]))).toEqual(['Beach'])
  })
})
