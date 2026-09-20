import { Link, useParams } from 'react-router'

import { useAudienceGroup } from '../api/resources'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'

export default function AudienceDetail() {
  const { id } = useParams()
  const group = useAudienceGroup(Number(id))

  return (
    <>
      <p>
        <Link to="/audiences">← Audiences</Link>
      </p>
      <ScreenState query={group}>
        {group.data && (
          <>
            <h1>{group.data.name}</h1>
            {group.data.description && <p>{group.data.description}</p>}

            <dl className="facts">
              <dt>Created</dt>
              <dd>{formatDate(group.data.created_at)}</dd>
              <dt>Updated</dt>
              <dd>{formatDate(group.data.updated_at)}</dd>
            </dl>

            {/*
              Members and rule blocks each have their own endpoint and are not
              loaded here yet. Resolving a group to its recipients is
              consent-gated and channel-dependent on the server
              (`resolve_audience`), so the count a screen shows has to come from
              the server rather than from counting rows a client happens to hold.
            */}
            <p className="muted">
              Members and rules land with the audience write surface.
            </p>
          </>
        )}
      </ScreenState>
    </>
  )
}
