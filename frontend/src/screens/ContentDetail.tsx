import { useState } from 'react'
import { Button, Switch } from 'react-aria-components'
import { Link, useNavigate, useParams } from 'react-router'

import {
  useCampaignsUsing,
  useContentAssignments,
  useContentFields,
  useContentReach,
  useContentRecord,
  useContentVersions,
  useDuplicateContent,
  useDuplicateTargets,
  useEditAssignments,
  useMarkReady,
  useSaveContentRecord,
  useSetContentStatus,
  useSetMachineReady,
  type ContentRecordDetail,
} from '../api/resources'
import CategoryChoice from '../components/CategoryChoice'
import Choice from '../components/Choice'
import { HttpError } from '../api/session'
import { AutosaveField, SaveState, fieldError } from '../components/EditorFields'
import PublishState from '../components/PublishState'
import ScreenState from '../components/ScreenState'
import { STAGE_LABEL } from './Monitoring'

type ContentField = NonNullable<ReturnType<typeof useContentFields>['data']>[number]

/**
 * A content record's page, where the record is written (task-279) — the
 * primary authoring surface (Manager Workflow Q4), as the Content Write
 * Surface final design pass decided it:
 *
 * - Every field saves on blur with the record's version (decision 1, the
 *   editor's D1): changing the catalogue is this page's purpose, and nothing
 *   reaches a send until it is published.
 * - One passive line says how far an edit reaches; no confirmations (2).
 * - The composer's publish notice, and a read-only list of versions (3).
 * - Channels as labelled sections down the page, each field in the modules'
 *   declared order (MW Q2, task-276).
 * - Status and duplicate now; delete waits for task-117 (7).
 * - Categories with their 1-10 scores, changed in place (5, task-280).
 * - A Ready switch per channel and a Machine ready switch by the status
 *   (task-285, the Channel Readiness final design pass).
 */
export default function ContentDetail() {
  const { id } = useParams()
  const recordId = Number(id)
  const record = useContentRecord(recordId)
  const fields = useContentFields()
  const [generation, setGeneration] = useState(0)

  return (
    <>
      <p>
        <Link to="/content">← Content</Link>
      </p>
      <ScreenState query={record}>
        {record.data && (
          <RecordPage
            // "Load their version" remounts the page, so every field starts
            // from what is stored. A field keeps its draft while its stored
            // value is unchanged, and after a refused save the value often is
            // unchanged (somebody else edited another field): the refused text
            // would stay on screen looking saved.
            key={generation}
            record={record.data}
            fields={fields.data ?? []}
            reload={() => {
              setGeneration((n) => n + 1)
              record.refetch()
            }}
          />
        )}
      </ScreenState>
    </>
  )
}

