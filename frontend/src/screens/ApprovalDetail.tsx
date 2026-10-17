import { useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import {
  Button,
  Label,
  Radio,
  RadioGroup,
  TextArea,
  TextField,
} from 'react-aria-components'
import { useParams } from 'react-router'

import { useApproval, useDecide, type PendingActionDetail } from '../api/resources'
import { HttpError } from '../api/session'
import Fact from '../components/Fact'
import ScreenState from '../components/ScreenState'
import StatusChip from '../components/StatusChip'
import { deadline } from './Approvals'
import { formatDate } from './Campaigns'

/**
 * Column 3 of the inbox (task-372; HANDOFF section 6): the request's label and
 * summary, what to know before deciding, the facts, and the decision docked at
 * the foot on the same ground. Also rendered on its own (its route, the tests).
 */
export default function ApprovalDetail() {
  const { id } = useParams()
  const approval = useApproval(Number(id))

  return (
    <ScreenState query={approval}>
      {approval.data && (
        <div className="detail">
          <div className="detail-scroll">
            <header className="detail-head">
              <h2>{approval.data.label}</h2>
              <p className="muted">{approval.data.summary}</p>
            </header>

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
              <p role="status" className="quiet muted">
                You cannot decide this request.
                {approval.data.blocked_reason ? ` ${approval.data.blocked_reason}` : ''}
              </p>
            )}

            {approval.data.describe_error && (
              <p role="alert" className="notice-alert">
                This request could not be described in full: {approval.data.describe_error}
              </p>
            )}

            {/* Rendered, never enforced: a warning that blocked would be a guard. */}
            {approval.data.warnings.length > 0 && (
              <section aria-labelledby="warnings">
                <h3 id="warnings" className="group-title">
                  Before you decide
                </h3>
                <ul className="group group-list">
                  {approval.data.warnings.map((w) => (
                    <li key={w} className="group-row notice">
                      <AlertTriangle size={14} strokeWidth={2} aria-hidden="true" className="notice-icon" />
                      <span>{w}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            <dl className="group fact-list">
              <Fact label="Status">
                <StatusChip status={approval.data.status} />
              </Fact>
              <Fact label="Requested by">{approval.data.requested_by_type}</Fact>
              <Fact label="Requested">{formatDate(approval.data.created_at)}</Fact>
              <Fact label="Expires">{deadline(approval.data.expires_at)}</Fact>
              {approval.data.decided_at && <Fact label="Decided">{formatDate(approval.data.decided_at)}</Fact>}
              {approval.data.decision_reason && <Fact label="Reason given">{approval.data.decision_reason}</Fact>}
              {approval.data.execution_error && (
                <Fact label="Why it did not run">{approval.data.execution_error}</Fact>
              )}
              {/*
                `rows` is the server's own description of what this request
                would do, as label/value pairs. Rendering them generically is
                deliberate: each action type describes itself, so a client that
                knew the shapes would need editing every time one is added.
              */}
              {approval.data.rows.map((row) => (
                <Fact key={row.label} label={row.label}>
                  {row.value}
                </Fact>
              ))}
            </dl>

            {approval.data.status === 'pending' && approval.data.requester_allowed === false && (
              // task-331 (ADR-142, second addendum of 2026-10-09): the request is
              // re-checked against its requester when approved.
              <p role="status" className="quiet">
                Whoever asked for this is no longer allowed to: they were switched off, or lost
                the permission it needs. Approving will withdraw the request, and nothing will run.
              </p>
            )}
          </div>
          {/* Keyed by the request: in the split the details stay mounted from one
              request to the next, and a choice or reason belongs to the request it
              was made on (ADR-141 section 4; Codex doc-33). */}
          {approval.data.may_decide && approval.data.status === 'pending' && (
            <Decision key={approval.data.id} approval={approval.data} />
          )}
        </div>
      )}
    </ScreenState>
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
    <section aria-labelledby="decide" className="decide">
      <h3 id="decide" className="group-title">
        Decide
      </h3>
      <div className="group group-body">
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
        <TextArea rows={3} />
      </TextField>
      <p className="btnrow">
        <Button
          className="btn-primary btn-lg"
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
          className="btn-lg btn-destructive"
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
      </div>
    </section>
  )
}
