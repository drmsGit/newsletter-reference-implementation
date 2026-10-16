import { useState } from 'react'
import { Button, Input, Label, Menu, MenuItem, MenuTrigger, Popover, Text, TextArea, TextField } from 'react-aria-components'

import { useExpressions, type ModuleVariable } from '../api/resources'
import { HttpError } from '../api/session'
import ImageField from './ImageField'

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
  alt,
  personalise = false,
  error,
}: {
  // A module's field, or a record's (`ContentField`): what a form needs of either.
  field: Pick<ModuleVariable, 'name' | 'label' | 'type' | 'note'> & { required?: boolean; alt?: string | null }
  value: string
  /** `also` carries the image's paired alt field, saved in the same write. */
  onSave: (value: string, also?: Record<string, string>) => void
  /** An image field's paired alt value (see `altFieldsOf`). */
  alt?: string
  /** Offer the brand's entries ("Personalise…", ADR-199): only on texts
   * that take them, never a link, an image or a title. */
  personalise?: boolean
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
  // Where the caret was, so an entry goes in there rather than at the end.
  const [caret, setCaret] = useState<number | null>(null)
  const remember = (event: { currentTarget: HTMLInputElement | HTMLTextAreaElement }) =>
    setCaret(event.currentTarget.selectionStart)

  // An image is picked, not typed (task-112; ADR-197): a pick saves at once.
  if (field.type === 'image') {
    const altName = field.alt
    return (
      <ImageField
        label={label}
        value={value}
        alt={altName ? (alt ?? '') : undefined}
        onChange={(next, nextAlt) =>
          altName && nextAlt !== undefined ? onSave(next, { [altName]: nextAlt }) : onSave(next)
        }
        required={field.required}
        error={error}
      />
    )
  }

  const text = (
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
      {multiline ? (
        <TextArea rows={4} onSelect={remember} onKeyUp={remember} />
      ) : (
        <Input type={field.type === 'url' ? 'url' : 'text'} onSelect={remember} onKeyUp={remember} />
      )}

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
  if (!personalise || field.type === 'url' || conflict) return text
  return (
    <>
      {text}
      {/* An entry goes in at the caret and is saved at once, like a picked
          image: the press took the focus, so no blur will save it. */}
      <Personalise
        onInsert={(token) => {
          const at = caret ?? draft.length
          const next = draft.slice(0, at) + token + draft.slice(at)
          setDraft(next)
          setCaret(at + token.length)
          onSave(next)
        }}
      />
    </>
  )
}

/** "Personalise…": the brand's entries, by label, to put into a text. */
function Personalise({ onInsert }: { onInsert: (token: string) => void }) {
  const dictionary = useExpressions()
  const entries = dictionary.data?.items ?? []
  if (entries.length === 0) return null
  return (
    <MenuTrigger>
      <Button className="personalise">Personalise…</Button>
      <Popover>
        <Menu aria-label="Insert a personalisation" onAction={(name) => onInsert(`{{${String(name)}}}`)}>
          {entries.map((entry) => (
            <MenuItem key={entry.name} id={entry.name} textValue={entry.label}>
              {entry.label} <span className="muted">{`{{${entry.name}}}`}</span>
            </MenuItem>
          ))}
        </Menu>
      </Popover>
    </MenuTrigger>
  )
}

/**
 * The fields that hold an image's alt text (ADR-197 addendum 2026-10-15, the
 * second): filled with a web address in the image's pop-in, never shown as a
 * form field of their own.
 */
export function altFieldsOf(fields: { alt?: string | null }[]): Set<string> {
  return new Set(fields.flatMap((f) => (f.alt ? [f.alt] : [])))
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