function RecordPage({
  record,
  fields,
  reload,
}: {
  record: ContentRecordDetail
  fields: ContentField[]
  reload: () => void
}) {
  const save = useSaveContentRecord(record.id)
  const content = (record.content ?? {}) as Record<string, unknown>
  const channels = [...new Set(fields.map((f) => f.channel ?? 'other'))]
  const defined = new Set(fields.map((f) => f.name))
  // Keys no definition names: shown, never hidden, but not editable here —
  // PATCH writes by channel group, and these are in none.
  const undefinedKeys = Object.keys(content).filter((key) => !defined.has(key)).sort()

  return (
    <>
      <h1>{record.title}</h1>
      <StatusAndDuplicate record={record} />

      <div className="record-notices">
        <PublishState recordId={record.id} detail={record} />
        <ReachLine recordId={record.id} />
      </div>

      <section aria-labelledby="record-details-heading">
        <h2 id="record-details-heading">Details</h2>
        <AutosaveField
          field={{ name: 'title', label: 'Title', type: 'text', required: true }}
          value={record.title}
          onSave={(title) => title.trim() && save.mutate({ title })}
          error={fieldError(save.error, 'title')}
        />
        <AutosaveField
          field={{ name: 'description', label: 'Description', type: 'text' }}
          value={record.description ?? ''}
          onSave={(description) => save.mutate({ description })}
          error={fieldError(save.error, 'description')}
        />
      </section>

      {channels.map((channel) => (
        <details key={channel} open className="record-channel">
          <summary>
            <h2>{channel.charAt(0).toUpperCase() + channel.slice(1)}</h2>
          </summary>
          {channel !== 'other' && <ReadyFor record={record} channel={channel} />}
          {fields
            .filter((f) => (f.channel ?? 'other') === channel)
            .map((field) => (
              <AutosaveField
                key={field.name}
                field={field}
                value={typeof content[field.name] === 'string' ? (content[field.name] as string) : ''}
                // Only this channel's fields may be cleared by this save (B19).
                onSave={(value) => save.mutate({ content: { [field.name]: value }, groups: [channel] })}
                error={fieldError(save.error, field.name)}
              />
            ))}
        </details>
      ))}

      {undefinedKeys.length > 0 && (
        <section aria-labelledby="record-other-heading">
          <h2 id="record-other-heading">Other stored values</h2>
          <p className="muted">No field definition names these, so they are shown but not edited here.</p>
          <dl className="facts">
            {undefinedKeys.map((key) => (
              <div key={key} style={{ display: 'contents' }}>
                <dt>{key}</dt>
                <dd>{typeof content[key] === 'string' ? (content[key] as string) : JSON.stringify(content[key])}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}
      <SaveState mutation={save} reload={reload} what="the record" />

      <Categories recordId={record.id} />
      <Versions recordId={record.id} fields={fields} />
      <UsedIn recordId={record.id} />
    </>
  )
}

/** Decision 2: how far an edit reaches, said once, passively — no prompt per field. */
function ReachLine({ recordId }: { recordId: number }) {
  const reach = useContentReach(recordId)
  if (!reach.data) return null
  const { count } = reach.data
  return (
    <p className="muted reach-line">
      {count === 0
        ? 'No unsent campaign uses this record. '
        : `Edits here change this record for ${count} unsent campaign${count === 1 ? '' : 's'}. `}
      Sends use the published version. <a href="#used-in-heading">Where it is used</a>
    </p>
  )
}

/** Status (the safe way to retire a record) and duplicating into a brand (decision 7). */
function StatusAndDuplicate({ record }: { record: ContentRecordDetail }) {
  const status = useSetContentStatus(record.id)
  const targets = useDuplicateTargets(record.id)
  const duplicate = useDuplicateContent(record.id)
  const navigate = useNavigate()
  const [target, setTarget] = useState<string | null>(null)
  const [copiedTo, setCopiedTo] = useState<string | null>(null)
  const active = record.status === 'active'
  const options = targets.data ?? []
  const chosen = target ?? (options[0] ? String(options[0].id) : null)

  return (
    <div className="record-actions">
      <span className="muted">{active ? 'Active' : 'Inactive'}</span>{' '}
      <Button
        isDisabled={status.isPending}
        onPress={() => status.mutate(active ? 'inactive' : 'active')}
      >
        {active ? 'Deactivate' : 'Reactivate'}
      </Button>
      {!active && (
        <span className="muted"> Inactive records are not offered by the picker or chosen by a slot.</span>
      )}
      <SaveState mutation={status} what="the record" />
      <MachineReady record={record} />
      {options.length > 0 && chosen && (
        <div className="record-duplicate">
          <Choice
            label="Duplicate into"
            options={options.map((b) => ({ id: String(b.id), name: b.name }))}
            selected={chosen}
            onChange={setTarget}
          />
          <Button
            isDisabled={duplicate.isPending}
            onPress={() => {
              const brand = options.find((b) => String(b.id) === chosen)
              duplicate.mutate(Number(chosen), {
                onSuccess: (copy) => {
                  // A copy in this brand opens; one in another brand cannot be
                  // opened from here, so it is said where it went.
                  if (brand && !brand.crossing) navigate(`/content/${copy.id}`)
                  else setCopiedTo(brand?.name ?? 'the other brand')
                },
              })
            }}
          >
            Duplicate
          </Button>
          {copiedTo && (
            <p role="status">
              Copied to {copiedTo}. The copy has no published version, so it cannot be sent until it is
              published there.
            </p>
          )}
          <SaveState mutation={duplicate} what="the copy" />
        </div>
      )}
    </div>
  )
}

/**
 * A person's assertion that the record may go out on this channel (ADR-174).
 * The warning is the server's — it fires when the record can fill no module of
 * the channel — and it informs, never blocks (point 2). The switch shows what
 * is stored: it moves once the record has been re-read, not before. Read-only
 * while a change is saved, never disabled: a disabled input drops keyboard
 * focus to the page.
 */
function ReadyFor({ record, channel }: { record: ContentRecordDetail; channel: string }) {
  const mark = useMarkReady(record.id, channel)
  const stored = record.readiness.find((r) => r.channel === channel)
  const title = channel.charAt(0).toUpperCase() + channel.slice(1)
  return (
    <div className="readiness">
      <Switch isSelected={!!stored} isReadOnly={mark.isPending} onChange={(ready) => mark.mutate(ready)}>
        <span className="switch__indicator" aria-hidden="true" />
        Ready for {title}
      </Switch>
      {stored && (
        <p className="muted">
          Marked ready by {stored.marked_by ?? 'unknown'} · {new Date(stored.marked_at).toLocaleString()}
        </p>
      )}
      {stored?.warning && <p className="readiness__warning">{stored.warning}</p>}
      <SaveState mutation={mark} what={`readiness for ${title}`} />
    </div>
  )
}

/** ADR-179 point 2: the human gate on what a machine may pick. People only. */
function MachineReady({ record }: { record: ContentRecordDetail }) {
  const set = useSetMachineReady(record.id)
  return (
    <div className="readiness">
      <Switch isSelected={record.machine_ready} isReadOnly={set.isPending} onChange={(on) => set.mutate(on)}>
        <span className="switch__indicator" aria-hidden="true" />
        Machine ready
      </Switch>
      <span className="muted"> May a decision slot pick this without a person choosing it.</span>
      <SaveState mutation={set} what="machine ready" />
    </div>
  )
}

const SCORES = Array.from({ length: 10 }, (_, index) => ({ id: String(index + 1), name: String(index + 1) }))

/**
 * A record's categories (decision 5, ADR-080's 2026-10-04 addendum): each
 * score a 1-10 choice changed in place — never remove-and-re-add, which would
 * take the record out of the category for a moment — removed per row, and
 * added from the hierarchy the picker uses. Categories are only assigned
 * here, never created: they build each recipient's interest profile, and a
 * label made for finding content belongs to facets (ADR-175).
 */
function Categories({ recordId }: { recordId: number }) {
  const assignments = useContentAssignments(recordId)
  const edit = useEditAssignments(recordId)
  const [adding, setAdding] = useState<number | null>(null)
  const [score, setScore] = useState('10')
  const assigned = new Set((assignments.data ?? []).map((a) => a.category_id))

  return (
    <section aria-labelledby="categories-heading">
      <h2 id="categories-heading">Categories</h2>
      <p className="muted">
        Categories build each recipient&apos;s interest profile. For finding content, facets will follow.
      </p>
      <ScreenState query={assignments}>
        {assignments.data && assignments.data.length === 0 ? (
          <p className="muted">No categories yet.</p>
        ) : (
          <ul className="assignments">
            {assignments.data?.map((assignment) => (
              <li key={assignment.assignment_id} className="assignment">
                <span className="assignment__name">{assignment.name}</span>
                <Choice
                  label={`Score for ${assignment.name}`}
                  options={SCORES}
                  selected={String(assignment.score ?? 10)}
                  onChange={(next) =>
                    edit.mutate({ kind: 'score', assignmentId: assignment.assignment_id, score: Number(next) })
                  }
                />
                <Button
                  aria-label={`Remove ${assignment.name}`}
                  isDisabled={edit.isPending}
                  onPress={() => edit.mutate({ kind: 'remove', assignmentId: assignment.assignment_id })}
                >
                  Remove
                </Button>
              </li>
            ))}
          </ul>
        )}
      </ScreenState>
      <div className="assignment-add">
        <CategoryChoice
          label="Add a category"
          noneLabel="Choose a category"
          selected={adding}
          onChange={setAdding}
          exclude={assigned}
        />
        <Choice label="Score" options={SCORES} selected={score} onChange={setScore} />
        <Button
          isDisabled={adding == null || edit.isPending}
          onPress={() =>
            adding != null &&
            edit.mutate(
              { kind: 'assign', categoryId: adding, score: Number(score) },
              { onSuccess: () => setAdding(null) },
            )
          }
        >
          Add
        </Button>
      </div>
      <p className="muted">1 = barely in the category, 10 = squarely in it.</p>
      {edit.isError && (
        // The server's own words, not SaveState's: a 409 here is "already
        // assigned" (somebody added it meanwhile), not a stale version, and a
        // refused score arrives as a field error SaveState would not show.
        <p role="alert">Not saved: {edit.error instanceof HttpError ? edit.error.detail : 'the change failed.'}</p>
      )}
    </section>
  )
}

/** Decision 3: what each published version said — read only; no restore or compare. */
function Versions({ recordId, fields }: { recordId: number; fields: ContentField[] }) {
  const versions = useContentVersions(recordId)
  const labelOf = new Map(fields.map((f) => [f.name, f.label ?? f.name]))
  return (
    <section aria-labelledby="versions-heading">
      <h2 id="versions-heading">Published versions</h2>
      <ScreenState query={versions}>
        {versions.data && versions.data.length === 0 ? (
          <p className="muted">Nothing published yet.</p>
        ) : (
          <ul className="versions">
            {versions.data?.map((version) => (
              <li key={version.id}>
                <details>
                  <summary>
                    Version {version.version_number}
                    <span className="muted">
                      {' '}
                      · {version.created_by ?? 'unknown'} ·{' '}
                      {version.created_at ? new Date(version.created_at).toLocaleString() : '—'}
                    </span>
                  </summary>
                  <dl className="facts">
                    {Object.entries((version.content ?? {}) as Record<string, unknown>).map(([key, value]) => (
                      <div key={key} style={{ display: 'contents' }}>
                        <dt>{labelOf.get(key) ?? key}</dt>
                        <dd>{typeof value === 'string' ? value : JSON.stringify(value)}</dd>
                      </div>
                    ))}
                  </dl>
                </details>
              </li>
            ))}
          </ul>
        )}
      </ScreenState>
    </section>
  )
}

/**
 * Where the record is used (task-267): every campaign with a module bound to
 * it, each variant that uses it linked to its editor and marked with its
 * stage, so a sent one reads as sent. Bound modules only, as the composer's
 * reach count counts them — a slot picks at send time, so it is not "using"
 * the record until then.
 */
function UsedIn({ recordId }: { recordId: number }) {
  const used = useCampaignsUsing(recordId)
  return (
    <section aria-labelledby="used-in-heading">
      <h2 id="used-in-heading">Used in</h2>
      <ScreenState query={used}>
        {used.data && used.data.items.length === 0 ? (
          <p className="muted">No campaign has a module bound to this record.</p>
        ) : (
          <ul className="used-in">
            {used.data?.items.map((campaign) => (
              <li key={campaign.id}>
                <Link to={`/campaigns/${campaign.id}`}>{campaign.name}</Link>:{' '}
                {campaign.variants.map((variant, index) => (
                  <span key={variant.id}>
                    {index > 0 && ', '}
                    <Link to={`/campaigns/${campaign.id}/variants/${variant.id}`}>{variant.name}</Link>{' '}
                    <span className={variant.stage === 'sent' ? 'used-in__sent' : 'muted'}>
                      ({variant.channel}, {STAGE_LABEL[variant.stage] ?? variant.stage})
                    </span>
                  </span>
                ))}
              </li>
            ))}
          </ul>
        )}
        {used.data && used.data.total > used.data.items.length && (
          <p className="muted">
            Showing {used.data.items.length} of {used.data.total} campaigns.
          </p>
        )}
        <p className="muted">A decision slot that may pick this record when it sends is not listed.</p>
      </ScreenState>
    </section>
  )
}
