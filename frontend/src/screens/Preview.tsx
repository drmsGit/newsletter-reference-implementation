import { useState } from 'react'
import { Button, Dialog, Heading, Modal, ModalOverlay } from 'react-aria-components'

import {
  useRenderedVariant,
  type ModuleManifest,
  type ModuleState,
} from '../api/resources'
import RecipientPicker from '../components/RecipientPicker'
import ScreenState from '../components/ScreenState'
import { ShortcutHint, useShortcut } from '../shortcuts/Shortcuts'

/**
 * The variant editor's preview (task-265): a collapsed bar that says what the
 * render found, and an overlay with the render itself (Variant Editor
 * interview 2.1).
 *
 * **It needs no render button.** Every field saves on blur (design pass D1)
 * and every save re-reads the composition, whose update time keys the render,
 * so the bar is always about what is saved now.
 *
 * **It is a sketch, and says so** (4.2, 4.3): it shows unpublished edits, it
 * reads existing decisions rather than making any, and when a named recipient
 * has no pick of their own it says the generic one is shown. A test send is
 * what shows what will ship; the approver's proof is the snapshot (4.1).
 */
export default function PreviewBar({
  variantId,
  variantName,
  stamp,
  byName,
}: {
  variantId: number
  variantName: string
  stamp: number
  byName: Map<string, ModuleManifest>
}) {
  const [open, setOpen] = useState(false)
  useShortcut('p', 'Open the preview', () => setOpen(true))
  const [recipient, setRecipient] = useState<{ id: number; label: string } | null>(null)
  const render = useRenderedVariant(variantId, recipient?.id ?? null, stamp)
  const findings = summarise(render.data?.modules ?? [])

  return (
    <section className="preview-bar" aria-label="Preview">
      <span className={findings.marked ? 'preview-bar__findings preview-bar__findings--marked' : 'preview-bar__findings'}>
        {render.isError
          ? 'The preview could not be rendered.'
          : render.isPending
            ? 'Rendering…'
            : findings.text}
      </span>
      <Button onPress={() => setOpen(true)}>
        Open preview <ShortcutHint keys="p" />
      </Button>
      <ModalOverlay isOpen={open} onOpenChange={setOpen} isDismissable className="preview-overlay">
        <Modal className="preview-modal">
          <Dialog aria-label={`Preview of ${variantName}`}>
            <div className="preview-head">
              <Heading slot="title">Preview of {variantName}</Heading>
              <Button onPress={() => setOpen(false)}>Close</Button>
            </div>
            <p className="muted">
              A preview shows what is saved now, unpublished edits included. A test send shows what
              will actually be sent.
            </p>
            <RecipientChoice recipient={recipient} onChange={setRecipient} />
            <ScreenState query={render}>
              {render.data && (
                <div className="preview-body">
                  <ModuleStates modules={render.data.modules ?? []} byName={byName} named={recipient != null} />
                  {render.data.artifact_body ? (
                    // No scripts, no same-origin access: the document is the
                    // email as rendered, shown and nothing more.
                    <iframe
                      className="preview-frame"
                      title={`Rendered email: ${variantName}`}
                      sandbox=""
                      srcDoc={render.data.artifact_body}
                    />
                  ) : (
                    <dl className="facts">
                      {Object.entries(render.data.fields ?? {}).map(([key, value]) => (
                        <div key={key} style={{ display: 'contents' }}>
                          <dt>{key}</dt>
                          <dd>{typeof value === 'string' ? value : JSON.stringify(value)}</dd>
                        </div>
                      ))}
                    </dl>
                  )}
                </div>
              )}
            </ScreenState>
          </Dialog>
        </Modal>
      </ModalOverlay>
    </section>
  )
}

/**
 * The one line the collapsed bar shows. Only "finds nothing" is marked: it
 * is the only state that means "your rule is wrong", and the only one that
 * otherwise ships as a silently shorter email (4.4).
 */
function summarise(modules: ModuleState[]): { text: string; marked: boolean } {
  const nothing = modules.filter((m) => m.slot_state === 'finds_nothing').length
  const unpublished = modules.filter((m) => m.unpublished_changes).length
  const empty = modules.reduce((n, m) => n + (m.missing_required?.length ?? 0), 0)
  const parts = [
    nothing && `${nothing} slot${nothing === 1 ? '' : 's'} find${nothing === 1 ? 's' : ''} nothing`,
    unpublished && `${unpublished} record${unpublished === 1 ? '' : 's'} with unpublished edits`,
    empty && `${empty} required field${empty === 1 ? '' : 's'} empty`,
  ].filter(Boolean)
  return { text: parts.length ? parts.join(' · ') : 'Nothing to flag.', marked: nothing > 0 }
}

/** Each module's state, in order (task-227). */
function ModuleStates({
  modules,
  byName,
  named,
}: {
  modules: ModuleState[]
  byName: Map<string, ModuleManifest>
  named: boolean
}) {
  return (
    <ol className="module-states">
      {modules.map((m) => {
        const label = byName.get(m.module_type)?.label ?? m.module_type
        return (
          <li key={m.module_id} className={m.slot_state === 'finds_nothing' ? 'module-state--marked' : undefined}>
            <strong>{label}</strong> <span className="muted">· {describe(m, named)}</span>
            {(m.missing_required ?? []).length > 0 && (
              <span className="muted"> · empty: {(m.missing_required ?? []).join(', ')}</span>
            )}
          </li>
        )
      })}
    </ol>
  )
}

function describe(m: ModuleState, named: boolean): string {
  switch (m.kind) {
    case 'slot':
      if (m.slot_state === 'finds_nothing')
        return 'finds nothing — its rule matches no content, so it will be hidden. Widen the rule.'
      if (m.slot_state === 'not_run') return 'not run yet — shows nothing until the decision runs'
      if (m.slot_state === 'per_recipient')
        return 'picks per recipient — name a recipient above to see their pick'
      return m.generic_pick && named
        ? 'the generic pick — this recipient has no pick of their own yet'
        : 'picked'
    case 'record':
      return m.unpublished_changes ? 'shows unpublished edits — a send still uses the published version' : 'from the catalogue'
    case 'unbound':
      return 'no content yet — not shown'
    case 'unknown':
      return 'not a module of this channel — not shown'
    default:
      return 'typed in'
  }
}

/** Name a recipient for the preview, or go back to the generic one (4.2). */
function RecipientChoice({
  recipient,
  onChange,
}: {
  recipient: { id: number; label: string } | null
  onChange: (recipient: { id: number; label: string } | null) => void
}) {
  if (recipient) {
    return (
      <p>
        For <strong>{recipient.label}</strong>.{' '}
        <Button onPress={() => onChange(null)}>Generic preview</Button>
      </p>
    )
  }
  return <RecipientPicker label="Preview for a recipient (optional)" onChoose={({ id, label }) => onChange({ id, label })} />
}
