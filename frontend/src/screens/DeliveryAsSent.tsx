import { AlertTriangle } from 'lucide-react'
import { useParams } from 'react-router'

import { useAsSent, type DeliveryAsSent as AsSent } from '../api/resources'
import { HttpError } from '../api/session'
import BackTo from '../components/BackTo'
import DataTable, { type DataColumn } from '../components/DataTable'
import Fact from '../components/Fact'
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
  /**
   * A slot shows up to five picks, the module repeated once per pick: each
   * copy is its own row, numbered in the order it appeared (task-109).
   */
  { key: 'kind', header: 'Kind', render: (m) => (m.rank != null ? `${m.kind} (pick ${m.rank})` : m.kind) },
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
    // Column 3 of the deliveries, the send's row still open in the list (render 31).
    <div className="detail">
      <div className="detail-scroll">
        <div className="detail-head">
          <BackTo to={`/deliveries/${sendId}`} label="The send" />
          <h2>As sent</h2>
        </div>
        {notSent ? (
          <p role="status" className="muted quiet">
            There is nothing to show: this recipient was not sent this message, or
            it was sent before delivery records existed.
          </p>
        ) : (
          <ScreenState query={asSent}>
            {asSent.data && (
              <>
                {!asSent.data.templates_match && (
                  <p role="alert" className="group group-body notice">
                    <AlertTriangle size={16} strokeWidth={1.75} aria-hidden="true" className="notice-icon" />
                    <span>
                      The templates have changed since this was sent. The content below
                      is exactly what was sent; the layout is today's.
                    </span>
                  </p>
                )}
                {!asSent.data.hash_matches && (
                  <p role="alert" className="group group-body notice">
                    <AlertTriangle size={16} strokeWidth={1.75} aria-hidden="true" className="notice-icon" />
                    <span>This rebuild is not byte-identical to what was sent.</span>
                  </p>
                )}

                <dl className="group fact-list">
                  <Fact label="Channel">{asSent.data.channel}</Fact>
                  <Fact label="Sent">{formatDate(asSent.data.sent_at)}</Fact>
                  {/*
                    The envelope is rendered generically, like an approval's rows:
                    email carries subject and preheader, another channel carries
                    its own keys, and a client that knew the shapes would need
                    editing for every channel added.
                  */}
                  {Object.entries(asSent.data.envelope).map(([key, value]) => (
                    <Fact key={key} label={key}>
                      {String(value ?? '—')}
                    </Fact>
                  ))}
                </dl>

                {asSent.data.body != null && (
                  <section aria-labelledby="as-sent-message" className="detail-section">
                    <h3 id="as-sent-message" className="group-title">
                      Message
                    </h3>
                    <div className="preview-stage">
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
                        className="preview-frame preview-frame--message"
                        sandbox=""
                        referrerPolicy="no-referrer"
                        srcDoc={asSent.data.body}
                      />
                    </div>
                  </section>
                )}

                {asSent.data.fields && (
                  <section aria-labelledby="as-sent-fields" className="detail-section">
                    <h3 id="as-sent-fields" className="group-title">
                      Fields
                    </h3>
                    <dl className="group fact-list">
                      {Object.entries(asSent.data.fields).map(([key, value]) => (
                        <Fact key={key} label={key}>
                          {String(value ?? '—')}
                        </Fact>
                      ))}
                    </dl>
                  </section>
                )}

                <section aria-labelledby="as-sent-modules" className="detail-section">
                  <h3 id="as-sent-modules" className="group-title">
                    Modules
                  </h3>
                  <div className="group table-card">
                    <DataTable
                      label="Modules in this message"
                      columns={moduleColumns}
                      // A row per copy, so a module that repeated has several: the
                      // position in the list is the key, not the module id.
                      items={asSent.data.modules.map((m, index) => ({ ...m, id: index }))}
                      emptyMessage="This message had no modules."
                    />
                  </div>
                </section>
              </>
            )}
          </ScreenState>
        )}
      </div>
    </div>
  )
}
