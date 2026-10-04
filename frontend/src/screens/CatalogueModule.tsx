import { useState } from 'react'
import { Button, Input, Label, Text, TextField } from 'react-aria-components'
import { Link } from 'react-router'

import {
  useBindModule,
  useContentList,
  useContentReach,
  useContentRecord,
  usePublishRecord,
  useSaveCatalogueField,
  useSetOverride,
  useAttachSlot,
  useSaveModule,
  type ComposedModule,
  type ModuleManifest,
} from '../api/resources'
import Choice from '../components/Choice'
import { AutosaveField, SaveState, fieldError } from '../components/EditorFields'
import ScreenState from '../components/ScreenState'
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
}: {
  campaignId: number
  module: ComposedModule
  manifest: ModuleManifest
  channel: string
  reload: () => void
}) {
  if (module.decision_slot_id != null) {
    return (
      <SlotBound campaignId={campaignId} module={module} manifest={manifest} slotId={module.decision_slot_id} />
    )
  }
  if (module.content_record_id == null) {
    return <Unbound campaignId={campaignId} module={module} />
  }
  return (
    <CatalogueFields
      campaignId={campaignId}
      module={module}
      recordId={module.content_record_id}
      manifest={manifest}
      channel={channel}
      reload={reload}
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
}: {
  campaignId: number
  module: ComposedModule
  recordId: number
  manifest: ModuleManifest
  channel: string
  reload: () => void
}) {
  const record = useContentRecord(recordId)
  const saveField = useSaveCatalogueField(recordId, channel)
  const setOverride = useSetOverride(campaignId)
  const overrides = (module.active_override?.field_overrides ?? {}) as Record<string, unknown>
  // Content fields only: a field typed in the module is the module's own,
  // edited below and never overridden (ADR-179's 2026-10-04 addendum).
  const fields = manifest.variables.filter((v) => !v.envelope && v.source !== 'module')
  const [confirmReset, setConfirmReset] = useState(false)
  const [rebinding, setRebinding] = useState(false)

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
          {rebinding && <BindRecord campaignId={campaignId} module={module} />}
          <PublishState recordId={recordId} detail={record.data} />

          <ModuleOwnFields campaignId={campaignId} module={module} manifest={manifest} />
          {fields.map((field) => (
            <CatalogueField
              key={field.name}
              module={module}
              field={field}
              catalogue={record.data.content[field.name]}
              overrides={overrides}
              setOverride={setOverride}
              saveField={saveField}
              recordId={recordId}
            />
          ))}

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

/** Design pass D5: a send uses the published version, so say when that lags. */
function PublishState({
  recordId,
  detail,
}: {
  recordId: number
  detail: { latest_version_number?: number | null; unpublished_changes: boolean }
}) {
  const publish = usePublishRecord(recordId)
  if (!detail.unpublished_changes) return null
  return (
    <p className="publish-state" role="status">
      {detail.latest_version_number == null
        ? 'Not published yet, so it cannot be sent until it is.'
        : `Changed since version ${detail.latest_version_number} was published — sends still use version ${detail.latest_version_number}.`}{' '}
      <Button isDisabled={publish.isPending} onPress={() => publish.mutate()}>
        {publish.isPending ? 'Publishing…' : 'Publish'}
      </Button>
      <SaveState mutation={publish} what="the record" />
    </p>
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

/** Bind a catalogue module to a record, found by title. */
function BindRecord({ campaignId, module }: { campaignId: number; module: ComposedModule }) {
  const [q, setQ] = useState('')
  const results = useContentList(0, q, 'active')
  const bind = useBindModule(campaignId)
  return (
    <div className="bind">
      {module.content_record_id == null && (
        <p>Not bound to content yet. It is reported at send, never blocked.</p>
      )}
      <TextField value={q} onChange={setQ}>
        <Label>Find a content record by title</Label>
        <Input />
      </TextField>
      {q.trim() && (
        <ul className="bind__results">
          {(results.data?.items ?? []).slice(0, 10).map((record) => (
            <li key={record.id}>
              <Button
                isDisabled={bind.isPending || record.id === module.content_record_id}
                onPress={() => bind.mutate({ id: module.id, contentRecordId: record.id })}
              >
                Use “{record.title}”
              </Button>
            </li>
          ))}
          {results.data && results.data.items.length === 0 && <li className="muted">No record matches.</li>}
        </ul>
      )}
      <SaveState mutation={bind} what="the module" />
    </div>
  )
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
  overrides,
  setOverride,
  saveField,
  recordId,
}: {
  module: ComposedModule
  field: ModuleManifest['variables'][number]
  catalogue: unknown
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
        // AutosaveField saves only a changed value, so an untouched catalogue
        // value never becomes an override.
        onSave={(next) => setOverride.mutate({ id: module.id, set: { [field.name]: next } })}
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

/**
 * A module filled by a decision slot: its settings in place (slice 7), and
 * the way back to one fixed record. Never overridable (ADR-186 point 5).
 */
function SlotBound({
  campaignId,
  module,
  manifest,
  slotId,
}: {
  campaignId: number
  module: ComposedModule
  manifest: ModuleManifest
  slotId: number
}) {
  const [rebinding, setRebinding] = useState(false)
  return (
    <>
      <ModuleOwnFields campaignId={campaignId} module={module} manifest={manifest} />
      <SlotSettings campaignId={campaignId} slotId={slotId} />
      <p className="muted">
        A slot is never overridden: one pinned value would replace every personal pick.
      </p>
      <Button onPress={() => setRebinding(!rebinding)}>
        {rebinding ? 'Keep the slot' : 'Use one content record instead'}
      </Button>
      {rebinding && <BindRecord campaignId={campaignId} module={module} />}
    </>
  )
}

/** A catalogue module with no content yet: one record, or a slot that picks per recipient. */
function Unbound({ campaignId, module }: { campaignId: number; module: ComposedModule }) {
  const attach = useAttachSlot(campaignId)
  return (
    <>
      <BindRecord campaignId={campaignId} module={module} />
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
