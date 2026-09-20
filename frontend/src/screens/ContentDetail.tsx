import { Link, useParams } from 'react-router'

import { useContentRecord } from '../api/resources'
import ScreenState from '../components/ScreenState'

export default function ContentDetail() {
  const { id } = useParams()
  const record = useContentRecord(Number(id))

  return (
    <>
      <p>
        <Link to="/content">← Content</Link>
      </p>
      <ScreenState query={record}>
        {record.data && (
          <>
            <h1>{record.data.title}</h1>
            {record.data.description && <p>{record.data.description}</p>}

            <dl className="facts">
              <dt>Status</dt>
              <dd>{record.data.status ?? '—'}</dd>
            </dl>

            <h2>Fields</h2>
            {/*
              **`content` is an open object and is rendered generically.**

              The API types it as a dictionary, not a fixed shape, because what
              a content record carries depends on its type -- and ADR-165 made
              the core channel-neutral, so a client that hard-coded "headline"
              and "body_medium" would be an email-shaped client again. Whatever
              the server sends is what is shown.
            */}
            <dl className="facts">
              {Object.entries(record.data.content ?? {}).map(([field, value]) => (
                <div key={field} style={{ display: 'contents' }}>
                  <dt>{field}</dt>
                  <dd>{typeof value === 'string' ? value : JSON.stringify(value)}</dd>
                </div>
              ))}
            </dl>
          </>
        )}
      </ScreenState>
    </>
  )
}
