import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Button, Checkbox, CheckboxGroup, Input, Label, Text, TextField } from 'react-aria-components'

import {
  useAddRule,
  useAudienceBlocks,
  useCategories,
  useCriteriaValues,
  useRemoveRule,
  useSaveRule,
  type AudienceRuleBlock,
} from '../api/resources'
import { HttpError } from '../api/session'
import CategoryChoice from '../components/CategoryChoice'
import { SaveState } from '../components/EditorFields'
import DetailSection from '../components/DetailSection'
import ScreenState from '../components/ScreenState'
import {
  EngagementFields,
  EngagementSummary,
  NEW_ENGAGEMENT,
  engagementDraftOf,
  engagementOf,
  type EngagementDraft,
} from './AudienceEngagement'

/**
 * A group's rules in two lists, "Who's in" and "Leave out" (Audience Write
 * Surface decision 9; ADR-188 point 6). The logic is flat (ADR-188 point 1):
 * values OR inside a field, fields AND inside a rule, rules OR across, and the
 * leave-out rules subtract.
 */
export default function AudienceRules({ groupId, reload }: { groupId: number; reload: () => void }) {
  const blocks = useAudienceBlocks(groupId)
  return (
    <ScreenState query={blocks}>
      <RuleSection
        groupId={groupId}
        kind="include"
        title="Who's in"
        blocks={(blocks.data ?? []).filter((b) => b.kind === 'include')}
        reload={reload}
      />
      <RuleSection
        groupId={groupId}
        kind="exclude"
        title="Leave out"
        blocks={(blocks.data ?? []).filter((b) => b.kind === 'exclude')}
        reload={reload}
      >
        <div>
          <p>
            Leaves these people out even if a rule or a hand-add includes them. People who opted out are never sent
            to anyway: that&apos;s consent, not this list.
          </p>
          <p className="muted">To reach people who did not click, include who received it and leave out who clicked.</p>
        </div>
      </RuleSection>
    </ScreenState>
  )
}

function RuleSection({
  groupId,
  kind,
  title,
  blocks,
  reload,
  children,
}: {
  groupId: number
  kind: 'include' | 'exclude'
  title: string
  blocks: AudienceRuleBlock[]
  reload: () => void
  children?: ReactNode
}) {
  const [adding, setAdding] = useState(false)
  const id = `rules-${kind}`
  return (
    <DetailSection id={id} title={title} className="rules">
      {children}
      {blocks.map((block) => (
        <Rule key={block.id} groupId={groupId} kind={kind} block={block} reload={reload} />
      ))}
      {blocks.length === 0 && !adding && (
        <p className="muted">{kind === 'include' ? 'No rules yet: only people added by hand are in.' : 'Nobody is left out by a rule.'}</p>
      )}
      {adding ? (
        <RuleForm groupId={groupId} kind={kind} reload={reload} onDone={() => setAdding(false)} />
      ) : (
        <div>
          <Button onPress={() => setAdding(true)}>Add a rule</Button>
        </div>
      )}
    </DetailSection>
  )
}

type CategoryRow = { categoryId: number | null; minScore: string }
type Draft = {
  languages: string[]
  statuses: string[]
  categories: CategoryRow[]
  engagement: EngagementDraft | null
  label: string
}

/**
 * A rule's categories as `(id, score)` pairs, in either stored shape: the list
 * (ADR-188 addendum 2026-10-06) or the older single pair the server still
 * accepts and converts (`category_terms` on the server).
 */
function categoriesOf(criteria: Record<string, unknown>): { id: number; score: number }[] {
  if (Array.isArray(criteria.categories))
    return (criteria.categories as { category_id: number; min_score: number }[]).map((c) => ({
      id: Number(c.category_id),
      score: Number(c.min_score),
    }))
  if (criteria.category_id == null || criteria.category_id === '') return []
  return [{ id: Number(criteria.category_id), score: Number(criteria.min_score ?? 0) }]
}

/** A rule's fields as the form edits them; everything else in its criteria is kept as it is. */
function draftOf(block: AudienceRuleBlock | undefined): Draft {
  const c = (block?.criteria ?? {}) as Record<string, unknown>
  const list = (v: unknown) => (Array.isArray(v) ? v.map(String) : v == null || v === '' ? [] : [String(v)])
  return {
    languages: list(c.language),
    statuses: list(c.status),
    categories: categoriesOf(c).map(({ id, score }) => ({ categoryId: id, minScore: String(score) })),
    engagement: engagementDraftOf(c.engagement),
    label: block?.label ?? '',
  }
}

