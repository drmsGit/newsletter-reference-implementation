import { useState } from 'react'
import { Button, Checkbox, Label, Text, TextArea, TextField } from 'react-aria-components'

import {
  useBuildFromProposal,
  useProposeFromTopic,
  useTopicProposals,
  type TopicProposal as Proposal,
} from '../api/resources'
import { HttpError } from '../api/session'
import AIButton from '../components/AIButton'

const MAX_TOPIC = 500

/**
 * "Prepare from a topic" in an empty email variant (task-370; ADR-141
 * addendum 2026-10-17). The manager names a topic; the model proposes a hero,
 * an editorial text, two to four records in image blocks, maybe a slot by
 * categories, and subject and preheader — chosen only from what a machine may
 * take. Nothing is written by asking: the proposal is read back, each part
 * can be left out, the editorial edited, and "Build the variant" builds the
 * rest in one step. The editor offers it only while the server says the
 * variant is empty (`preparable_from_topic`).
 */
export default function TopicProposal({ campaignId, variantId }: { campaignId: number; variantId: number }) {
  const [topic, setTopic] = useState('')
  const ask = useProposeFromTopic(variantId)
  const proposals = useTopicProposals(variantId, true)
  const refused = ask.error instanceof HttpError ? ask.error : null
  const latest = proposals.data?.[0]

  return (
    <section aria-labelledby="topic-heading" className="topic-proposal">
      <h3 id="topic-heading">Prepare from a topic</h3>
      <TextField value={topic} onChange={setTopic} isInvalid={!!refused?.fields.topic}>
        <Label>Topic</Label>
        <TextArea rows={2} />
        <Text slot="description">
          What this edition is about, in a sentence. The AI builds the stack from content a machine may take.
          {` ${topic.length} of ${MAX_TOPIC} characters.`}
        </Text>
        {refused?.fields.topic && <Text slot="errorMessage">{refused.fields.topic}</Text>}
      </TextField>
      <AIButton onPress={() => ask.mutate(topic)} pending={ask.isPending}>
        Propose a variant
      </AIButton>
      {ask.error && !refused?.fields.topic && (
        <p role="alert">{refused?.detail ?? 'The proposal could not be asked for.'}</p>
      )}
      {latest && <Review key={latest.run_id} campaignId={campaignId} variantId={variantId} proposal={latest} />}
    </section>
  )
}

/** One proposal, its own ticks: keyed by run, so a new one starts afresh. */
function Review({ campaignId, variantId, proposal }: { campaignId: number; variantId: number; proposal: Proposal }) {
  const build = useBuildFromProposal(campaignId, variantId)
  const [hero, setHero] = useState(true)
  const [editorial, setEditorial] = useState(proposal.editorial)
  const [blocks, setBlocks] = useState(proposal.blocks.map((b) => b.record_id))
  const [slot, setSlot] = useState(true)
  const [envelope, setEnvelope] = useState(true)
  const tokens = proposal.input_tokens + proposal.output_tokens

  if (proposal.status !== 'ok') return <p role="alert">{proposal.message ?? 'The proposal could not be made.'}</p>
  const empty = !proposal.hero && !proposal.editorial && proposal.blocks.length === 0 && !proposal.slot
  if (empty)
    return (
      <div className="draft-proposal">
        <p>No proposal could be read from the reply. The model said:</p>
        <blockquote>{proposal.reply}</blockquote>
      </div>
    )

  const toggle = (id: number) =>
    setBlocks((now) => (now.includes(id) ? now.filter((b) => b !== id) : proposal.blocks
      .map((b) => b.record_id).filter((b) => now.includes(b) || b === id)))

  return (
    <div className="draft-proposal">
      <p className="hint">Chosen among the {proposal.offered} most recently created records a machine may take.</p>
      {proposal.notices.length > 0 && (
        <ul aria-label="Before you build it">
          {proposal.notices.map((notice) => (
            <li key={notice}>{notice}</li>
          ))}
        </ul>
      )}
      <ol aria-label="Proposed stack">
        {proposal.hero && (
          <li>
            <Checkbox isSelected={hero} onChange={setHero} aria-label={`Hero: ${proposal.hero.title}`}>
              <strong>Hero</strong>: {proposal.hero.title} — {proposal.hero.reason}
            </Checkbox>
          </li>
        )}
        <li>
          <TextField value={editorial} onChange={setEditorial}>
            <Label>Editorial</Label>
            <TextArea rows={3} />
            <Text slot="description">Empty leaves the editorial out.</Text>
          </TextField>
        </li>
        {proposal.blocks.map((b) => {
          // Left and right alternate over the ticked blocks, as the build lays them out.
          const at = blocks.indexOf(b.record_id)
          const kind = at < 0 ? 'Image block' : at % 2 === 0 ? 'Image left' : 'Image right'
          return (
            <li key={b.record_id}>
              <Checkbox isSelected={at >= 0} onChange={() => toggle(b.record_id)} aria-label={`Block: ${b.title}`}>
                <strong>{kind}</strong>: {b.title} — {b.reason}
              </Checkbox>
            </li>
          )
        })}
        {proposal.slot && (
          <li>
            <Checkbox isSelected={slot} onChange={setSlot} aria-label="Slot by categories">
              <strong>Slot</strong>, up to 3 picks per reader from {proposal.slot.categories.join(', ')} —{' '}
              {proposal.slot.reason}
            </Checkbox>
          </li>
        )}
        {proposal.subject && (
          <li>
            <Checkbox isSelected={envelope} onChange={setEnvelope} aria-label="Subject and preheader">
              <strong>Subject</strong>: {proposal.subject}
              {proposal.preheader && <> — {proposal.preheader}</>}
            </Checkbox>
          </li>
        )}
      </ol>
      <Button
        isDisabled={build.isPending}
        onPress={() =>
          build.mutate({
            run_id: proposal.run_id, hero, editorial: editorial.trim(), blocks, slot, envelope,
          })
        }
      >
        Build the variant
      </Button>
      {build.error && (
        <p role="alert">
          Not built: {(build.error instanceof HttpError && build.error.detail) || 'the server refused it.'}
        </p>
      )}
      <p className="hint">
        {tokens} tokens · {proposal.model ?? proposal.provider}
        {proposal.prompt_version != null && ` · prompt v${proposal.prompt_version}`}
      </p>
    </div>
  )
}
