import { Button } from 'react-aria-components'
import { useSearchParams } from 'react-router'

/** Rows per page: ADR-185's default, which every paged route also uses. */
export const PAGE_SIZE = 50

/**
 * The page a screen is on, from the URL (`?offset=`), so a page survives a
 * reload, the back button steps back through pages, and a link can be shared.
 */
export function useOffset(param = 'offset'): number {
  const [params] = useSearchParams()
  return Math.max(0, Number(params.get(param) ?? 0) || 0)
}

/**
 * Newer / Older over one ADR-185 page (`{items, total, limit, offset}`).
 *
 * **The total is the server's**, counted with the same filters as the rows, so
 * "Older" is disabled exactly on the last page — not, as before the envelope
 * existed, offered whenever a page came back full and then leading to an empty
 * one. Renders nothing when everything fits on one page.
 */
export default function Pager({
  page,
  param = 'offset',
}: {
  page: { total: number; limit: number; offset: number; items: unknown[] } | undefined
  /** The address's name for this page, when two paged lists share a screen (task-372). */
  param?: string
}) {
  const [params, setParams] = useSearchParams()
  if (!page || page.total <= page.limit) return null

  function go(to: number) {
    const next = new URLSearchParams(params)
    if (to > 0) next.set(param, String(to))
    else next.delete(param)
    setParams(next)
  }

  const first = page.items.length > 0 ? page.offset + 1 : 0
  const last = page.offset + page.items.length
  return (
    <nav aria-label="Pages" className="pager">
      <Button isDisabled={page.offset === 0} onPress={() => go(Math.max(0, page.offset - page.limit))}>
        Newer
      </Button>
      <span className="muted">
        {first}–{last} of {page.total}
      </span>
      <Button isDisabled={last >= page.total} onPress={() => go(page.offset + page.limit)}>
        Older
      </Button>
    </nav>
  )
}
