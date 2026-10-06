import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Button, Checkbox, CheckboxGroup, Input, Label, Text, TextField } from 'react-aria-components'

import {
  useAddRule,
  useAudienceBlocks,
  useCriteriaValues,
  useRemoveRule,
  useSaveRule,
  type AudienceRuleBlock,
} from '../api/resources'
import { HttpError } from '../api/session'
import CategoryChoice from '../components/CategoryChoice'
import { SaveState } from '../components/EditorFields'
import ScreenState from '../components/ScreenState'

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
        <p>
          Leaves these people out even if a rule or a hand-add includes them. People who opted out are never sent
          to anyway: that&apos;s consent, not this list.
        </p>
        <p className="muted">To reach people who did not click, include who received it and leave out who clicked.</p>
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
    <section aria-labelledby={id} className="rules">
      <h2 id={id}>{title}</h2>
      {children}
      {blocks.map((block) => (
        <RuleForm key={block.id} groupId={groupId} kind={kind} block={block} reload={reload} />
      ))}
      {blocks.length === 0 && !adding && (
        <p className="muted">{kind === 'include' ? 'No rules yet: only people added by hand are in.' : 'Nobody is left out by a rule.'}</p>
      )}
      {adding ? (
        <RuleForm groupId={groupId} kind={kind} reload={reload} onDone={() => setAdding(false)} />
      ) : (
        <Button onPress={() => setAdding(true)}>Add a rule</Button>
      )}
    </section>
  )
}

type Draft = { languages: string[]; statuses: string[]; categoryId: number | null; minScore: string; label: string }

/** A rule's fields as the form edits them; everything else in its criteria is kept as it is. */
function draftOf(block: AudienceRuleBlock | undefined): Draft {
  const c = (block?.criteria ?? {}) as Record<string, unknown>
  const list = (v: unknown) => (Array.isArray(v) ? v.map(String) : v == null || v === '' ? [] : [String(v)])
  return {
    languages: list(c.language),
    statuses: list(c.status),
    categoryId: c.category_id == null ? null : Number(c.category_id),
    // Filled in with 1.0 when a category is chosen (ADR-188 point 2).
    minScore: c.min_score == null ? '' : String(c.min_score),
    label: block?.label ?? '',
  }
}

function criteriaOf(draft: Draft, block: AudienceRuleBlock | undefined): Record<string, unknown> {
  const { language: _l, status: _s, category_id: _c, min_score: _m, ...kept } = (block?.criteria ?? {}) as Record<string, unknown>
  const criteria: Record<string, unknown> = { ...kept }
  if (draft.languages.length) criteria.language = [...draft.languages].sort()
  if (draft.statuses.length) criteria.status = [...draft.statuses].sort()
  if (draft.categoryId != null) {
    criteria.category_id = draft.categoryId
    criteria.min_score = draft.minScore.trim() === '' ? null : Number(draft.minScore)
  }
  return criteria
}

/**
 * One rule, edited in place and saved with its own "Save rule" (decision 10):
 * a half-built rule would briefly change the live audience, so nothing is
 * sent while it is edited. Language and status offer the values the brand's
 * recipients hold, several at once; a category always comes with a minimum
 * score, 1.0 unless changed (ADR-188 point 2).
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
  onDone?: () => void
}) {
  const values = useCriteriaValues()
  const add = useAddRule(groupId)
  const save = useSaveRule(groupId)
  const remove = useRemoveRule(groupId)
  const saved = JSON.stringify(draftOf(block))
  const [draft, setDraft] = useState<Draft>(() => draftOf(block))
  // The draft follows the saved rule whenever the server's answer changes.
  useEffect(() => setDraft(JSON.parse(saved)), [saved])
  const write = block ? save : add
  const dirty = JSON.stringify(draft) !== saved
  const engagement = (block?.criteria as Record<string, unknown> | null | undefined)?.engagement as
    | { event?: string }
    | undefined

  function submit(event: FormEvent) {
    event.preventDefault()
    const criteria = criteriaOf(draft, block)
    const label = draft.label.trim() || null
    if (block) save.mutate({ blockId: block.id, criteria, label })
    else add.mutate({ kind, criteria, label }, { onSuccess: () => onDone?.() })
  }

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
      <CategoryChoice
        label="Category interest"
        noneLabel="No category"
        selected={draft.categoryId}
        onChange={(categoryId) =>
          setDraft({ ...draft, categoryId, minScore: draft.minScore.trim() ? draft.minScore : '1.0' })
        }
      />
      {draft.categoryId != null && (
        <TextField value={draft.minScore} onChange={(minScore) => setDraft({ ...draft, minScore })} inputMode="decimal">
          <Label>Minimum score</Label>
          <Input />
          <Text slot="description" className="muted">
            How strong their interest in this category must be; above 0.
          </Text>
        </TextField>
      )}
      {engagement && (
        <p className="muted">Also reads what they did with a mailing ({engagement.event}); kept as it is.</p>
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
      {block ? (
        <Button isDisabled={remove.isPending} onPress={() => remove.mutate(block.id)}>
          Remove rule
        </Button>
      ) : (
        <Button onPress={onDone}>Cancel</Button>
      )}
      <SaveState mutation={write} what="this audience" reload={reload} />
      <SaveState mutation={remove} what="this audience" reload={reload} />
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
    <CheckboxGroup className="categories" value={selected} onChange={onChange}>
      <Label>{label}</Label>
      {options.map((value) => (
        <Checkbox key={value} value={value}>
          {value}
        </Checkbox>
      ))}
    </CheckboxGroup>
  )
}
