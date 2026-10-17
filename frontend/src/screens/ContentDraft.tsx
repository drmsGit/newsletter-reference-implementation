import { useState } from 'react'
import { Button, Checkbox, CheckboxGroup, Label, Text, TextArea, TextField } from 'react-aria-components'

import {
  useContentDrafts,
  useDraftContent,
  useEditAssignments,
  useSaveContentRecord,
  type ContentDraft as Draft,
} from '../api/resources'
import type { components } from '../api/schema'
import { HttpError } from '../api/session'
import AIButton from '../components/AIButton'
import Choice from '../components/Choice'
import DetailSection from '../components/DetailSection'
import { SCORES } from './scores'

type ContentField = components['schemas']['ContentField']

/** Said on the box (ADR-141 addendum 2026-10-16, point 2); the server refuses past it. */
const MAX_SOURCE = 12000

/**
 * "Draft with AI" on a record's page (task-368; ADR-141 addendum 2026-10-16).
 *
 * A manager pastes a source and ticks the channels; the model drafts their
 * text fields and proposes categories from the existing ones. Nothing is
 * written by asking: the newest draft is read back from the server and a
 * person takes the fields and categories they tick, through the ordinary
 * record save and category writes, each naming the run. There is no approval
 * step (ADR-140 addendum of the same date): taking it is the person's act.
 */
export default function ContentDraft({ recordId, fields }: { recordId: number; fields: ContentField[] }) {
  const channels = [...new Set(fields.map((f) => f.channel).filter((c): c is string => !!c))]
  // What was unticked, not what is ticked: the fields can arrive after the
  // panel does, and a channel that arrives later starts ticked.
  const [unticked, setUnticked] = useState<string[]>([])
  const ticked = channels.filter((c) => !unticked.includes(c))
  const [source, setSource] = useState('')
  const drafts = useContentDrafts(recordId)
  const ask = useDraftContent(recordId)
  const refused = ask.error instanceof HttpError ? ask.error : null
  const latest = drafts.data?.[0]

  return (
    <DetailSection id="draft-heading" title="Draft with AI" className="content-draft">
      <TextField value={source} onChange={setSource} isInvalid={!!refused?.fields.source}>
        <Label>Source</Label>
        <TextArea rows={6} />
        <Text slot="description">
          Paste the content or write a brief — not anyone&apos;s personal details: the text goes to the model
          provider and is not kept here. {source.length.toLocaleString('en')} of {MAX_SOURCE.toLocaleString('en')}{' '}
          characters.
        </Text>
        {refused?.fields.source && <Text slot="errorMessage">{refused.fields.source}</Text>}
      </TextField>
      <CheckboxGroup
        value={ticked}
        onChange={(value) => setUnticked(channels.filter((c) => !value.includes(c)))}
        className="react-aria-CheckboxGroup categories option-pair"
      >
        <Label>Draft the text fields for</Label>
        {channels.map((channel) => (
          <Checkbox key={channel} value={channel}>
            {channel.charAt(0).toUpperCase() + channel.slice(1)}
          </Checkbox>
        ))}
      </CheckboxGroup>
      {refused?.fields.channels && <p role="alert">{refused.fields.channels}</p>}
      <AIButton onPress={() => ask.mutate({ source, channels: ticked })} pending={ask.isPending}>
        Draft with AI
      </AIButton>
      {ask.error && !refused?.fields.source && !refused?.fields.channels && (
        <p role="alert">{refused?.detail ?? 'The draft could not be asked for.'}</p>
      )}
      {latest && <Proposal key={latest.run_id} recordId={recordId} draft={latest} />}
    </DetailSection>
  )
}

/**
 * One draft, with its own ticks: keyed by run, so a new draft starts afresh.
 * Also takes a fresh translation (task-369), which has fields only and starts
 * with the fields whose original changed ticked.
 */
