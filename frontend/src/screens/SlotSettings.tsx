import { useEffect, useState } from 'react'
import { Checkbox, CheckboxGroup, Input, Label, Text, TextField } from 'react-aria-components'
import { Link } from 'react-router'

import {
  useCategories,
  useDecisionSlotStats,
  useSaveSlot,
  useSlotCandidates,
  useStrategies,
  type StrategyMeta,
} from '../api/resources'
import Choice from '../components/Choice'
import { SaveState } from '../components/EditorFields'
import ScreenState from '../components/ScreenState'

/**
 * A decision slot, configured on its module (task-264, slice 7).
 *
 * Variant Editor interview 1.3: the manager chooses the strategy and its
 * settings here, in place; the Decisions screen is for seeing what slots
 * pick. Every setting saves as soon as it changes, with the slot's version
 * (ADR-180 point 2), and the count of records the slot would choose between
 * is shown without resolving it (task-205). "Show up to" is how many picks the
 * module shows, best first, the module repeated once per pick (task-109,
 * ADR-084 addendum 2026-10-11); a push slot always shows one.
 */
export default function SlotSettings({
  campaignId,
  slotId,
  channel,
}: {
  campaignId: number
  slotId: number
  channel: string
}) {
  const stats = useDecisionSlotStats(slotId)
  const strategies = useStrategies()
  const save = useSaveSlot(campaignId, slotId)

  return (
    <ScreenState query={stats}>
      {stats.data && strategies.data && (
        <Settings
          slot={stats.data.slot}
          strategies={strategies.data}
          save={save}
          slotId={slotId}
          channel={channel}
        />
      )}
    </ScreenState>
  )
}

function Settings({
  slot,
  strategies,
  save,
  slotId,
  channel,
}: {
  slot: {
    decision_strategy: string
    max_results: number
    candidate_filter?: Record<string, unknown> | null
    strategy_config?: Record<string, unknown> | null
  }
  strategies: StrategyMeta[]
  save: ReturnType<typeof useSaveSlot>
  slotId: number
  channel: string
}) {
  const meta = strategies.find((s) => s.name === slot.decision_strategy)
  const filter = slot.candidate_filter ?? {}
  const config = slot.strategy_config ?? {}
  const takesCategories = (meta?.candidate_filter_fields ?? []).some((f) => f.name === 'category_ids')

  return (
    <div className="slot-settings">
      <p>
        Filled per recipient by a decision slot.{' '}
        <Link to={`/decision-slots/${slotId}`}>See what it has picked</Link>
      </p>
      <Choice
        label="Strategy"
        options={strategies.map((s) => ({ id: s.name, name: s.label }))}
        selected={slot.decision_strategy}
        onChange={(name) => {
          if (name !== slot.decision_strategy) save.mutate({ decision_strategy: name })
        }}
      />
      {meta && <Text className="muted">{meta.description}</Text>}
      <Candidates slotId={slotId} />
      {channel === 'push' ? (
        <Text className="muted">Shows one pick: a push is one notification.</Text>
      ) : (
        <Choice
          label="Show up to"
          options={[1, 2, 3, 4, 5].map((n) => ({ id: String(n), name: n === 1 ? '1 pick' : `${n} picks` }))}
          selected={String(slot.max_results)}
          onChange={(n) => {
            if (Number(n) !== slot.max_results) save.mutate({ max_results: Number(n) })
          }}
        />
      )}
      {takesCategories && (
        <Categories
          selected={Array.isArray(filter.category_ids) ? (filter.category_ids as number[]) : []}
          onChange={(ids) => save.mutate({ candidate_filter: { ...filter, category_ids: ids } })}
        />
      )}
      {(meta?.config_fields ?? []).map((field) => (
        <NumberSetting
          key={field.name}
          label={field.name.replace(/_/g, ' ')}
          description={field.description}
          value={config[field.name] ?? field.default}
          onSave={(n) => save.mutate({ strategy_config: { ...config, [field.name]: n } })}
        />
      ))}
      <SaveState mutation={save} what="the slot" />
    </div>
  )
}

/** What the slot would choose between now, asked without resolving it (task-205). */
function Candidates({ slotId }: { slotId: number }) {
  const candidates = useSlotCandidates(slotId)
  if (!candidates.data) return null
  const { candidate_count: count, requires_recipient } = candidates.data
  return (
    <p className="muted" role="status">
      Would choose between {count} active content record{count === 1 ? '' : 's'} now.
      {requires_recipient && ' It picks per recipient, so one person may be offered fewer.'}
    </p>
  )
}

/** The categories a slot may pick from; none ticked means every category. */
function Categories({ selected, onChange }: { selected: number[]; onChange: (ids: number[]) => void }) {
  const categories = useCategories()
  if (!categories.data) return null
  return (
    <CheckboxGroup
      className="react-aria-CheckboxGroup categories"
      value={selected.map(String)}
      onChange={(values) => onChange(values.map(Number))}
    >
      <Label>Categories (none ticked: every category)</Label>
      {categories.data.map((category) => (
        <Checkbox key={category.id} value={String(category.id)}>
          {category.name}
        </Checkbox>
      ))}
    </CheckboxGroup>
  )
}

/** A number setting that saves on blur, and only a number. */
function NumberSetting({
  label,
  description,
  value,
  onSave,
}: {
  label: string
  description: string
  value: unknown
  onSave: (n: number) => void
}) {
  const shown = value == null ? '' : String(value)
  const [draft, setDraft] = useState(shown)
  const [invalid, setInvalid] = useState(false)
  useEffect(() => setDraft(shown), [shown])
  return (
    <TextField
      className="react-aria-TextField field"
      value={draft}
      onChange={(next) => {
        setDraft(next)
        setInvalid(false)
      }}
      onBlur={() => {
        if (draft === shown) return
        const n = Number(draft)
        if (draft.trim() === '' || Number.isNaN(n)) {
          setInvalid(true)
          return
        }
        onSave(n)
      }}
      isInvalid={invalid}
    >
      <Label>{label}</Label>
      <Input inputMode="decimal" />
      {description && <Text slot="description" className="muted">{description}</Text>}
      {invalid && (
        <p role="alert" className="field-error">
          Enter a number.
        </p>
      )}
    </TextField>
  )
}
