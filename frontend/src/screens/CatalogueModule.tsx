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
  type ComposedModule,
  type ModuleManifest,
} from '../api/resources'
import Choice from '../components/Choice'
import { AutosaveField, SaveState, fieldError } from '../components/EditorFields'
import ScreenState from '../components/ScreenState'

/**
 * A catalogue-bound module in the variant editor (task-258, slice 6):
 * ADR-178 made concrete.
 *
 * - A field shows the record's value, and typing edits **the record** — the
 *   default, because a typo is wrong everywhere (point 1).
 * - "Override here" converts **that one field**; from then on it edits this
 *   module only, and the catalogue value it covers stays visible (points 2, 4).
 * - Reset one field, or every override on the module after a confirmation (6).
 * - Beside the fields, how many unsent campaigns use the record (8), and
 *   whether a send would carry the edits yet, with Publish (design pass D5).
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
      <p>
        Its fields come from{' '}
        <Link to={`/decision-slots/${module.decision_slot_id}`}>decision slot #{module.decision_slot_id}</Link>,
        picked per recipient. A slot is never overridden: one pinned value would replace every
        personal pick.
      </p>
    )
  }
  if (module.content_record_id == null) {
    return <BindRecord campaignId={campaignId} module={module} />
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
  const fields = manifest.variables.filter((v) => !v.envelope)
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
          <Reach recordId={recordId} />
          <PublishState recordId={recordId} detail={record.data} />

          {fields.map((field) => {
            const catalogue = record.data.content[field.name]
            const catalogueText = typeof catalogue === 'string' ? catalogue : ''
            if (field.name in overrides) {
              const value = overrides[field.name]
              return (
                <div key={field.name} className="overridden">
                  <AutosaveField
                    field={{ ...field, label: `${field.label ?? field.name} — overridden here` }}
                    value={typeof value === 'string' ? value : ''}
                    onSave={(next) => setOverride.mutate({ id: module.id, set: { [field.name]: next } })}
                    error={fieldError(setOverride.error, field.name)}
                  />
                  <Text className="muted">Catalogue: {catalogueText || '—'}</Text>{' '}
                  <Button onPress={() => setOverride.mutate({ id: module.id, unset: [field.name] })}>
                    Back to the catalogue value
                  </Button>
                </div>
              )
            }
            return (
              <div key={field.name}>
                <AutosaveField
                  field={field}
                  value={catalogueText}
                  onSave={(next) => saveField.mutate({ [field.name]: next.trim() ? next : null })}
                  error={fieldError(saveField.error, field.name)}
                />
                {module.overrideable && (
                  <Button
                    onPress={() =>
                      setOverride.mutate({ id: module.id, set: { [field.name]: catalogueText } })
                    }
                  >
                    Override {field.label ?? field.name} here
                  </Button>
                )}
              </div>
            )
          })}

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

/** ADR-178 point 8: passive, before anyone types; the list only on request. */
function Reach({ recordId }: { recordId: number }) {
  const reach = useContentReach(recordId)
  const [open, setOpen] = useState(false)
  if (!reach.data) return null
  const { count, campaigns } = reach.data
  return (
    <div className="reach">
      <Text className="muted">
        Editing a field here changes the catalogue record, used by {count} unsent campaign
        {count === 1 ? '' : 's'}.
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
