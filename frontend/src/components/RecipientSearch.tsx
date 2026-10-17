import { useRef, useState } from 'react'
import { Button, Input, Label, TextField } from 'react-aria-components'
import { useSearchParams } from 'react-router'

import { ShortcutHint, useShortcut } from '../shortcuts/Shortcuts'

/** The current search, from the URL (`?q=`), so it survives a reload and a link. */
export function useSearch(): string {
  const [params] = useSearchParams()
  return params.get('q') ?? ''
}

/**
 * Find a recipient by identifier or address (2026-10-03).
 *
 * An audience's reach and a send's recipients show a sample of twenty, not a
 * paged list -- decided with the user: a manager looking for someone specific
 * has who they are looking for, and searches. The match itself is the
 * server's (`recipients/search.py`, part-match, any case), so this sends the
 * words and shows what comes back. Runs on Enter or Search, not per keystroke.
 */
export default function RecipientSearch() {
  return <SearchBox label="Find a recipient (identifier or address)" />
}

/**
 * A search box over one list, held in the URL as `?q=`. Running a search starts
 * from the first page again: page 3 of the old results means nothing for the
 * new ones. Used for recipients above, and for content, campaign and audience
 * names (2026-10-03).
 */
export function SearchBox({ label, compact = false }: { label: string; compact?: boolean }) {
  const [params, setParams] = useSearchParams()
  const [value, setValue] = useState(params.get('q') ?? '')
  const input = useRef<HTMLInputElement>(null)
  // / jumps to the search on any list that has one (task-266).
  useShortcut('/', label, () => input.current?.focus())

  function run(q: string) {
    const next = new URLSearchParams(params)
    if (q.trim()) next.set('q', q.trim())
    else next.delete('q')
    next.delete('offset')
    setParams(next)
  }

  return (
    <form
      className={compact ? 'filters search-compact' : 'filters'}
      role="search"
      onSubmit={(event) => {
        event.preventDefault()
        run(value)
      }}
    >
      <TextField value={value} onChange={setValue} aria-label={compact ? label : undefined}>
        {/* In a list column (task-372) the label is the placeholder, and still the field's name. */}
        {!compact && (
          <Label>
            {label} <ShortcutHint keys="/" />
          </Label>
        )}
        <Input ref={input} placeholder={compact ? label : undefined} />
      </TextField>
      {/* Not the screen's primary action, so not drawn as one (render 20). */}
      <Button type="submit" className="btn-secondary">
        Search
      </Button>
      {params.get('q') && (
        <Button
          onPress={() => {
            setValue('')
            run('')
          }}
        >
          Clear
        </Button>
      )}
    </form>
  )
}
