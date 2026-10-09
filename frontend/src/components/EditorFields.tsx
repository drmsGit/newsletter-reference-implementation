import { useState } from 'react'
import { Button, Input, Label, Text, TextArea, TextField } from 'react-aria-components'

import type { ModuleVariable } from '../api/resources'
import { HttpError } from '../api/session'

/**
 * A field that saves when it loses focus, and only when its value changed.
 *
 * The draft follows the stored value while nobody has typed in it, and when
 * the stored value becomes the draft (its own save coming back). Typing is
 * never replaced by a refresh (task-329): if somebody else's value arrives
 * underneath it, the typing stays, a notice shows theirs, and leaving the
 * field saves nothing — the manager chooses "Save mine" or "Use theirs"
 * (decided with the user 2026-10-09; ADR-180: a person is told, not blocked).
 * Discarding a refused save is "Load their version", which remounts the page.
 *
 * `onLeave` lets the caller see where the focus went before anything is
 * saved, and take the draft elsewhere instead (return true). A field whose
 * typing was meant for another act — ADR-186's "Change in catalogue" — must
 * not save it to this one on the way there (task-261).
 */
export function AutosaveField({
  field,
  value,
  onSave,
  onLeave,
  error,
}: {
  // A module's field, or a record's (`ContentField`): what a form needs of either.
  field: Pick<ModuleVariable, 'name' | 'label' | 'type' | 'note'> & { required?: boolean }
  value: string
  onSave: (value: string) => void
  onLeave?: (draft: string, next: Element | null) => boolean
  error: string | undefined
}) {
  const [draft, setDraft] = useState(value)
  // The stored value the draft started from. Adjusted during render, not in
  // an effect, so a refresh never paints the wrong text for a frame.
  const [base, setBase] = useState(value)
  if (value !== base && (draft === base || draft === value)) {
    setDraft(value)
    setBase(value)
  }
  const conflict = value !== base
  const label = field.label ?? field.name
  const multiline = field.type === 'richtext'

  return (
    <TextField
      className="react-aria-TextField field"
      value={draft}
      onChange={setDraft}
      onBlur={(event) => {
        if (draft === value) return
        if (onLeave?.(draft, event.relatedTarget as Element | null)) return
        if (conflict) return
        onSave(draft)
      }}
      isInvalid={!!error}
    >
      <Label>
        {label}
        {field.required && <span className="muted"> (required)</span>}
      </Label>
      {multiline ? <TextArea rows={4} /> : <Input type={field.type === 'url' ? 'url' : 'text'} />}
      {multiline && (
        // VE 2.5: raw markdown, no toolbar, and the syntax said where it is typed.
        <Text slot="description" className="muted">
          **bold**, *italic*, [link](https://…), and a line starting with - for a bullet.
        </Text>
      )}
      {field.note && field.note !== label && (
        <Text slot="description" className="muted">
          {field.note}
        </Text>
      )}
      {field.required && !draft.trim() && !error && (
        // Shown here and only here (VE 2.2): a manager decides when it is ready.
        <Text slot="description" className="muted">
          Empty — needed before this is sent.
        </Text>
      )}
      {conflict && (
        <div role="alert" className="field-error">
          <p>
            Somebody else changed this while you were typing. Theirs: <q>{value}</q>. Yours is not saved
            until you choose.
          </p>
          <Button
            onPress={() => {
              setBase(value)
              onSave(draft)
            }}
          >
            Save mine
          </Button>{' '}
          <Button onPress={() => setDraft(value) /* base follows on the next render */}>Use theirs</Button>
        </div>
      )}
      {error && (
        <p role="alert" className="field-error">
          {error}
        </p>
      )}
    </TextField>
  )
}

export function fieldError(error: unknown, name: string): string | undefined {
  return error instanceof HttpError ? error.fields[name] : undefined
}

/**
 * What a write ended in, in place: a stale save (409) offers a reload, a
 * permission refusal says so, anything else shows the server's reason.
 * Per-field errors (422) are shown on their fields, not repeated here.
 */
export function SaveState({
  mutation,
  what,
  reload,
}: {
  mutation: { isError: boolean; error: unknown; reset: () => void }
  what: string
  reload?: () => void
}) {
  if (!mutation.isError) return null
  const error = mutation.error instanceof HttpError ? mutation.error : undefined
  if (error && Object.keys(error.fields).length > 0) return null
  return (
    <p role="alert">
      {error?.status === 409 ? (
        <>
          Somebody changed {what} after you loaded it, so your change was not saved.{' '}
          <Button
            onPress={() => {
              mutation.reset()
              reload?.()
            }}
          >
            Load their version
          </Button>
        </>
      ) : error?.status === 403 ? (
        `You do not have permission to change ${what}.`
      ) : (
        `Not saved: ${error?.detail ?? `${what} could not be changed.`}`
      )}
    </p>
  )
}

