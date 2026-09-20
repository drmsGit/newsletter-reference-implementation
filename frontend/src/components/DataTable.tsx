import type { ReactNode } from 'react'
import { Cell, Column, Row, Table, TableBody, TableHeader } from 'react-aria-components'

export type DataColumn<T> = {
  /** Stable identity for the column, and its React key. */
  key: string
  header: string
  render: (item: T) => ReactNode
  /**
   * The column that names the row.
   *
   * A screen reader announces this cell when the user moves between rows, so
   * without one every row is read as a list of values with nothing saying which
   * record they belong to. Exactly one column per table should set it.
   */
  isRowHeader?: boolean
}

type Props<T> = {
  /**
   * What this table is, for a screen reader.
   *
   * Required rather than optional on purpose: React Aria will warn without it,
   * and a table announced only as "table" is the most common accessibility
   * defect in an admin interface.
   */
  label: string
  columns: DataColumn<T>[]
  items: T[]
  emptyMessage: string
  onRowAction?: (item: T) => void
}

/**
 * A list of records, rendered as a real table.
 *
 * **This component is the reason ADR-173 chose React Aria.** Radix and Base UI
 * have no table primitive, and a manager client is mostly lists -- campaigns,
 * content, audiences, approvals. What arrives with it is keyboard navigation
 * between rows and cells, the ARIA grid roles that make the structure
 * announceable, and row actions reachable without a mouse.
 *
 * It is deliberately thin. It owns the accessible shape and the empty state,
 * and holds no opinion about sorting, filtering or pagination -- none of which
 * any screen needs yet, and each of which is easier to add once something
 * actually asks for it.
 */
export default function DataTable<T extends { id: number }>({
  label,
  columns,
  items,
  emptyMessage,
  onRowAction,
}: Props<T>) {
  const byId = new Map(items.map((item) => [item.id, item]))

  return (
    <Table
      aria-label={label}
      selectionMode="none"
      onRowAction={
        onRowAction
          ? (key) => {
              const item = byId.get(Number(key))
              if (item) onRowAction(item)
            }
          : undefined
      }
    >
      <TableHeader>
        {columns.map((column) => (
          <Column key={column.key} id={column.key} isRowHeader={column.isRowHeader}>
            {column.header}
          </Column>
        ))}
      </TableHeader>
      <TableBody renderEmptyState={() => <span className="muted">{emptyMessage}</span>}>
        {items.map((item) => (
          <Row key={item.id} id={item.id}>
            {columns.map((column) => (
              <Cell key={column.key}>{column.render(item)}</Cell>
            ))}
          </Row>
        ))}
      </TableBody>
    </Table>
  )
}
