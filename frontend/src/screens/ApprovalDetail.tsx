import { Link, useParams } from 'react-router'

import { useApproval } from '../api/resources'
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
          </>
        )}
      </ScreenState>
    </>
  )
}