export function Proposal({ recordId, draft, ticked }: { recordId: number; draft: Draft; ticked?: string[] }) {
  const save = useSaveContentRecord(recordId)
  const edit = useEditAssignments(recordId)
  // A field that already has text, or a category already on the record, starts
  // unticked — unless the caller names the fields to start with (a fresh
  // translation: those whose original changed).
  const [fieldTicks, setFieldTicks] = useState(
    ticked ? draft.fields.filter((f) => ticked.includes(f.name)).map((f) => f.name)
      : draft.fields.filter((f) => !f.current).map((f) => f.name),
  )
  const [categoryTicks, setCategoryTicks] = useState(
    draft.categories.filter((c) => c.assigned_score == null).map((c) => String(c.category_id)),
  )
  const [scores, setScores] = useState<Record<number, string>>(
    Object.fromEntries(draft.categories.map((c) => [c.category_id, String(c.score)])),
  )
  const [done, setDone] = useState('')
  const failure = save.error ?? edit.error
  const tokens = draft.input_tokens + draft.output_tokens

  function takeFields() {
    const taken = draft.fields.filter((f) => fieldTicks.includes(f.name))
    // A translation proposes the title and description too, which are the
    // record's own, not content fields.
    const own = (name: string) => taken.find((f) => f.name === name)?.text
    const fields = taken.filter((f) => f.name !== 'title' && f.name !== 'description')
    save.mutate(
      {
        ...(own('title') !== undefined && { title: own('title') }),
        ...(own('description') !== undefined && { description: own('description') }),
        content: Object.fromEntries(fields.map((f) => [f.name, f.text])),
        groups: [...new Set(fields.map((f) => f.channel).filter((c): c is string => !!c))],
        applied_suggestion_run_id: draft.run_id,
      },
      { onSuccess: () => setDone(`${taken.length} field${taken.length === 1 ? '' : 's'} saved.`) },
    )
  }

  async function assignCategories() {
    const taken = draft.categories.filter((c) => categoryTicks.includes(String(c.category_id)))
    try {
      for (const c of taken) {
        const score = Number(scores[c.category_id])
        await edit.mutateAsync(
          c.assignment_id != null
            ? { kind: 'score', assignmentId: c.assignment_id, score, runId: draft.run_id }
            : { kind: 'assign', categoryId: c.category_id, score, runId: draft.run_id },
        )
      }
      setDone(`${taken.length} categor${taken.length === 1 ? 'y' : 'ies'} assigned.`)
    } catch {
      // Shown from `edit.error` below.
    }
  }

  if (draft.status !== 'ok') return <p role="alert">{draft.message ?? 'The draft could not be made.'}</p>
  if (draft.fields.length === 0 && draft.categories.length === 0)
    return (
      <div className="draft-proposal">
        <p>No draft could be read from the reply. The model said:</p>
        <blockquote>{draft.reply}</blockquote>
      </div>
    )

  return (
    <div className="draft-proposal">
      {draft.notices.length > 0 && (
        <ul aria-label="Before you take any of it">
          {draft.notices.map((notice) => (
            <li key={notice}>{notice}</li>
          ))}
        </ul>
      )}
      {draft.fields.length > 0 && (
        <>
          <CheckboxGroup value={fieldTicks} onChange={setFieldTicks} className="react-aria-CheckboxGroup categories">
            <Label>Drafted fields</Label>
            {draft.fields.map((f) => (
              <Checkbox key={f.name} value={f.name} aria-label={f.label}>
                <span>
                  <strong>{f.label}</strong>: {f.text}
                  {f.current && <span className="muted"> (now: {f.current})</span>}
                </span>
              </Checkbox>
            ))}
          </CheckboxGroup>
          <Button onPress={takeFields} isDisabled={fieldTicks.length === 0 || save.isPending}>
            Use ticked fields
          </Button>
        </>
      )}
      {draft.categories.length > 0 && (
        <>
          <CheckboxGroup value={categoryTicks} onChange={setCategoryTicks} className="react-aria-CheckboxGroup categories">
            <Label>Proposed categories</Label>
            {draft.categories.map((c) => (
              <div key={c.category_id} className="draft-category">
                <Checkbox value={String(c.category_id)} aria-label={c.name}>
                  <strong>{c.name}</strong> — {c.reason}
                  {c.assigned_score != null && <span className="muted"> (on the record at {c.assigned_score})</span>}
                </Checkbox>
                <Choice
                  label={`Score for ${c.name}`}
                  options={SCORES}
                  selected={scores[c.category_id]}
                  onChange={(next) => setScores((s) => ({ ...s, [c.category_id]: next }))}
                />
              </div>
            ))}
          </CheckboxGroup>
          <Button onPress={assignCategories} isDisabled={categoryTicks.length === 0 || edit.isPending}>
            Assign ticked
          </Button>
        </>
      )}
      {done && <p role="status">{done}</p>}
      {failure && (
        <p role="alert">Not saved: {(failure instanceof HttpError && failure.detail) || 'the server refused it.'}</p>
      )}
      <p className="hint">
        {tokens} tokens · {draft.model ?? draft.provider}
        {draft.prompt_version != null && ` · prompt v${draft.prompt_version}`}
      </p>
    </div>
  )
}
