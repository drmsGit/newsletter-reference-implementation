import type { ReactNode } from 'react'
import { Button } from 'react-aria-components'

import { HttpError } from '../api/session'

/**
 * A setting saved on purpose, with its own button (Settings: "each change is
 * saved on purpose"), and what the save did. Shared by General and the AI
 * prompts (task-372).
 */
/** What a save did, said once beside its control. */
export function Outcome({ write }: { write: { isSuccess: boolean; isError: boolean; error: unknown } }) {
  if (write.isSuccess) return <p role="status">Saved.</p>
  if (!write.isError) return null
  const error = write.error instanceof HttpError ? write.error : undefined
  return (
    <p role="alert">
      {error?.status === 403
        ? 'You do not have permission to change this.'
        : error?.detail
          ? `Not saved: ${error.detail}`
          : 'Not saved. The server refused the value.'}
    </p>
  )
}

export function Form({ children, onSave, saving, label }: {
  children: ReactNode
  onSave: () => void
  saving: boolean
  label: string
}) {
  return (
    // In a card its fields, notes and button are rows (task-372).
    <form
      className="card-rows"
      onSubmit={(event) => {
        event.preventDefault()
        onSave()
      }}
    >
      {children}
      <div>
        {/* One of several saves on the page, so not drawn as the primary action (render 33). */}
        <Button type="submit" className="btn-secondary" isDisabled={saving}>
          {saving ? 'Saving…' : label}
        </Button>
      </div>
    </form>
  )
}

