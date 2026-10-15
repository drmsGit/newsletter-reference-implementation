import { useEffect, useRef, useState } from 'react'
import { Button, Input, Label, ListBox, ListBoxItem, Switch, Text, TextField } from 'react-aria-components'
import { Link } from 'react-router'

import {
  useBindModule,
  useContentReach,
  useContentRecord,
  useSaveCatalogueField,
  useSetOverride,
  useAttachSlot,
  useSaveModule,
  useSetHiddenFields,
  usePickerRecords,
  type ComposedModule,
  type ContentListItem,
  type ModuleManifest,
} from '../api/resources'
import CategoryChoice from '../components/CategoryChoice'
import PublishState from '../components/PublishState'
import Choice from '../components/Choice'
import { AutosaveField, SaveState, altFieldsOf, fieldError } from '../components/EditorFields'
import ScreenState from '../components/ScreenState'
import { useShortcut } from '../shortcuts/Shortcuts'
import SlotSettings from './SlotSettings'

/**
 * A catalogue-bound module in the variant editor (task-258, slice 6), as
 * ADR-186 decides it (it superseded ADR-178 on 2026-10-03):
 *
 * - Typing in a field writes an **override for this module** — the default,
 *   so approved catalogue content is never one blur away from change (point 1).
 * - "Change in catalogue" is the explicit act: one field, one edit, its reach
 *   shown first (points 2, 8). An overridden field keeps the catalogue value
 *   it covers in view (4).
 * - Reset one field, or every override on the module after a confirmation (6).
 * - Whether a send would carry the record's edits yet, with Publish (point 11,
 *   design pass D5).
 * - An optional reason, as presets or Other (9). No outcome figures (10).
 *
 * A module bound to a decision slot gets none of this (point 5).
 */
export default function CatalogueModule({
  campaignId,
  module,
  manifest,
  channel,
  reload,
  otherRecordIds,
}: {
  campaignId: number
  module: ComposedModule
  manifest: ModuleManifest
  channel: string
  reload: () => void
  /** Records the variant's other modules are bound to, for "already in this variant" (VE 1.6). */
  otherRecordIds: number[]
}) {
  if (module.decision_slot_id != null) {
    return (
      <SlotBound
        campaignId={campaignId}
        module={module}
        manifest={manifest}
        channel={channel}
        slotId={module.decision_slot_id}
        otherRecordIds={otherRecordIds}
        reload={reload}
      />
    )
  }
  if (module.content_record_id == null) {
    return (
      <Unbound
        campaignId={campaignId}
        module={module}
        manifest={manifest}
        channel={channel}
        otherRecordIds={otherRecordIds}
        reload={reload}
      />
    )
  }
  return (
    <CatalogueFields
      campaignId={campaignId}
      module={module}
      recordId={module.content_record_id}
      manifest={manifest}
      channel={channel}
      reload={reload}
      otherRecordIds={otherRecordIds}
    />
  )
}

