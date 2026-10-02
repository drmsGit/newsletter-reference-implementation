import { Link, useParams } from 'react-router'

import { useAsSent, type DeliveryAsSent as AsSent } from '../api/resources'
import { HttpError } from '../api/session'
import DataTable, { type DataColumn } from '../components/DataTable'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'

type ModuleRow = AsSent['modules'][number] & { id: number }

const moduleColumns: DataColumn<ModuleRow>[] = [
  { key: 'type', header: 'Module', isRowHeader: true, render: (m) => m.module_type },
  /**
   * `kind` says where the module's values came from -- content, static, a
   * decision slot's pick for this recipient -- which is the answer to "why did
   * they get this", so it is shown as the server names it.
   */
  { key: 'kind', header: 'Kind', render: (m) => m.kind },
  { key: 'content', header: 'Content record', render: (m) => m.content_record_id ?? '—' },
  { key: 'version', header: 'Version', render: (m) => m.content_version_id ?? '—' },
]

/**
 * What one recipient got in one send, as of the send date (ADR-183).
 *
 * **Content is exact; layout is best-effort, and this screen says which it is.**
 * The server rebuilds the message from the snapshot's frame and the execution's
 * delivery record with today's templates. When those templates are not the ones
 * used, or the rebuilt output is not byte-identical to what was sent, a notice
 * says so above the message -- ADR-183 point 4: a layout difference is reported,
 * never hidden.
 */
export default function DeliveryAsSent() {
  const params = useParams()
  const sendId = Number(params.id)
  const asSent = useAsSent(Number(params.executionId))

  // 409 is an answer, not a failure: this execution has no delivery record.
  const notSent = asSent.error instanceof HttpError && asSent.error.status === 409

  return (
    <>
      <p>
        <Link to={`/deliveries/${sendId}`}>← The send</Link>
      </p>
      <h1>As sent</h1>
      {notSent ? (
        <p role="status" className="muted">
          There is nothing to show: this recipient was not sent this message, or
          it was sent before delivery records existed.
        </p>
      ) : (
        <ScreenState query={asSent}>
          {asSent.data && (
            <>
              {!asSent.data.templates_match && (
                <p role="alert">
                  The templates have changed since this was sent. The content below
                  is exactly what was sent; the layout is today's.
                </p>
              )}
              {!asSent.data.hash_matches && (
                <p role="alert">
                  This rebuild is not byte-identical to what was sent.
                </p>
              )}

              <dl className="facts">
                <dt>Channel</dt>
                <dd>{asSent.data.channel}</dd>
                <dt>Sent</dt>
                <dd>{formatDate(asSent.data.sent_at)}</dd>
                {/*
                  The envelope is rendered generically, like an approval's rows:
                  email carries subject and preheader, another channel carries
                  its own keys, and a client that knew the shapes would need
                  editing for every channel added.
                */}
                {Object.entries(asSent.data.envelope).map(([key, value]) => (
                  <div key={key} style={{ display: 'contents' }}>
                    <dt>{key}</dt>
                    <dd>{String(value ?? '—')}</dd>
                  </div>
                ))}
              </dl>

              {asSent.data.body != null && (
                <>
                  <h2>Message</h2>
                  {/*
                    **Sandboxed with every permission withheld.**

                    The body is email HTML: it was written for a mail client,
                    not for this application's origin. An empty `sandbox`
                    attribute gives the frame a unique origin of its own and
                    refuses scripts, forms and popups, so nothing in a message
                    can read this session or act as the person viewing it.
                    `no-referrer` keeps the images it loads from learning which
                    screen they were viewed on.
                  */}
                  <iframe
                    title="The message as sent"
                    sandbox=""
                    referrerPolicy="no-referrer"
                    srcDoc={asSent.data.body}
                    style={{ width: '100%', height: '40rem', border: '1px solid #ccc' }}
                  />
                </>
              )}

              {asSent.data.fields && (
                <>
                  <h2>Fields</h2>
                  <dl className="facts">
                    {Object.entries(asSent.data.fields).map(([key, value]) => (
                      <div key={key} style={{ display: 'contents' }}>
                        <dt>{key}</dt>
                        <dd>{String(value ?? '—')}</dd>
                      </div>
                    ))}
                  </dl>
                </>
              )}

              <h2>Modules</h2>
              <DataTable
                label="Modules in this message"
                columns={moduleColumns}
                items={asSent.data.modules.map((m) => ({ ...m, id: m.module_id }))}
                emptyMessage="This message had no modules."
              />
            </>
          )}
        </ScreenState>
      )}
    </>
  )
}
