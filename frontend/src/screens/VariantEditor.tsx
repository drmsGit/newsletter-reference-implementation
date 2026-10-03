import { useState, type KeyboardEvent } from 'react'
import { Button } from 'react-aria-components'
import { Link, useParams } from 'react-router'

import {
  useAddModule,
  useComposition,
  useDeleteModule,
  useModuleManifests,
  useMoveModule,
  useSaveModule,
  useSaveVariant,
  type ComposedModule,
  type ComposedVariant,
  type ModuleManifest,
} from '../api/resources'
import Choice from '../components/Choice'
import { AutosaveField, SaveState, fieldError } from '../components/EditorFields'
import ScreenState from '../components/ScreenState'
import CatalogueModule from './CatalogueModule'

/**
 * One variant, edited (task-255, slice 5 of the campaign write surface).
 *
 * The layout is the Variant Editor interview's 2.1: the module stack on one
 * side, the selected module's fields beside it, the envelope (subject,
 * preheader) as a fixed area on top (2.3). Modules move with buttons and
 * Alt+Arrow, never by dragging (1.5).
 *
 * **Every field saves when it loses focus** (design pass D1) and carries the
 * version it was read at (task-110), so a save over somebody else's newer
 * edit is refused with 409 and shown here, never merged silently.
 *
 * Not here yet, by slice: editing a catalogue-bound module's fields and
 * overriding them (6), configuring a slot on its module (7), the preview
 * overlay, and the advisory lock (task-254).
 */
export default function VariantEditor() {
  const params = useParams()
  const campaignId = Number(params.id)
  const variantId = Number(params.variantId)
  const composition = useComposition(campaignId)
  const composed = composition.data?.variants.find((v) => v.variant.id === variantId)
  const manifests = useModuleManifests(composed?.variant.channel)

  return (
    <>
      <p>
        <Link to={`/campaigns/${campaignId}`}>← {composition.data?.campaign.name ?? 'Campaign'}</Link>
      </p>
      <ScreenState query={composition}>
        {composition.data && !composed && <p>This campaign has no variant {variantId}.</p>}
        {composed && (
          <ScreenState query={manifests}>
            {manifests.data && (
              <Editor
                campaignId={campaignId}
                composed={composed}
                manifests={manifests.data}
                reload={() => composition.refetch()}
              />
            )}
          </ScreenState>
        )}
      </ScreenState>
    </>
  )
}

function Editor({
  campaignId,
  composed,
  manifests,
  reload,
}: {
  campaignId: number
  composed: ComposedVariant
  manifests: ModuleManifest[]
  reload: () => void
}) {
  const { variant, modules } = composed
  const [selectedId, setSelectedId] = useState<number | undefined>(modules[0]?.id)
  const selected = modules.find((m) => m.id === selectedId) ?? modules[0]
  const byName = new Map(manifests.map((m) => [m.name, m]))

  return (
    <>
      <h1>{variant.name}</h1>
      <p className="muted">
        {variant.channel} · {variant.status}
      </p>
      {composed.has_envelope && (
        <Envelope campaignId={campaignId} composed={composed} manifests={manifests} reload={reload} />
      )}
      <div className="editor">
        <section className="editor__stack" aria-labelledby="stack-heading">
          <h2 id="stack-heading">Modules</h2>
          <Stack
            campaignId={campaignId}
            modules={modules}
            byName={byName}
            selected={selected}
            onSelect={setSelectedId}
          />
          <AddModule campaignId={campaignId} composed={composed} byName={byName} onAdded={setSelectedId} />
        </section>
        <section className="editor__fields" aria-labelledby="fields-heading">
          {selected ? (
            <ModuleFields
              key={selected.id}
              campaignId={campaignId}
              module={selected}
              manifest={byName.get(selected.module_type)}
              channel={variant.channel}
              reload={reload}
            />
          ) : (
            <p id="fields-heading">Add a module to start.</p>
          )}
        </section>
      </div>
    </>
  )
}

/** Subject and preheader, from the channel's envelope fields (ADR-162 point 1). */
function Envelope({
  campaignId,
  composed,
  manifests,
  reload,
}: {
  campaignId: number
  composed: ComposedVariant
  manifests: ModuleManifest[]
  reload: () => void
}) {
  const save = useSaveVariant(campaignId)
  const { variant } = composed
  const fields = manifests.flatMap((m) => m.variables).filter((v) => v.envelope)
  const values: Record<string, string | null | undefined> = {
    subject: variant.subject,
    preheader: variant.preheader,
  }

  function saveField(name: string, value: string) {
    save.mutate({ id: variant.id, changes: { [name]: value.trim() || null } })
  }

  return (
    <section className="envelope" aria-label="Envelope">
      {fields.map((field) => (
        <AutosaveField
          key={field.name}
          field={field}
          value={values[field.name] ?? ''}
          onSave={(value) => saveField(field.name, value)}
          error={fieldError(save.error, field.name)}
        />
      ))}
      <SaveState mutation={save} reload={reload} what="the variant" />
    </section>
  )
}