function CatalogueFields({
  campaignId,
  module,
  recordId,
  manifest,
  channel,
  reload,
  otherRecordIds,
}: {
  campaignId: number
  module: ComposedModule
  recordId: number
  manifest: ModuleManifest
  channel: string
  reload: () => void
  otherRecordIds: number[]
}) {
  const record = useContentRecord(recordId)
  const saveField = useSaveCatalogueField(recordId, channel)
  const setOverride = useSetOverride(campaignId)
  const overrides = (module.active_override?.field_overrides ?? {}) as Record<string, unknown>
  // Content fields only: a field typed in the module is the module's own,
  // edited below and never overridden (ADR-179's 2026-10-04 addendum).
  // An image's alt field is not one of them: it is filled with a web
  // address in the image's pop-in (ADR-197 addendum 2026-10-15, the second).
  const alts = altFieldsOf(manifest.variables)
  const fields = manifest.variables.filter((v) => !v.envelope && v.source !== 'module' && !alts.has(v.name))
  const [confirmReset, setConfirmReset] = useState(false)
  const [rebinding, setRebinding] = useState(false)
  const hide = useHide(campaignId, module, manifest)

  return (
    <ScreenState query={record}>
      {record.data && (
        <>
          <p>
            Fields from{' '}
            <Link to={`/content/${recordId}`}>“{record.data.title}”</Link>.{' '}
            <Button onPress={() => setRebinding(!rebinding)}>
              {rebinding ? 'Keep this record' : 'Use another record'}
            </Button>
          </p>
          {rebinding && (
            // Closes once the new record is in: this component stays mounted
            // across the rebind (same module), so its state would keep it open.
            <BindRecord
              campaignId={campaignId}
              module={module}
              manifest={manifest}
              channel={channel}
              otherRecordIds={otherRecordIds}
              onClose={() => setRebinding(false)}
            />
          )}
          <PublishState recordId={recordId} detail={record.data} />

          <ModuleOwnFields campaignId={campaignId} module={module} manifest={manifest} />
          {fields.map((field) =>
            hide.hidden.has(field.name) ? (
              <HiddenField key={field.name} field={field} hide={hide} />
            ) : (
              <div key={field.name} className="field-shown">
                <CatalogueField
                  module={module}
                  field={field}
                  catalogue={record.data.content[field.name]}
                  catalogueAlt={field.alt ? record.data.content[field.alt] : undefined}
                  overrides={overrides}
                  setOverride={setOverride}
                  saveField={saveField}
                  recordId={recordId}
                />
                {field.hideable && <HideSwitch field={field} hide={hide} />}
              </div>
            ),
          )}
          <SaveState mutation={hide.set} reload={reload} what="the module" />

          {module.active_override && (
            <>
              <Reason
                current={module.active_override.reason ?? null}
                onChange={(reason) => setOverride.mutate({ id: module.id, reason })}
              />
              {confirmReset ? (
                <p role="group" aria-label="Reset every override on this module?">
                  {/* ADR-178 point 6: the wholesale reset is easy to fire by accident. */}
                  <Button
                    onPress={() => {
                      setConfirmReset(false)
                      setOverride.mutate({ id: module.id, unset: Object.keys(overrides) })
                    }}
                  >
                    Reset every override here
                  </Button>{' '}
                  <Button onPress={() => setConfirmReset(false)}>Keep them</Button>
                </p>
              ) : (
                <Button onPress={() => setConfirmReset(true)}>Reset all overrides on this module</Button>
              )}
            </>
          )}
          <SaveState mutation={saveField} reload={() => record.refetch()} what="the catalogue record" />
          <SaveState mutation={setOverride} reload={reload} what="the module" />
        </>
      )}
    </ScreenState>
  )
}

