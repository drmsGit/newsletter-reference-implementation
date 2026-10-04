import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { Button, Dialog, Heading, Modal, ModalOverlay } from 'react-aria-components'

/**
 * Keyboard shortcuts and the overview that lists them (task-266).
 *
 * The client is keyboard-first (Variant Editor interview, Cluster 1): a
 * manager moving through a queue works by keys, and an overview is what makes
 * the keys discoverable at all. **One registry**: every shortcut registers
 * here with its description, the overview lists what is registered, and so it
 * cannot drift from what the keys do. A screen's shortcuts register while the
 * screen is mounted, so the overview shows the ones that apply right now.
 *
 * Keys are written as a space-separated sequence: `"g c"` is g, then c within
 * a second; `"?"` and `"/"` are single keys. Nothing fires while the person is
 * typing in a field — a shortcut that steals a letter from a headline is a
 * bug, not a feature. Not configurable this round.
 */

export type Group = 'Global' | 'Go to' | 'This screen'

type Registration = {
  id: number
  keys: string
  description: string
  group: Group
  /** Null for an entry handled elsewhere and only listed here (Alt+↑ in the stack). */
  handler: (() => void) | null
}

type Registry = {
  register: (entry: Omit<Registration, 'id'>) => () => void
}

const ShortcutsContext = createContext<Registry | null>(null)

const SEQUENCE_TIMEOUT_MS = 1000

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return (
    target.isContentEditable ||
    target.tagName === 'INPUT' ||
    target.tagName === 'TEXTAREA' ||
    target.tagName === 'SELECT'
  )
}

export function ShortcutsProvider({ children }: { children: ReactNode }) {
  const [entries, setEntries] = useState<Registration[]>([])
  const [open, setOpen] = useState(false)
  const entriesRef = useRef<Registration[]>([])
  entriesRef.current = entries
  const pending = useRef<{ key: string; at: number } | null>(null)
  const nextId = useRef(1)

  const registry = useRef<Registry>({
    register(entry) {
      const id = nextId.current++
      setEntries((all) => [...all, { ...entry, id }])
      return () => setEntries((all) => all.filter((e) => e.id !== id))
    },
  }).current

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey) return
      if (isTyping(event.target)) return
      const key = event.key
      if (key === '?') {
        event.preventDefault()
        setOpen(true)
        return
      }
      const now = Date.now()
      const prefix = pending.current && now - pending.current.at < SEQUENCE_TIMEOUT_MS ? pending.current.key : null
      const candidates = entriesRef.current.filter((e) => e.handler)
      const sequence = prefix ? `${prefix} ${key}` : key
      const exact = candidates.find((e) => e.keys === sequence)
      if (exact) {
        event.preventDefault()
        pending.current = null
        exact.handler?.()
        return
      }
      // The first key of a sequence, held until the second arrives.
      if (candidates.some((e) => e.keys.startsWith(`${key} `))) {
        pending.current = { key, at: now }
        return
      }
      pending.current = null
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  return (
    <ShortcutsContext.Provider value={registry}>
      {children}
      <ShortcutsOverlay open={open} onOpenChange={setOpen} entries={entries} />
    </ShortcutsContext.Provider>
  )
}

/**
 * Register a shortcut while the calling component is mounted. Without a
 * provider (a screen rendered on its own, as in its tests) this does nothing.
 */
export function useShortcut(keys: string, description: string, handler: (() => void) | null, group: Group = 'This screen') {
  const registry = useContext(ShortcutsContext)
  const latest = useRef(handler)
  latest.current = handler
  useEffect(() => {
    if (!registry) return
    return registry.register({
      keys,
      description,
      group,
      handler: handler ? () => latest.current?.() : null,
    })
    // `handler`'s identity changes every render; `latest` carries the current one.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [registry, keys, description, group, handler === null])
}

const ORDER: Group[] = ['Global', 'Go to', 'This screen']

function ShortcutsOverlay({
  open,
  onOpenChange,
  entries,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  entries: Registration[]
}) {
  const all: Registration[] = [
    { id: 0, keys: '?', description: 'Show these shortcuts', group: 'Global', handler: null },
    ...entries,
  ]
  return (
    <ModalOverlay isOpen={open} onOpenChange={onOpenChange} isDismissable className="preview-overlay">
      <Modal className="shortcuts-modal">
        <Dialog aria-label="Keyboard shortcuts">
          <div className="preview-head">
            <Heading slot="title">Keyboard shortcuts</Heading>
            <Button onPress={() => onOpenChange(false)}>Close</Button>
          </div>
          {ORDER.map((group) => {
            const rows = all.filter((e) => e.group === group)
            if (rows.length === 0) return null
            return (
              <section key={group} aria-label={group}>
                <h3>{group}</h3>
                <dl className="shortcuts">
                  {rows.map((e) => (
                    <div key={e.id} style={{ display: 'contents' }}>
                      <dt>
                        {e.keys.split(' ').map((k, i) => (
                          <span key={i}>
                            {i > 0 && <span className="muted"> then </span>}
                            <kbd>{k}</kbd>
                          </span>
                        ))}
                      </dt>
                      <dd>{e.description}</dd>
                    </div>
                  ))}
                </dl>
              </section>
            )
          })}
        </Dialog>
      </Modal>
    </ModalOverlay>
  )
}
