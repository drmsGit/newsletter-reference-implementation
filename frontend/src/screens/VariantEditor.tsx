import { useState, type KeyboardEvent } from 'react'
import { ArrowDown, ArrowUp, ChevronLeft, Contrast, Pencil, Pin, type LucideIcon } from 'lucide-react'
import { Button } from 'react-aria-components'
import { Link, useParams } from 'react-router'

import {
  useAddModule,
  useBrandProfileChoices,
  useBrandProfileStructure,
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
import Fence from './Fence'
import SubjectSuggestions, { type SuggestionOption } from './SubjectSuggestions'
import TopicProposal from './TopicProposal'
import PreviewBar from './Preview'
import { ShortcutHint, useShortcut } from '../shortcuts/Shortcuts'
import { BRAND_PROFILES, fieldLabels } from './BrandProfiles'

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
 *
 * v2 (task-372, render 21): the stack is column 2 and everything else column
 * 3, the selected module last. The navigation stays as the person set it, as
 * on every screen (decision 13, 2026-10-17).
 */
export default function VariantEditor() {
  const params = useParams()
  const campaignId = Number(params.id)
  const variantId = Number(params.variantId)
  const composition = useComposition(campaignId)
  const composed = composition.data?.variants.find((v) => v.variant.id === variantId)
  const manifests = useModuleManifests(composed?.variant.channel)
  // Bumped by "Load their version": the fields remount and start from what is
  // stored. A field keeps its draft while its stored value is unchanged, and
  // after a refused save it often is (somebody else edited another field), so
  // the refused text would otherwise stay on screen looking saved (the bug
  // task-279 found on the record page, reproduced here 2026-10-05).
  const [generation, setGeneration] = useState(0)

  const back = (
    <Link className="back-link" to={`/campaigns/${campaignId}`}>
      <ChevronLeft size={14} strokeWidth={1.75} aria-hidden="true" />
      {composition.data?.campaign.name ?? 'Campaign'}
    </Link>
  )
  const waiting = composition.data && composed && manifests.data ? null : (
    <div className="detail-scroll">
      <p>{back}</p>
      <ScreenState query={composition}>
        {composition.data && !composed && <p>This campaign has no variant {variantId}.</p>}
        {composed && <ScreenState query={manifests}>{null}</ScreenState>}
      </ScreenState>
    </div>
  )

  return (
    waiting ?? (
      <Editor
        back={back}
        campaignId={campaignId}
        composed={composed!}
        manifests={manifests.data!}
        reload={() => {
          setGeneration((n) => n + 1)
          composition.refetch()
        }}
        generation={generation}
        stamp={composition.dataUpdatedAt}
      />
    )
  )
}

function Editor({
  back,
  campaignId,
  composed,
  manifests,
  reload,
  generation,
  stamp,
}: {
  back: React.ReactNode
  campaignId: number
  composed: ComposedVariant
  manifests: ModuleManifest[]
  reload: () => void
  generation: number
  stamp: number
}) {
  const { variant, modules } = composed
  const [selectedId, setSelectedId] = useState<number | undefined>(modules[0]?.id)
  const selected = modules.find((m) => m.id === selectedId) ?? modules[0]
  const byName = new Map(manifests.map((m) => [m.name, m]))

  return (
    <div className="split">
      <section className="col-list" aria-labelledby="stack-heading">
        <div className="list-head">
          {back}
          <h1 id="stack-heading">Modules</h1>
        </div>
        <Stack
          campaignId={campaignId}
          modules={modules}
          byName={byName}
          selected={selected}
          onSelect={setSelectedId}
        />
        <div className="list-foot list-foot--add">
          <AddModule campaignId={campaignId} composed={composed} byName={byName} onAdded={setSelectedId} />
        </div>
      </section>
      <section className="col-detail" aria-labelledby="variant-heading">
        <div className="detail-scroll">
          <div className="detail-head detail-head--bar">
            <div>
              <h2 id="variant-heading">{variant.name}</h2>
              <p className="muted">
                {variant.channel} · {variant.status} ·{' '}
                <Link to={`/campaigns/${campaignId}/variants/${variant.id}/send`}>Send…</Link>
              </p>
            </div>
            <PreviewBar variantId={variant.id} variantName={variant.name} stamp={stamp} byName={byName} />
          </div>
          <Fence campaignId={campaignId} variantId={variant.id} fence={composed.fence} />
          <ProfileChoice campaignId={campaignId} composed={composed} reload={reload} />
          {composed.has_envelope && (
            <Envelope key={generation} campaignId={campaignId} composed={composed} manifests={manifests} reload={reload} />
          )}
          {composed.preparable_from_topic && (
            <div className="group group-body">
              <TopicProposal campaignId={campaignId} variantId={variant.id} />
            </div>
          )}
          <section className="detail-section editor__fields" aria-labelledby="fields-heading">
            {selected ? (
              <ModuleFields
                key={`${selected.id}-${generation}`}
                campaignId={campaignId}
                module={selected}
                manifest={byName.get(selected.module_type)}
                channel={variant.channel}
                reload={reload}
                otherRecordIds={modules.flatMap((m) =>
                  m.id !== selected.id && m.content_record_id != null ? [m.content_record_id] : [],
                )}
              />
            ) : (
              <p id="fields-heading" className="quiet muted">
                Add a module to start.
              </p>
            )}
          </section>
        </div>
      </section>
    </div>
  )
}

/**
 * Which of the brand's profiles this variant uses (task-350; ADR-194 point 4):
 * its look, texts and legal details. Saved on choosing, like every field here.
 * Says when the profile is incomplete, and when it changed without anybody
 * choosing it because the one it used was deleted.
 */
function ProfileChoice({
  campaignId,
  composed,
  reload,
}: {
  campaignId: number
  composed: ComposedVariant
  reload: () => void
}) {
  const choices = useBrandProfileChoices()
  const structure = useBrandProfileStructure()
  const save = useSaveVariant(campaignId)
  const current = composed.brand_profile
  const items = choices.data?.items ?? []
  // The current one is offered even before the list arrives, so the choice
  // never shows empty.
  const options = (items.some((p) => p.id === current.id) ? items : [current, ...items]).map((p) => ({
    id: String(p.id),
    name: `${p.name}${p.is_default ? ' (default)' : ''} · ${p.language}${p.kind === 'transactional' ? ' · transactional' : ''}`,
  }))

  return (
    <section className="detail-section brand-profile-choice" aria-labelledby="profile-heading">
      <h3 id="profile-heading" className="group-title">
        Brand profile
      </h3>
      <div className="group card-rows">
        <Choice
          labelHidden
          label="Brand profile"
          options={options}
          selected={String(current.id)}
          onChange={(id) => save.mutate({ id: composed.variant.id, changes: { brand_profile_id: Number(id) } })}
        />
        {current.kind === 'transactional' && (
          // ADR-195: the manager sees, where they choose, that this skips the opt-in.
          <p role="status">
            <strong>Sent without opt-in check.</strong> This profile is transactional: everyone in the audience is
            mailed whether or not they agreed to marketing.
          </p>
        )}
        {current.notice && <p role="status">{current.notice}</p>}
        {current.missing.length > 0 && (
          <p role="status">
            This profile is incomplete:{' '}
            {fieldLabels(current.missing, structure.data)}. <Link to={`${BRAND_PROFILES}/${current.id}`}>Fill it in</Link>{' '}
            before sending.
          </p>
        )}
        {choices.data && choices.data.total > items.length && (
          <p className="muted">Only the first {items.length} of {choices.data.total} profiles are offered.</p>
        )}
        <SaveState mutation={save} reload={reload} what="the variant" />
      </div>
    </section>
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
  // The fields of the module the server says carries the envelope (task-221),
  // not every module's envelope-flagged fields: scanning for those here would
  // be a second copy of `envelope_module_type`, in another language (ADR-177
  // point 8). A variant has this before its first subject is saved, when it
  // has no envelope row yet.
  const carrier = manifests.find((m) => m.carries_envelope)
  const fields = (carrier?.variables ?? []).filter((v) => v.envelope)

  // The whole envelope goes with each save, since a sent envelope replaces the
  // stored one; the values are read and written by the manifest's field names,
  // so no channel's field names are spelt out here (task-48).
  function saveField(name: string, value: string) {
    save.mutate({ id: variant.id, changes: { envelope: { ...variant.envelope, [name]: value.trim() || null } } })
  }

  // Subject and preheader together, in one save, and the entry names the run
  // the copy came from (task-367). The option's keys are the envelope's own
  // field names, as the Jinja page's "Use this" posts them.
  function takeOption(option: SuggestionOption, runId: number) {
    save.mutate({
      id: variant.id,
      changes: {
        envelope: { ...variant.envelope, subject: option.subject, preheader: option.preheader || null },
        applied_suggestion_run_id: runId,
      },
    })
  }

  return (
    <section className="detail-section envelope" aria-labelledby="envelope-heading">
      <h3 id="envelope-heading" className="group-title">
        Envelope
      </h3>
      <div className="group card-rows">
        {fields.map((field) => (
          <AutosaveField
            key={field.name}
            field={field}
            value={variant.envelope[field.name] ?? ''}
            onSave={(value) => saveField(field.name, value)}
            personalise
            error={fieldError(save.error, field.name)}
          />
        ))}
        {carrier && (
          <SubjectSuggestions variantId={variant.id} onUse={takeOption} using={save.isPending} />
        )}
        <SaveState mutation={save} reload={reload} what="the variant" />
      </div>
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
  // Handled on the selected module itself (onKeyDown below); listed so the
  // overview shows them (task-266).
  useShortcut('Alt+↑', 'Move the selected module up', null)
  useShortcut('Alt+↓', 'Move the selected module down', null)
  const remove = useDeleteModule(campaignId)
  const [confirming, setConfirming] = useState<number | null>(null)

  if (modules.length === 0) return <p className="list-empty muted">This variant has no modules yet.</p>

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
      <ol className="stack item-list">
        {modules.map((module, index) => {
          const label = byName.get(module.module_type)?.label ?? module.module_type
          const source = sourceOf(module)
          return (
            <li key={module.id} className="stack__item" aria-current={module.id === selected?.id || undefined}>
              <Button
                className="stack__select"
                onPress={() => onSelect(module.id)}
                onKeyDown={(event) => onKeyDown(event, module, index)}
                aria-keyshortcuts="Alt+ArrowUp Alt+ArrowDown"
                // Said as one line, "Hero · Record “Lisbon”": browsers join the two
                // lines' parts without spaces otherwise.
                aria-label={`${label} · ${source.word}${source.name ? ` ${source.name}` : ''}`}
              >
                <span className="item-title">{label}</span>
                <span className="stack__source">
                  <SourceChip source={source} />
                  {source.name && <span className="muted">{source.name}</span>}
                </span>
              </Button>
              <Button
                className="btn-plain btn-sm btn-icon"
                aria-label={`Move ${label} up`}
                isDisabled={index === 0}
                onPress={() => move.mutate({ id: module.id, direction: 'up' })}
              >
                <ArrowUp size={14} strokeWidth={1.75} aria-hidden="true" /> <ShortcutHint keys="Alt+↑" />
              </Button>
              <Button
                className="btn-plain btn-sm btn-icon"
                aria-label={`Move ${label} down`}
                isDisabled={index === modules.length - 1}
                onPress={() => move.mutate({ id: module.id, direction: 'down' })}
              >
                <ArrowDown size={14} strokeWidth={1.75} aria-hidden="true" /> <ShortcutHint keys="Alt+↓" />
              </Button>
              {confirming === module.id ? (
                <span role="group" aria-label={`Remove ${label}?`} className="stack__confirm">
                  {/*
                    Removing is not undoable and takes the module's overrides
                    with it (their history stays in the audit log, design pass
                    D2), so it asks once, in place.
                  */}
                  <Button
                    className="btn-sm btn-destructive"
                    onPress={() => {
                      setConfirming(null)
                      remove.mutate({ id: module.id })
                    }}
                  >
                    Remove {label}
                  </Button>
                  <Button className="btn-sm" onPress={() => setConfirming(null)}>
                    Keep
                  </Button>
                </span>
              ) : (
                <Button
                  className="btn-plain btn-sm"
                  aria-label={`Remove ${label}`}
                  onPress={() => setConfirming(module.id)}
                >
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

/** The suffix of the "two at once" choice for a module that pairs. */
const TWO = ':two'

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
  // A module that pairs (the Column, ADR-198 point 4) is also offered two at
  // once, side by side: "Two columns".
  const options = composed.accepted_module_types.flatMap((type) => {
    const manifest = byName.get(type)
    const one = { id: type, name: manifest?.label ?? type }
    return manifest?.pairs ? [one, { id: `${type}${TWO}`, name: `Two ${one.name.toLowerCase()}s` }] : [one]
  })
  const [type, setType] = useState(options[0]?.id ?? '')
  const two = type.endsWith(TWO)
  const moduleType = two ? type.slice(0, -TWO.length) : type

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
        onPress={async () => {
          const created = await add.mutateAsync({ variantId: composed.variant.id, moduleType }).catch(() => null)
          if (created && two) await add.mutateAsync({ variantId: composed.variant.id, moduleType }).catch(() => null)
          if (created) onAdded(created.id)
        }}
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
  otherRecordIds,
}: {
  campaignId: number
  module: ComposedModule
  manifest: ModuleManifest | undefined
  channel: string
  reload: () => void
  otherRecordIds: number[]
}) {
  const save = useSaveModule(campaignId)
  const title = manifest?.label ?? module.module_type

  if (!manifest) {
    return (
      <>
        <h3 id="fields-heading" className="group-title">
          {title}
        </h3>
        <p className="group group-body">
          This channel has no module called {module.module_type}, so it cannot be edited or rendered.
        </p>
      </>
    )
  }
  if (manifest.cms) {
    // Catalogue-bound (ADR-179): ADR-178's edit-or-override, slice 6.
    return (
      <>
        <h3 id="fields-heading" className="group-title">
          {title}
        </h3>
        <div className="group card-rows module-card">
          <CatalogueModule
            campaignId={campaignId}
            module={module}
            manifest={manifest}
            channel={channel}
            reload={reload}
            otherRecordIds={otherRecordIds}
          />
        </div>
      </>
    )
  }

  const data = module.module_data as Record<string, unknown>
  const fields = manifest.variables.filter((v) => !v.envelope)
  return (
    <>
      <h3 id="fields-heading" className="group-title">
        {title}
      </h3>
      <div className="group card-rows module-card">
        {fields.map((field) => (
          <AutosaveField
            key={field.name}
            field={field}
            value={typeof data[field.name] === 'string' ? (data[field.name] as string) : ''}
            onSave={(value) =>
              save.mutate({ id: module.id, changes: { [field.name]: value.trim() ? value : null } })
            }
            personalise
            error={fieldError(save.error, field.name)}
          />
        ))}
        <SaveState mutation={save} reload={reload} what="the module" />
      </div>
    </>
  )
}

/**
 * How a module's content is chosen, the system and human cue (task-372,
 * decision 11, 2026-10-17): a record a person bound, a decision slot that
 * picks for the system, or text typed in. A glyph and a word in a neutral
 * chip, so no colour carries it.
 */
type Source = { word: string; icon: LucideIcon; name: string | null }

function sourceOf(module: ComposedModule): Source {
  // Names, not ids (2026-10-04); the id only when no name came back.
  if (module.content_record_id != null)
    return {
      word: 'Record',
      icon: Pin,
      name: `“${module.content_record_title ?? `record #${module.content_record_id}`}”`,
    }
  if (module.decision_slot_id != null)
    return { word: 'Slot', icon: Contrast, name: `“${module.decision_slot_name ?? `#${module.decision_slot_id}`}”` }
  return { word: 'Typed in', icon: Pencil, name: null }
}

function SourceChip({ source }: { source: Source }) {
  const Icon = source.icon
  return (
    <span className="chip chip-source">
      <Icon size={12} strokeWidth={1.75} aria-hidden="true" />
      {source.word}
    </span>
  )
}
