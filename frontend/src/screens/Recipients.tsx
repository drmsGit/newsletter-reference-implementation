import { useNavigate } from 'react-router'

import { useRecipients } from '../api/resources'
import DataTable, { type DataColumn } from '../components/DataTable'
import Pager, { useOffset } from '../components/Pager'
import { SearchBox, useSearch } from '../components/RecipientSearch'
import ScreenState from '../components/ScreenState'

type Row = NonNullable<ReturnType<typeof useRecipients>['data']>['items'][number]

const columns: DataColumn<Row>[] = [
  { key: 'who', header: 'Recipient', isRowHeader: true, render: (r) => r.external_id },
  {
    key: 'addresses',
    header: 'Reachable on',
    render: (r) => r.addresses.map((a) => a.channel).join(', ') || <span className="muted">—</span>,
  },
  { key: 'language', header: 'Language', render: (r) => r.language ?? '—' },
  { key: 'status', header: 'Status', render: (r) => r.status },
]

/**
 * Look one person up (task-292; Manager Workflow interview Q4.5): the list is
 * only the way in to "why did this person get this". Read-only — the CRM owns
 * the person (ADR-120).
 */
export default function Recipients() {
  const recipients = useRecipients(useOffset(), useSearch())
  const navigate = useNavigate()
  return (
    <>
      <h1>Recipients</h1>
      <SearchBox label="Find a recipient by identifier or address" />
      <ScreenState query={recipients}>
        <DataTable
          label="Recipients"
          columns={columns}
          items={recipients.data?.items ?? []}
          emptyMessage="Nobody matches."
          onRowAction={(r) => navigate(`/recipients/${r.id}`)}
        />
        <Pager page={recipients.data} />
      </ScreenState>
    </>
  )
}