/** ADR-186 point 8: shown with the catalogue act, before anyone types; the list on request. */
function Reach({ recordId }: { recordId: number }) {
  const reach = useContentReach(recordId)
  const [open, setOpen] = useState(false)
  if (!reach.data) return null
  const { count, campaigns } = reach.data
  return (
    <div className="reach">
      <Text className="muted">
        Saving this changes the catalogue record for every campaign that uses it: {count} unsent
        campaign{count === 1 ? '' : 's'}.
      </Text>{' '}
      {count > 0 && (
        <Button onPress={() => setOpen(!open)}>{open ? 'Hide which' : 'Show which'}</Button>
      )}
      {open && (
        <ul>
          {campaigns.map((c) => (
            <li key={c.id}>
              <Link to={`/campaigns/${c.id}`}>{c.name}</Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/** Presets chosen with the user, 2026-10-03 (design pass D6); free text behind Other. */
const REASONS = [
  'Shorter for this send',
  'Different tone for this audience',
  'Out of date for this campaign',
  'Legal or compliance',
]

/** ADR-178 point 9: optional, one click for a preset, free text behind Other. */
function Reason({ current, onChange }: { current: string | null; onChange: (reason: string | null) => void }) {
  const isPreset = current != null && REASONS.includes(current)
  const [other, setOther] = useState(current != null && !isPreset ? current : '')
  const selected = current == null ? 'none' : isPreset ? current : 'other'
  const [showOther, setShowOther] = useState(selected === 'other')
  return (
    <div className="reason">
      <Choice
        label="Why overridden (optional)"
        options={[
          { id: 'none', name: 'No reason given' },
          ...REASONS.map((r) => ({ id: r, name: r })),
          { id: 'other', name: 'Other…' },
        ]}
        selected={showOther ? 'other' : selected}
        onChange={(id) => {
          setShowOther(id === 'other')
          if (id === 'none') onChange(null)
          else if (id !== 'other') onChange(id)
        }}
      />
      {showOther && (
        <TextField
          value={other}
          onChange={setOther}
          onBlur={() => {
            if (other.trim() && other.trim() !== current) onChange(other.trim())
          }}
        >
          <Label>Other reason</Label>
          <Input />
        </TextField>
      )}
    </div>
  )
}

/** `value`, once it has stopped changing for `ms` — so a search waits for a pause in typing. */
function useDebounced<T>(value: T, ms: number): T {
  const [settled, setSettled] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), ms)
    return () => clearTimeout(timer)
  }, [value, ms])
  return settled
}

/**
 * Choose the record a catalogue module shows (task-269), as task-263 decided
 * it (design pass, "Choosing a record for a module"; ADR-175 addendum
 * 2026-10-04):
 *
 * - It lists records before anything is typed, so a manager with only a topic
 *   in mind has something to choose from. Text matches title or description;
 *   one category narrows to records assigned to it directly, best fit first.
 * - Keyboard-first (VE): ArrowDown from the search goes into the list, arrows
 *   move, Enter uses the record, Esc closes a picker that was opened.
 * - A row says what to know before choosing, never refusing: required fields
 *   the record lacks for this module (VE 2.8), already in this variant (VE
 *   1.6), never published.
 */
function BindRecord({
  campaignId,
  module,
  manifest,
  channel,
  otherRecordIds,
  onClose,
}: {
  campaignId: number
  module: ComposedModule
  manifest: ModuleManifest
  /** The variant's channel: the picker opens on records ready for it (task-286, MW Q11). */
  channel: string
  otherRecordIds: number[]
  onClose?: () => void
}) {
  const [q, setQ] = useState('')
  const [categoryId, setCategoryId] = useState<number | null>(null)
  const [showUnready, setShowUnready] = useState(false)
  const channelTitle = channel.charAt(0).toUpperCase() + channel.slice(1)
  const records = usePickerRecords(useDebounced(q.trim(), 250), categoryId, showUnready ? null : channel)
  const bind = useBindModule(campaignId)
  const list = useRef<HTMLDivElement>(null)
  useShortcut('↓', 'From the record search, into the list of records', null)
  useShortcut('Enter', 'Use the highlighted record for this module', null)
  // Content fields this module must have, as the module declares them (ADR-177).
  // Required when shown (ADR-187 point 6): a field this module hides is not lacking.
  const hiddenHere = new Set(module.hidden_fields ?? [])
  const required = manifest.variables.filter(
    (v) => v.required && !v.envelope && v.source !== 'module' && !hiddenHere.has(v.name),
  )
  const items = records.data?.items ?? []
  return (
    <div
      className="bind"
      onKeyDownCapture={(event) => {
        // DOM containment, not React's tree: Esc in the category dropdown's
        // popover (portalled out) closes that popover, not the picker.
        if (event.key === 'Escape' && onClose && event.currentTarget.contains(event.target as Node)) {
          event.stopPropagation()
          onClose()
        }
      }}
    >
      {onClose && <CloseShortcut />}
      {module.content_record_id == null && (
        <p>Not bound to content yet. It is reported at send, never blocked.</p>
      )}
      <div className="bind__filters">
        <TextField
          value={q}
          onChange={setQ}
          autoFocus={onClose != null}
          onKeyDown={(event) => {
            if (event.key !== 'ArrowDown' || items.length === 0) return event.continuePropagation()
            list.current?.focus()
          }}
        >
          <Label>Find a record by title or description</Label>
          <Input />
        </TextField>
        <CategoryChoice selected={categoryId} onChange={setCategoryId} />
        <Switch isSelected={showUnready} onChange={setShowUnready}>
          <span className="switch__indicator" aria-hidden="true" />
          Show records not ready for {channelTitle}
        </Switch>
      </div>
      {records.data && items.length === 0 ? (
        <p className="muted">No record matches.</p>
      ) : (
        <ListBox
          ref={list}
          aria-label="Records to use"
          className="bind__results"
          items={items}
          disabledKeys={bind.isPending ? items.map((r) => r.id) : [module.content_record_id ?? -1]}
          onAction={(key) =>
            bind.mutate({ id: module.id, contentRecordId: Number(key) }, { onSuccess: () => onClose?.() })
          }
        >
          {(record) => (
            <ListBoxItem id={record.id} textValue={record.title} className="bind__record">
              <span className="bind__title">{record.title}</span>
              {record.id === module.content_record_id && <span className="muted"> · this module's record</span>}
              {record.description && <span className="bind__description muted">{record.description}</span>}
              <Notices
                record={record}
                required={required}
                inVariant={otherRecordIds.includes(record.id)}
                notReadyFor={record.ready_for.includes(channel) ? null : channelTitle}
              />
            </ListBoxItem>
          )}
        </ListBox>
      )}
      {records.data && records.data.total > items.length && (
        <p className="muted">
          Showing {items.length} of {records.data.total}. Type or choose a category to narrow them.
        </p>
      )}
      <SaveState mutation={bind} what="the module" />
    </div>
  )
}

/** Listed only where Esc does something: a picker that was opened can be closed. */
function CloseShortcut() {
  useShortcut('Esc', 'Close the record picker', null)
  return null
}

/** What to know about a record before using it here. Each one informs; none blocks (VE 1.4). */
function Notices({
  record,
  required,
  inVariant,
  notReadyFor,
}: {
  record: ContentListItem
  required: ModuleManifest['variables']
  inVariant: boolean
  /** The channel this record is not marked ready for, when it is not (ADR-174). */
  notReadyFor: string | null
}) {
  const content = record.content as Record<string, unknown>
  const missing = required.filter((v) => {
    const value = content[v.name]
    return value == null || (typeof value === 'string' && !value.trim())
  })
  const notes = [
    notReadyFor && `Not ready for ${notReadyFor}`,
    missing.length > 0 && `Lacks ${missing.map((v) => v.label ?? v.name).join(', ')} for this module`,
    inVariant && 'Already in this variant',
    record.latest_version_number == null && 'Not published yet',
  ].filter(Boolean)
  if (notes.length === 0) return null
  return <span className="bind__notices">{notes.join(' · ')}</span>
}

/**
 * One catalogue-bound field (ADR-186).
 *
 * Typing writes an override for this module — the default, because approved
 * catalogue content should not be one blur away from change (point 1). The
 * catalogue changes only through "Change in catalogue": one field, one edit,
 * with its reach shown before anything is typed, saved with an explicit
 * button, and closed afterwards (points 2, 8). Nothing stays switched on (3).
 */
function CatalogueField({
  module,
  field,
  catalogue,
  catalogueAlt,
  overrides,
  setOverride,
  saveField,
  recordId,
}: {
  module: ComposedModule
  field: ModuleManifest['variables'][number]
  catalogue: unknown
  catalogueAlt?: unknown
  overrides: Record<string, unknown>
  setOverride: ReturnType<typeof useSetOverride>
  saveField: ReturnType<typeof useSaveCatalogueField>
  recordId: number
}) {
  const label = field.label ?? field.name
  const catalogueText = typeof catalogue === 'string' ? catalogue : ''
  const overridden = field.name in overrides
  const own = overrides[field.name]
  const [catalogueDraft, setCatalogueDraft] = useState<string | null>(null)

  if (catalogueDraft !== null) {
    return (
      // Keyed apart from the field below, so React replaces the subtree rather
      // than reusing its nodes: otherwise the press that opened this lands on
      // "Save to the catalogue", which took over the button's DOM node.
      <div
        key="catalogue-edit"
        className="catalogue-edit"
        role="group"
        aria-label={`Change ${label} in the catalogue`}
      >
        <Reach recordId={recordId} />
        <TextField value={catalogueDraft} onChange={setCatalogueDraft} autoFocus>
          <Label>{label} in the catalogue</Label>
          <Input />
        </TextField>
        <Button
          isDisabled={saveField.isPending}
          onPress={() =>
            saveField.mutate(
              { [field.name]: catalogueDraft.trim() ? catalogueDraft : null },
              { onSuccess: () => setCatalogueDraft(null) },
            )
          }
        >
          Save to the catalogue
        </Button>{' '}
        <Button onPress={() => setCatalogueDraft(null)}>Cancel</Button>
        {fieldError(saveField.error, field.name) && (
          <p role="alert" className="field-error">{fieldError(saveField.error, field.name)}</p>
        )}
      </div>
    )
  }

  const changeInCatalogue = (
    <Button data-catalogue-for={field.name} onPress={() => setCatalogueDraft(catalogueText)}>
      Change {label} in catalogue
    </Button>
  )

  if (!module.overrideable) {
    // Not overridable (no manifest knowledge of the module): the catalogue
    // value is shown, and the explicit act is the only way to change it.
    return (
      <div>
        <p>
          <span className="muted">{label}:</span> {catalogueText || '—'}
        </p>
        {changeInCatalogue}
      </div>
    )
  }

  return (
    <div key="field" className={overridden ? 'overridden' : undefined}>
      <AutosaveField
        field={{ ...field, label: overridden ? `${label} — overridden here` : label }}
        value={overridden ? (typeof own === 'string' ? own : '') : catalogueText}
        alt={altText(field.alt, overrides, catalogueAlt)}
        // AutosaveField saves only a changed value, so an untouched catalogue
        // value never becomes an override. An address's alt is overridden with it.
        onSave={(next, also) => setOverride.mutate({ id: module.id, set: { [field.name]: next, ...also } })}
        // Typing that leaves the field for its own "Change in catalogue"
        // was meant for the catalogue: it goes there, and no override is
        // written on the way (task-261).
        onLeave={(draft, next) => {
          if ((next as HTMLElement | null)?.dataset?.catalogueFor !== field.name) return false
          setCatalogueDraft(draft)
          return true
        }}
        error={fieldError(setOverride.error, field.name)}
      />
      {overridden && (
        <>
          <Text className="muted">Catalogue: {catalogueText || '—'}</Text>{' '}
          <Button onPress={() => setOverride.mutate({ id: module.id, unset: [field.name] })}>
            Back to the catalogue value
          </Button>{' '}
        </>
      )}
      {changeInCatalogue}
    </div>
  )
}

/** An image's alt text as this module shows it: overridden here, or the catalogue's. */
function altText(name: string | null | undefined, overrides: Record<string, unknown>, catalogue: unknown): string {
  if (!name) return ''
  const value = name in overrides ? overrides[name] : catalogue
  return typeof value === 'string' ? value : ''
}

/**
 * A module filled by a decision slot: its settings in place (slice 7), and
 * the way back to one fixed record. Never overridable (ADR-186 point 5).
 */
function SlotBound({
  campaignId,
  module,
  manifest,
  channel,
  slotId,
  otherRecordIds,
  reload,
}: {
  campaignId: number
  module: ComposedModule
  manifest: ModuleManifest
  channel: string
  slotId: number
  otherRecordIds: number[]
  reload: () => void
}) {
  const [rebinding, setRebinding] = useState(false)
  return (
    <>
      <ModuleOwnFields campaignId={campaignId} module={module} manifest={manifest} />
      <HiddenFieldsGroup campaignId={campaignId} module={module} manifest={manifest} reload={reload} />
      <SlotSettings campaignId={campaignId} slotId={slotId} channel={channel} />
      <p className="muted">
        A slot is never overridden: one pinned value would replace every personal pick.
      </p>
      <Button onPress={() => setRebinding(!rebinding)}>
        {rebinding ? 'Keep the slot' : 'Use one content record instead'}
      </Button>
      {rebinding && (
        <BindRecord
          campaignId={campaignId}
          module={module}
          manifest={manifest}
          channel={channel}
          otherRecordIds={otherRecordIds}
          onClose={() => setRebinding(false)}
        />
      )}
    </>
  )
}

/** A catalogue module with no content yet: one record, or a slot that picks per recipient. */
function Unbound({
  campaignId,
  module,
  manifest,
  channel,
  otherRecordIds,
  reload,
}: {
  campaignId: number
  module: ComposedModule
  manifest: ModuleManifest
  channel: string
  otherRecordIds: number[]
  reload: () => void
}) {
  const attach = useAttachSlot(campaignId)
  return (
    <>
      <HiddenFieldsGroup campaignId={campaignId} module={module} manifest={manifest} reload={reload} />
      <BindRecord
        campaignId={campaignId}
        module={module}
        manifest={manifest}
        channel={channel}
        otherRecordIds={otherRecordIds}
      />
      <p>
        Or fill it per recipient:{' '}
        <Button isDisabled={attach.isPending} onPress={() => attach.mutate({ id: module.id })}>
          Personalise with a decision slot
        </Button>
      </p>
      <SaveState mutation={attach} what="the module" />
    </>
  )
}

/**
 * The fields a catalogue module types itself (ADR-179's 2026-10-04
 * addendum) — today the optional heading above it. Saved to the module, with
 * its version, and shown only when the module is: a slot that finds nothing
 * hides its heading too (ADR-086).
 */
function ModuleOwnFields({
  campaignId,
  module,
  manifest,
}: {
  campaignId: number
  module: ComposedModule
  manifest: ModuleManifest
}) {
  const save = useSaveModule(campaignId)
  const own = manifest.variables.filter((v) => v.source === 'module')
  if (own.length === 0) return null
  const data = module.module_data as Record<string, unknown>
  return (
    <div className="module-own-fields">
      {own.map((field) => (
        <AutosaveField
          key={field.name}
          field={field}
          value={typeof data[field.name] === 'string' ? (data[field.name] as string) : ''}
          onSave={(value) => save.mutate({ id: module.id, changes: { [field.name]: value.trim() ? value : null } })}
          error={fieldError(save.error, field.name)}
        />
      ))}
      <SaveState mutation={save} what="the module" />
    </div>
  )
}

/**
 * Hiding fields in this module (ADR-187, task-291): which are hidden, and a
 * toggle that sends the whole list in the manifest's order. One mutation per
 * module, so its refusals show in one place.
 */
function useHide(campaignId: number, module: ComposedModule, manifest: ModuleManifest) {
  const set = useSetHiddenFields(campaignId)
  const hidden = new Set(module.hidden_fields ?? [])
  const order = manifest.variables.filter((v) => v.hideable).map((v) => v.name)
  function toggle(name: string) {
    const next = new Set(hidden)
    if (next.has(name)) next.delete(name)
    else next.add(name)
    set.mutate({ id: module.id, hidden: order.filter((n) => next.has(n)) })
  }
  return { set, hidden, toggle }
}

type Hide = ReturnType<typeof useHide>

/** The toggle on one hideable field. Read-only while saving, so it keeps focus. */
function HideSwitch({ field, hide }: { field: ModuleManifest['variables'][number]; hide: Hide }) {
  const label = field.label ?? field.name
  const refused = fieldError(hide.set.error, field.name)
  return (
    <div className="hide-switch">
      <Switch
        isSelected={hide.hidden.has(field.name)}
        isReadOnly={hide.set.isPending}
        onChange={() => hide.toggle(field.name)}
      >
        <span className="switch__indicator" aria-hidden="true" />
        Hide {label} in this module
      </Switch>
      {refused && <p role="alert" className="field-error">{refused}</p>}
    </div>
  )
}

/**
 * A hidden field, folded: its label and why, no input — nobody edits copy
 * that will not be seen. The value is kept where it is; showing the field
 * again brings it back (ADR-187 point 7).
 */
function HiddenField({ field, hide }: { field: ModuleManifest['variables'][number]; hide: Hide }) {
  return (
    <div className="field-hidden">
      <p>
        <span>{field.label ?? field.name}</span> <span className="muted">Hidden in this module</span>
      </p>
      <HideSwitch field={field} hide={hide} />
    </div>
  )
}

/**
 * The toggles where a module's fields are not listed: a slot-filled module
 * (its values are each recipient's pick) and one not bound yet. The choice is
 * the module's, whatever fills it (ADR-187 point 3).
 */
function HiddenFieldsGroup({
  campaignId,
  module,
  manifest,
  reload,
}: {
  campaignId: number
  module: ComposedModule
  manifest: ModuleManifest
  reload: () => void
}) {
  const hide = useHide(campaignId, module, manifest)
  const hideable = manifest.variables.filter((v) => v.hideable)
  if (hideable.length === 0) return null
  return (
    <div role="group" aria-label="Fields shown in this module" className="hidden-fields">
      {hideable.map((field) => (
        <HideSwitch key={field.name} field={field} hide={hide} />
      ))}
      <SaveState mutation={hide.set} reload={reload} what="the module" />
    </div>
  )
}
