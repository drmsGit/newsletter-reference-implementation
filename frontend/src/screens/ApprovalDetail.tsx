import { useState } from 'react'
import {
  Button,
  Label,
  Radio,
  RadioGroup,
  TextArea,
  TextField,
} from 'react-aria-components'
import { Link, useParams } from 'react-router'

import { useApproval, useDecide, type PendingActionDetail } from '../api/resources'
import { HttpError } from '../api/session'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'

export default function ApprovalDetail() {
  const { id } = useParams()
  const approval = useApproval(Number(id))

  return (
    <>
      <p>
        <Link to="/approvals">← Approvals</Link>
      </p>
      <ScreenState query={approval}>
        {approval.data && (
          <>
            <h1>{approval.data.label}</h1>
            <p>{approval.data.summary}</p>

            {/*
              **`may_decide` is read, never computed.**

              `docs/react-screen-inventory.md` lists "deciding whether a person
              may approve a particular held action" among the things the SPA
              must not reimplement -- the rule lives in `approvals/service.py`,
              checks the action's own permission against the ROW's brand rather
              than the reader's, and a client-side copy would be a second
              answer free to disagree with the first.
            */}
            {!approval.data.may_decide && (
              <p role="status" className="muted">
                You cannot decide this request.
                {approval.data.blocked_reason ? ` ${approval.data.blocked_reason}` : ''}
              </p>
            )}

            {approval.data.describe_error && (
              <p role="alert">
                This request could not be described in full: {approval.data.describe_error}
              </p>
            )}

            {/* Rendered, never enforced: a warning that blocked would be a guard. */}
            {approval.data.warnings.length > 0 && (
              <section aria-labelledby="warnings">
                <h2 id="warnings">Before you decide</h2>
                <ul>
                  {approval.data.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </section>
            )}

            <dl className="facts">
              <dt>Status</dt>
              <dd>{approval.data.status}</dd>
              <dt>Requested by</dt>
              <dd>{approval.data.requested_by_type}</dd>
              <dt>Requested</dt>
              <dd>{formatDate(approval.data.created_at)}</dd>
              <dt>Expires</dt>
              <dd>{formatDate(approval.data.expires_at)}</dd>
              {approval.data.decided_at && (
                <>
                  <dt>Decided</dt>
                  <dd>{formatDate(approval.data.decided_at)}</dd>
                </>
              )}
              {approval.data.decision_reason && (
                <>
                  <dt>Reason given</dt>
                  <dd>{approval.data.decision_reason}</dd>
                </>
              )}
              {approval.data.execution_error && (
                <>
                  <dt>Why it did not run</dt>
                  <dd>{approval.data.execution_error}</dd>
                </>
              )}
              {/*
                `rows` is the server's own description of what this request
                would do, as label/value pairs. Rendering them generically is
                deliberate: each action type describes itself, so a client that
                knew the shapes would need editing every time one is added.
              */}
              {approval.data.rows.map((row) => (
                <div key={row.label} style={{ display: 'contents' }}>
                  <dt>{row.label}</dt>
                  <dd>{row.value}</dd>
                </div>
              ))}
            </dl>

            {approval.data.may_decide && approval.data.status === 'pending' && (
              <Decision approval={approval.data} />
            )}
          </>
        )}
      </ScreenState>
    </>
  )
}

/**
 * Approve or reject (2026-10-03).
 *
 * **Approving runs the action** (ADR-142 §4), so the button says so. One press,
 * decided with the user: the screen above already shows what will happen, and a
 * confirm step on every approval trains people to click through it.
 *
 * **The reason is optional on both** (Manager Workflow Q1.5) -- the requester
 * reads it, and "an agency needs to know what they need to change". A pick-one
 * (ADR-141 §4) must have an option chosen before approving: the action refuses
 * without one rather than defaulting to the first. A request the action says it
 * cannot run (`blocked_reason`) can still be rejected, never approved.
 */
function Decision({ approval }: { approval: PendingActionDetail }) {
  const decide = useDecide(approval.id)
  const [reason, setReason] = useState('')
  const [choice, setChoice] = useState<string>('')
  const options = approval.options ?? []
  const needsChoice = options.length > 0
  const canApprove = !approval.blocked_reason && (!needsChoice || choice !== '')

  const outcome = decide.data
  const failure = decide.error instanceof HttpError ? decide.error : undefined

  return (
    <section aria-labelledby="decide">
      <h2 id="decide">Decide</h2>
      {needsChoice && (
        <RadioGroup value={choice} onChange={setChoice}>
          <Label>Choose one</Label>
          {options.map((o) => (
            <Radio key={o.index} value={String(o.index)}>
              {o.label}
            </Radio>
          ))}
        </RadioGroup>
      )}
      <TextField value={reason} onChange={setReason}>
        <Label>Reason (optional; the requester sees it)</Label>
        <TextArea rows={3} style={{ width: '100%' }} />
      </TextField>
      <p>
        <Button
          isDisabled={!canApprove || decide.isPending}
          onPress={() =>
            decide.mutate({
              verdict: 'approve',
              reason,
              choice: needsChoice ? Number(choice) : undefined,
            })
          }
        >
          Approve and run
        </Button>{' '}
        <Button
          isDisabled={decide.isPending}
          onPress={() => decide.mutate({ verdict: 'reject', reason })}
        >
          Reject
        </Button>
      </p>
      {needsChoice && choice === '' && (
        <p className="muted">Choose an option to approve.</p>
      )}
      {outcome && (
        <p role={outcome.ok ? 'status' : 'alert'}>
          {outcome.message} Status: {outcome.status}.
        </p>
      )}
      {failure && (
        <p role="alert">
          {failure.status === 403
            ? 'You cannot decide this request.'
            : failure.detail ?? 'The decision could not be recorded.'}
        </p>
      )}
    </section>
  )
}
