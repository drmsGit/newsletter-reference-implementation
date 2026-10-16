import { Button } from 'react-aria-components'
import { Link } from 'react-router'

import { useSuggestSubject, useSuggestions, type SuggestionRun } from '../api/resources'
import { HttpError } from '../api/session'
import AIButton from '../components/AIButton'

export type SuggestionOption = SuggestionRun['options'][number]

/**
 * AI subject and preheader suggestions under the envelope (task-367; ADR-141 §3).
 *
 * The newest run is shown, read back from the server, so a reload shows the
 * same options. AI output stays a proposal: nothing reaches the variant until
 * a person presses "Use this". A run held for approval has its options taken
 * in Approvals, so it gets a link and no "Use this", as the Jinja page sends it
 * there.
 */
export default function SubjectSuggestions({
  variantId,
  onUse,
  using,
}: {
  variantId: number
  onUse: (option: SuggestionOption, runId: number) => void
  using: boolean
}) {
  const suggestions = useSuggestions(variantId)
  const suggest = useSuggestSubject(variantId)
  const latest = suggestions.data?.[0]
  const asked = suggest.data

  return (
    <section className="suggestions" aria-label="AI suggestions">
      <AIButton onPress={() => suggest.mutate()} pending={suggest.isPending}>
        Suggest with AI
      </AIButton>
      {suggest.error && (
        <p role="alert">
          {suggest.error instanceof HttpError && suggest.error.detail
            ? suggest.error.detail
            : 'The suggestion could not be asked for.'}
        </p>
      )}
      {asked && asked.outcome !== 'inline' && (
        <p role="status">
          {asked.message ?? 'The suggestion is waiting for approval.'}{' '}
          <Link to={asked.pending_action_id ? `/approvals/${asked.pending_action_id}` : '/approvals'}>
            Open it in Approvals
          </Link>
        </p>
      )}
      {latest && <Run run={latest} onUse={onUse} using={using} />}
    </section>
  )
}

function Run({ run, onUse, using }: { run: SuggestionRun; onUse: (option: SuggestionOption, runId: number) => void; using: boolean }) {
  const tokens = run.input_tokens + run.output_tokens
  const held = run.pending_action_id != null
  return (
    <div className="suggestion-run">
      {run.status !== 'ok' ? (
        <p role="alert">{run.message ?? 'The suggestion could not be generated.'}</p>
      ) : run.options.length === 0 ? (
        <>
          <p>No options could be read from the reply. The model said:</p>
          <blockquote>{run.reply}</blockquote>
        </>
      ) : (
        <>
          {held && (
            <p>
              These options wait for approval; one is picked there.{' '}
              <Link to={`/approvals/${run.pending_action_id}`}>Open it in Approvals</Link>
            </p>
          )}
          {run.notices.length > 0 && (
            <ul aria-label="Before you use one">
              {run.notices.map((notice) => (
                <li key={notice}>{notice}</li>
              ))}
            </ul>
          )}
          <ol aria-label="Suggested subjects">
            {run.options.map((option, index) => (
              <li key={index}>
                <strong>{option.subject}</strong>
                {option.preheader && <span> — {option.preheader}</span>}
                {!held && (
                  <Button
                    aria-label={`Use "${option.subject}"`}
                    isDisabled={using}
                    onPress={() => onUse(option, run.run_id)}
                  >
                    Use this
                  </Button>
                )}
              </li>
            ))}
          </ol>
        </>
      )}
      <p className="hint">
        {tokens} tokens · {run.model ?? run.provider}
        {run.prompt_version != null && ` · prompt v${run.prompt_version}`}
      </p>
    </div>
  )
}