function Stack({
  campaignId,
  modules,
  byName,
  selected,
  onSelect,
}: {
  campaignId: number
  modules: ComposedModule[]
  byName: Map<string, ModuleManifest>
  selected: ComposedModule | undefined
  onSelect: (id: number) => void
}) {
  const move = useMoveModule(campaignId)
  const remove = useDeleteModule(campaignId)
  const [confirming, setConfirming] = useState<number | null>(null)

  if (modules.length === 0) return <p>This variant has no modules yet.</p>

  function onKeyDown(event: KeyboardEvent, module: ComposedModule, index: number) {
    // Alt+Arrow moves the module the focus is on (VE 1.5): the keyboard path
    // the interview asked for, beside the buttons, with no dragging anywhere.
    if (!event.altKey) return
    if (event.key === 'ArrowUp' && index > 0) {
      event.preventDefault()
      move.mutate({ id: module.id, direction: 'up' })
    } else if (event.key === 'ArrowDown' && index < modules.length - 1) {
      event.preventDefault()
      move.mutate({ id: module.id, direction: 'down' })
    }
  }

  return (
    <>
      <ol className="stack">
        {modules.map((module, index) => {
          const label = byName.get(module.module_type)?.label ?? module.module_type
          return (
            <li key={module.id} className="stack__item" aria-current={module.id === selected?.id || undefined}>
              <Button
                className="stack__select"
                onPress={() => onSelect(module.id)}
                onKeyDown={(event) => onKeyDown(event, module, index)}
                aria-keyshortcuts="Alt+ArrowUp Alt+ArrowDown"
              >
                {label}{" "}
                <span className="muted">· {bindingOf(module)}</span>
              </Button>
              <Button
                aria-label={`Move ${label} up`}
                isDisabled={index === 0}
                onPress={() => move.mutate({ id: module.id, direction: 'up' })}
              >
                ↑
              </Button>
              <Button
                aria-label={`Move ${label} down`}
                isDisabled={index === modules.length - 1}
                onPress={() => move.mutate({ id: module.id, direction: 'down' })}
              >
                ↓
              </Button>
              {confirming === module.id ? (
                <span role="group" aria-label={`Remove ${label}?`}>
                  {/*
                    Removing is not undoable and takes the module's overrides
                    with it (their history stays in the audit log, design pass
                    D2), so it asks once, in place.
                  */}
                  <Button
                    onPress={() => {
                      setConfirming(null)
                      remove.mutate({ id: module.id })
                    }}
                  >
                    Remove {label}
                  </Button>
                  <Button onPress={() => setConfirming(null)}>Keep</Button>
                </span>
              ) : (
                <Button aria-label={`Remove ${label}`} onPress={() => setConfirming(module.id)}>
                  Remove
                </Button>
              )}
            </li>
          )
        })}
      </ol>
      <SaveState mutation={move} what="the module order" />
      <SaveState mutation={remove} what="the module" />
    </>
  )
}

function AddModule({
  campaignId,
  composed,
  byName,
  onAdded,
}: {
  campaignId: number
  composed: ComposedVariant
  byName: Map<string, ModuleManifest>
  onAdded: (id: number) => void
}) {
  const add = useAddModule(campaignId)
  // Only what the channel accepts, as the server says (envelope types are
  // already left out of `accepted_module_types`).
  const options = composed.accepted_module_types.map((type) => ({
    id: type,
    name: byName.get(type)?.label ?? type,
  }))
  const [type, setType] = useState(options[0]?.id ?? '')

  if (!composed.can_add_module) {
    return (
      <p className="muted">
        A {composed.variant.channel} variant holds {composed.module_limit} module
        {composed.module_limit === 1 ? '' : 's'}, and this one is full.
      </p>
    )
  }
  return (
    <div className="add-module">
      <Choice label="Add a module" options={options} selected={type} onChange={setType} />
      <Button
        isDisabled={!type || add.isPending}
        onPress={() =>
          add.mutate(
            { variantId: composed.variant.id, moduleType: type },
            { onSuccess: (created) => onAdded(created.id) },
          )
        }
      >
        Add
      </Button>
      <SaveState mutation={add} what="the module" />
    </div>
  )
}

/** The selected module's fields: a static module's here, a catalogue-bound one's in CatalogueModule. */
function ModuleFields({
  campaignId,
  module,
  manifest,
  channel,
  reload,
}: {
  campaignId: number
  module: ComposedModule
  manifest: ModuleManifest | undefined
  channel: string
  reload: () => void
}) {
  const save = useSaveModule(campaignId)
  const title = manifest?.label ?? module.module_type

  if (!manifest) {
    return (
      <>
        <h2 id="fields-heading">{title}</h2>
        <p>This channel has no module called {module.module_type}, so it cannot be edited or rendered.</p>
      </>
    )
  }
  if (manifest.cms) {
    // Catalogue-bound (ADR-179): ADR-178's edit-or-override, slice 6.
    return (
      <>
        <h2 id="fields-heading">{title}</h2>
        <CatalogueModule
          campaignId={campaignId}
          module={module}
          manifest={manifest}
          channel={channel}
          reload={reload}
        />
      </>
    )
  }

  const data = module.module_data as Record<string, unknown>
  const fields = manifest.variables.filter((v) => !v.envelope)
  return (
    <>
      <h2 id="fields-heading">{title}</h2>
      {fields.map((field) => (
        <AutosaveField
          key={field.name}
          field={field}
          value={typeof data[field.name] === 'string' ? (data[field.name] as string) : ''}
          onSave={(value) =>
            save.mutate({ id: module.id, changes: { [field.name]: value.trim() ? value : null } })
          }
          error={fieldError(save.error, field.name)}
        />
      ))}
      <SaveState mutation={save} reload={reload} what="the module" />
    </>
  )
}

function bindingOf(module: ComposedModule): string {
  if (module.content_record_id != null) return `record #${module.content_record_id}`
  if (module.decision_slot_id != null) return `slot #${module.decision_slot_id}`
  return 'typed in'
}
