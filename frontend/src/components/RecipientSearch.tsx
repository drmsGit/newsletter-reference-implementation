import { useRef, useState } from 'react'
import { Button, Input, Label, TextField } from 'react-aria-components'
import { useSearchParams } from 'react-router'

import { ShortcutHint, useShortcut } from '../shortcuts/Shortcuts'

/** The current search, from the URL (`?q=`), so it survives a reload and a link. */
export function useSearch(param = 'q'): string {
  const [params] = useSearchParams()
  return params.get(param) ?? ''
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
export function SearchBox({
  label,
  compact = false,
  param = 'q',
  pageParam = 'offset',
  shortcut = true,
}: {
  label: string
  compact?: boolean
  /** The address's names for this search and the page it resets, when a
   * screen holds two searchable lists (task-372: a list beside its details). */
  param?: string
  /** null: the list it searches is not paged. */
  pageParam?: string | null
  /** `/` jumps here. One box per screen takes it: the list's, beside its details. */
  shortcut?: boolean
}) {
  const [params, setParams] = useSearchParams()
  const [value, setValue] = useState(params.get(param) ?? '')
  const input = useRef<HTMLInputElement>(null)

  function run(q: string) {
    const next = new URLSearchParams(params)
    if (q.trim()) next.set(param, q.trim())
    else next.delete(param)
    if (pageParam) next.delete(pageParam)
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
      {shortcut && <SlashToFocus label={label} input={input} />}
      <TextField value={value} onChange={setValue} aria-label={compact ? label : undefined}>
        {/* In a list column (task-372) the label is the placeholder, and still the field's name. */}
        {!compact && (
          <Label>
            {label} {shortcut && <ShortcutHint keys="/" />}
          </Label>
        )}
        <Input ref={input} placeholder={compact ? label : undefined} aria-keyshortcuts={shortcut ? '/' : undefined} />
      </TextField>
      {/* Not the screen's primary action, so not drawn as one (render 20). */}
      <Button type="submit" className="btn-secondary">
        Search
      </Button>
      {params.get(param) && (
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

/** `/` jumps to the search on any list that has one (task-266). */
function SlashToFocus({ label, input }: { label: string; input: React.RefObject<HTMLInputElement | null> }) {
  useShortcut('/', label, () => input.current?.focus())
  return null
}