function criteriaOf(draft: Draft, block: AudienceRuleBlock | undefined): Record<string, unknown> {
  const {
    language: _l,
    status: _s,
    categories: _cs,
    category_id: _c,
    min_score: _m,
    engagement: _e,
    ...kept
  } = (block?.criteria ?? {}) as Record<string, unknown>
  const criteria: Record<string, unknown> = { ...kept }
  if (draft.languages.length) criteria.language = [...draft.languages].sort()
  if (draft.statuses.length) criteria.status = [...draft.statuses].sort()
  const chosen = draft.categories.filter((row) => row.categoryId != null)
  if (chosen.length)
    criteria.categories = chosen.map((row) => ({
      category_id: row.categoryId,
      min_score: row.minScore.trim() === '' ? null : Number(row.minScore),
    }))
  if (draft.engagement) criteria.engagement = engagementOf(draft.engagement)
  return criteria
}

/**
 * A saved rule reads as one line (task-300, the user 2026-10-07): what it
 * says, its name and whether the system suggested it, with "Edit" opening
 * the form for this rule only. Saving or cancelling closes it again.
 */
function Rule({
  groupId,
  kind,
  block,
  reload,
}: {
  groupId: number
  kind: 'include' | 'exclude'
  block: AudienceRuleBlock
  reload: () => void
}) {
  const [editing, setEditing] = useState(false)
  const remove = useRemoveRule(groupId)
  const name = block.label || `Rule ${block.id}`
  if (editing)
    return <RuleForm groupId={groupId} kind={kind} block={block} reload={reload} onDone={() => setEditing(false)} />
  return (
    <div className="rule rule--line" role="group" aria-label={name}>
      <div className="rule__text">
        {block.label && <strong>{block.label}</strong>}{' '}
        {block.source === 'suggested' && <span className="badge">Suggested</span>}{' '}
        <RuleSummary criteria={block.criteria ?? {}} />
      </div>
      <div className="rule__actions">
        <Button className="btn-sm" onPress={() => setEditing(true)}>
          Edit
        </Button>
        <Button className="btn-plain btn-sm" isDisabled={remove.isPending} onPress={() => remove.mutate(block.id)}>
          Remove rule
        </Button>
      </div>
      <SaveState mutation={remove} what="this audience" reload={reload} />
    </div>
  )
}

/** "Language de or fr · Status active · Nature ≥ 5 or Wellness ≥ 3". */
function RuleSummary({ criteria }: { criteria: Record<string, unknown> }) {
  const categories = useCategories()
  const names = new Map((categories.data ?? []).map((c) => [c.id, c.name]))
  const list = (v: unknown) => (Array.isArray(v) ? v.map(String) : v == null || v === '' ? [] : [String(v)])
  const parts = [
    list(criteria.language).length > 0 && `Language ${list(criteria.language).join(' or ')}`,
    list(criteria.status).length > 0 && `Status ${list(criteria.status).join(' or ')}`,
    categoriesOf(criteria).length > 0 &&
      categoriesOf(criteria)
        .map(({ id, score }) => `${names.get(id) ?? `Category ${id}`} ≥ ${score}`)
        .join(' or '),
  ].filter(Boolean)
  if (criteria.engagement != null)
    return (
      <span className="muted">
        {parts.map((part) => `${part} · `)}
        <EngagementSummary engagement={criteria.engagement} />
      </span>
    )
  return <span className="muted">{parts.length ? parts.join(' · ') : 'Everyone (no conditions)'}</span>
}

/**
 * One rule's form, saved with its own "Save rule" (decision 10): a half-built
 * rule would briefly change the live audience, so nothing is sent while it is
 * edited. Language and status offer the values the brand's recipients hold,
 * several at once; category interest lists one or more categories, each with
 * its own minimum score, 1.0 unless changed (ADR-188 point 3 and its
 * 2026-10-06 addendum). A person matches a rule when they clear any one.
 */
