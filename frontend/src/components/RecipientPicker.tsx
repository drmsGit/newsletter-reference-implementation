import { useState } from 'react'
import { Button, Input, Label, TextField } from 'react-aria-components'

import { useRecipientSearch } from '../api/resources'

export type PickedRecipient = { id: number; label: string; externalId: string }

/**
 * Find one recipient by identifier or address, and choose them. The search is
 * the server's (part-match, any case), ten at a time.
 *
 * Taken out of the preview (task-297) so the audience editor's "add a person"
 * names people the same way the preview does.
 */
export default function RecipientPicker({
  label,
  onChoose,
}: {
  label: string
  onChoose: (recipient: PickedRecipient) => void
}) {
  const [q, setQ] = useState('')
  const found = useRecipientSearch(q)
  return (
    <div className="recipient-choice">
      <TextField value={q} onChange={setQ}>
        <Label>{label}</Label>
        <Input />
      </TextField>
      {q.trim() && found.data && (
        <ul className="bind__results">
          {found.data.items.map((r) => (
            <li key={r.id}>
              <Button onPress={() => onChoose({ id: r.id, label: r.email || r.external_id, externalId: r.external_id })}>
                {r.email || r.external_id}
              </Button>
            </li>
          ))}
          {found.data.items.length === 0 && <li className="muted">Nobody matches.</li>}
        </ul>
      )}
    </div>
  )
}
