import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import DataTable, { type DataColumn } from './DataTable'
import { renderWithProviders } from '../test-utils'

type Row = { id: number; name: string }

const columns: DataColumn<Row>[] = [
  { key: 'name', header: 'Name', isRowHeader: true, render: (r) => r.name },
]

describe('the data table', () => {
  it('renders a real table with an accessible name', () => {
    /**
     * A table announced only as "table" is the most common accessibility defect
     * in an admin interface, which is why `label` is required rather than
     * optional. This asserts the name reaches the accessibility tree.
     */
    renderWithProviders(
      <DataTable
        label="Campaigns"
        columns={columns}
        items={[{ id: 1, name: 'Spring launch' }]}
        emptyMessage="Nothing here."
      />,
    )

    expect(screen.getByRole('grid', { name: 'Campaigns' })).toBeInTheDocument()
    expect(screen.getByText('Spring launch')).toBeInTheDocument()
  })

  it('shows the empty message rather than an empty table', () => {
    renderWithProviders(
      <DataTable label="Campaigns" columns={columns} items={[]} emptyMessage="Nothing here." />,
    )

    expect(screen.getByText('Nothing here.')).toBeInTheDocument()
  })
})