function RuleForm({
  groupId,
  kind,
  block,
  reload,
  onDone,
}: {
  groupId: number
  kind: 'include' | 'exclude'
  block?: AudienceRuleBlock
  reload: () => void
  onDone: () => void
}) {
  const values = useCriteriaValues()
  const add = useAddRule(groupId)
  const save = useSaveRule(groupId)
  const saved = JSON.stringify(draftOf(block))
  const [draft, setDraft] = useState<Draft>(() => draftOf(block))
  // The draft follows the saved rule whenever the server's answer changes.
  useEffect(() => setDraft(JSON.parse(saved)), [saved])
  const write = block ? save : add
  const dirty = JSON.stringify(draft) !== saved

  function submit(event: FormEvent) {
    event.preventDefault()
    const criteria = criteriaOf(draft, block)
    const label = draft.label.trim() || null
    if (block) save.mutate({ blockId: block.id, criteria, label }, { onSuccess: onDone })
    else add.mutate({ kind, criteria, label }, { onSuccess: onDone })
  }

  const setRow = (i: number, row: CategoryRow) =>
    setDraft({ ...draft, categories: draft.categories.map((r, j) => (j === i ? row : r)) })
  const fields = write.error instanceof HttpError ? write.error.fields : {}
  return (
    <form className="rule" aria-label={block ? block.label || `Rule ${block.id}` : 'New rule'} onSubmit={submit}>
      {block?.source === 'suggested' && <span className="badge">Suggested</span>}
      <Choices
        label="Language"
        offered={values.data?.languages ?? []}
        selected={draft.languages}
        onChange={(languages) => setDraft({ ...draft, languages })}
      />
      <Choices
        label="Status"
        offered={values.data?.statuses ?? []}
        selected={draft.statuses}
        onChange={(statuses) => setDraft({ ...draft, statuses })}
      />
      <div role="group" aria-labelledby={`interest-${block?.id ?? 'new'}`} className="rule__categories">
        <span id={`interest-${block?.id ?? 'new'}`}>Category interest</span>
        {draft.categories.length > 1 && <span className="muted"> — any one is enough</span>}
        {draft.categories.map((row, i) => (
          <div key={i} role="group" aria-label={`Category ${i + 1}`} className="rule__category">
            <CategoryChoice
              label="Category"
              noneLabel="Choose a category"
              selected={row.categoryId}
              exclude={new Set(draft.categories.filter((_, j) => j !== i).flatMap((r) => r.categoryId ?? []))}
              onChange={(categoryId) => setRow(i, { ...row, categoryId })}
            />
            <TextField value={row.minScore} onChange={(minScore) => setRow(i, { ...row, minScore })} inputMode="decimal">
              <Label>Minimum score</Label>
              <Input />
              <Text slot="description" className="muted">
                How strong their interest in this category must be; above 0.
              </Text>
            </TextField>
            <Button
              onPress={() => setDraft({ ...draft, categories: draft.categories.filter((_, j) => j !== i) })}
            >
              Remove this category
            </Button>
          </div>
        ))}
        <Button
          onPress={() =>
            setDraft({ ...draft, categories: [...draft.categories, { categoryId: null, minScore: '1.0' }] })
          }
        >
          Add a category
        </Button>
      </div>
      {draft.engagement ? (
        <EngagementFields
          draft={draft.engagement}
          kind={kind}
          onChange={(engagement) => setDraft({ ...draft, engagement })}
          onRemove={() => setDraft({ ...draft, engagement: null })}
        />
      ) : (
        <Button onPress={() => setDraft({ ...draft, engagement: NEW_ENGAGEMENT })}>Add engagement</Button>
      )}
      <TextField value={draft.label} onChange={(label) => setDraft({ ...draft, label })}>
        <Label>Rule name</Label>
        <Input />
      </TextField>
      {Object.entries(fields).map(([field, message]) => (
        <p key={field} role="alert" className="field-error">
          {message}
        </p>
      ))}
      <Button type="submit" isDisabled={write.isPending || (block != null && !dirty)}>
        {write.isPending ? 'Saving…' : 'Save rule'}
      </Button>{' '}
      {/* Closing the form discards the draft: it is read from the rule again when reopened. */}
      <Button onPress={onDone}>Cancel</Button>
      <SaveState mutation={write} what="this audience" reload={reload} />
    </form>
  )
}

/** Several values of one field; a value already in the rule stays offered even if nobody holds it now. */
function Choices({
  label,
  offered,
  selected,
  onChange,
}: {
  label: string
  offered: string[]
  selected: string[]
  onChange: (values: string[]) => void
}) {
  const options = [...new Set([...offered, ...selected])]
  if (options.length === 0) return null
  return (
    <CheckboxGroup className="react-aria-CheckboxGroup categories" value={selected} onChange={onChange}>
      <Label>{label}</Label>
      {options.map((value) => (
        <Checkbox key={value} value={value}>
          {value}
        </Checkbox>
      ))}
    </CheckboxGroup>
  )
}
