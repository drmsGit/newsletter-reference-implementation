import { useState } from 'react'
import { Button, Dialog, Heading, Modal, ModalOverlay } from 'react-aria-components'
import { useNavigate, useParams, useSearchParams } from 'react-router'
import { useQueryClient } from '@tanstack/react-query'

import {
  keys,
  useAudienceGroup,
  useAudiencePreview,
  useDeleteAudience,
  useRecalculate,
  useSaveAudience,
  useSettings,
  type AudienceGroup,
} from '../api/resources'
import { HttpError } from '../api/session'
import Choice from '../components/Choice'
import DataTable from '../components/DataTable'
import DetailSection from '../components/DetailSection'
import { AutosaveField, SaveState, fieldError } from '../components/EditorFields'
import Fact from '../components/Fact'
import { DialogActions } from '../components/NewDialog'
import { SearchBox, useSearch } from '../components/RecipientSearch'
import ScreenState from '../components/ScreenState'
import AudiencePeople, { PEOPLE_PAGE } from './AudiencePeople'
import AudienceRules from './AudienceRules'
import { formatDate } from './Campaigns'

/**
 * The group's page is its editor (task-297; Audience Write Surface decision
 * 1), not a separate edit mode: name and description save on leaving the
 * field, the rules and the people added by hand are edited in place, and the
 * arithmetic beside them is read again after every saved change, on the
 * chosen channel. Every write states the group's one version (decision 10).
 */
export default function AudienceDetail() {
  const { id } = useParams()
  const groupId = Number(id)
  const group = useAudienceGroup(groupId)
  const queryClient = useQueryClient()
  const reload = () => void queryClient.invalidateQueries({ queryKey: keys.audienceGroup(groupId) })
  const [channel, channels, setChannel] = useChannel()

  return (
    // Column 3 of the audiences (task-372, render 37). Who a send reaches
    // follows the rules and the people (decision 18, 2026-10-17): no room for
    // it beside them in the details column.
    <div className="detail">
      <div className="detail-scroll">
        <ScreenState query={group}>
          {group.data && (
            <>
              <div className="detail-head">
                <h2>{group.data.name}</h2>
              </div>
              <div className="group card-rows">
                <Details group={group.data} reload={reload} />
                {channels.length > 1 && (
                  <Choice
                    label="Channel"
                    options={channels.map((c) => ({ id: c, name: c }))}
                    selected={channel}
                    onChange={setChannel}
                  />
                )}
              </div>
              <AudienceRules groupId={groupId} reload={reload} />
              <AudiencePeople groupId={groupId} channel={channel} reload={reload} />
              <Reach groupId={groupId} channel={channel} />
              <Delete group={group.data} reload={reload} />
            </>
          )}
        </ScreenState>
      </div>
    </div>
  )
}

/**
 * The channel every number and mark on the page is about (ADR-176 point 5:
 * there is no channel-less answer): the first switched-on one, or the one in
 * the URL, with the switch visible.
 */
function useChannel(): [string, string[], (next: string) => void] {
  const [params, setParams] = useSearchParams()
  const settings = useSettings()
  const channels = (settings.data?.channels ?? []).filter((c) => c.available).map((c) => c.name)
  const channel = params.get('channel') ?? channels[0] ?? 'email'
  const set = (next: string) => {
    const updated = new URLSearchParams(params)
    updated.set('channel', next)
    // The people added by hand are marked per channel: their page starts again.
    updated.delete(PEOPLE_PAGE)
    setParams(updated)
  }
  return [channel, channels, set]
}

/** Name and description, each saved on leaving the field; only what changed is sent. */
function Details({ group, reload }: { group: AudienceGroup; reload: () => void }) {
  const save = useSaveAudience(group.id)
  const recalculate = useRecalculate(group.id)
  return (
    <>
      <AutosaveField
        field={{ name: 'name', label: 'Name', type: 'text' }}
        value={group.name}
        onSave={(name) => save.mutate({ name })}
        error={fieldError(save.error, 'name')}
      />
      <AutosaveField
        field={{ name: 'description', label: 'Description', type: 'text' }}
        value={group.description ?? ''}
        onSave={(description) => save.mutate({ description: description.trim() || null })}
        error={fieldError(save.error, 'description')}
      />
      <SaveState mutation={save} what="this audience" reload={reload} />
      <dl className="fact-list">
        <Fact label="Created">{formatDate(group.created_at)}</Fact>
        <Fact label="Updated">{formatDate(group.updated_at)}</Fact>
      </dl>
      {group.source_campaign_id != null && (
        // Manual, always (Manager Workflow 4.7): the suggestion is never redone behind the manager's back.
        <p className="recalculate">
          <Button isDisabled={recalculate.isPending} onPress={() => recalculate.mutate(undefined)}>
            Recalculate from campaign
          </Button>{' '}
          <span className="muted field-note">
            Brings the suggested rules up to date with the campaign&apos;s content: new topics are added, dropped
            ones removed, the rest kept as you set them. Your own rules stay.
          </span>
          {recalculate.isSuccess && <span role="status"> The suggested rules match the campaign now.</span>}
          <SaveState mutation={recalculate} what="this audience" reload={reload} />
        </p>
      )}
    </>
  )
}

/**
 * Delete, after a confirmation (decision 8). A group a send uses — planned or
 * sent — is refused with the server's explanation naming the sends; that 409
 * is an answer, not somebody else's edit, so it offers no "their version".
 */
function Delete({ group, reload }: { group: AudienceGroup; reload: () => void }) {
  const [open, setOpen] = useState(false)
  const remove = useDeleteAudience(group.id)
  const navigate = useNavigate()
  const refused = remove.error instanceof HttpError ? remove.error : undefined
  // The server's own words for a group in use (`GroupInUse`); any other 409 is a stale version.
  const inUse = refused?.status === 409 && refused.detail?.startsWith('Used by')
  return (
    <DetailSection id="audience-delete" title="Delete">
      <div>
        <Button className="btn-destructive" onPress={() => setOpen(true)}>
          Delete audience
        </Button>
      </div>
      <ModalOverlay
        isOpen={open}
        onOpenChange={(next) => {
          setOpen(next)
          if (!next) remove.reset()
        }}
        isDismissable
        className="preview-overlay"
      >
        <Modal className="create-modal">
          <Dialog role="alertdialog" aria-label={`Delete ${group.name}`}>
            <Heading slot="title">Delete “{group.name}”?</Heading>
            <p>Its rules and the people added by hand go with it. This cannot be undone.</p>
            {inUse ? (
              <p role="alert">{refused?.detail}</p>
            ) : (
              <SaveState mutation={remove} what="this audience" reload={reload} />
            )}
            <DialogActions onCancel={() => setOpen(false)}>
              <Button
                isDisabled={remove.isPending || inUse}
                onPress={() => remove.mutate(undefined, { onSuccess: () => navigate('/audiences') })}
              >
                Delete
              </Button>
            </DialogActions>
          </Dialog>
        </Modal>
      </ModalOverlay>
    </DetailSection>
  )
}

type Arithmetic = NonNullable<ReturnType<typeof useAudiencePreview>['data']>['arithmetic']

/**
 * How the audience on one channel is arrived at (task-213; Manager Workflow
 * interview Q4.3): the working, not just the total, so a manager can see where
 * people went — a hand-add an exclusion overrode included (ADR-176 point 1).
 * The server's terms add up to the total; "not agreed" is a count only.
 */
function Working({ arithmetic: a, channel }: { arithmetic: Arithmetic; channel: string }) {
  const rows: [string, string, string?][] = [
    ['Match the rules', String(a.matched_rules)],
    [`Not agreed to ${channel}`, `−${a.not_agreed}`],
    ['Added by hand', `+${a.added_by_hand}`],
    ['Removed by exclusion segments', `−${a.removed_by_exclusion}`,
      a.removed_hand_added > 0 ? ` (${a.removed_hand_added} of them added by hand)` : undefined],
    [`Added by hand, not agreed to ${channel}`, `−${a.dropped_by_consent}`],
    ['In the audience', String(a.total)],
  ]
  return (
    <table className="working" aria-label={`How the audience on ${channel} is arrived at`}>
      <tbody>
        {rows.map(([label, value, note], index) => (
          // The last row is the total the others add up to.
          <tr key={label} className={index === rows.length - 1 ? 'row-total' : undefined}>
            <th scope="row">
              {label}
              {note && <span className="muted">{note}</span>}
            </th>
            <td>{value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/**
 * Who a send to this group would reach, on one channel (2026-10-03).
 *
 * **There is no channel-less answer** (ADR-176 point 5): a group resolves to
 * different people per channel, so the channel is chosen first, from the
 * deployment's switched-on channels as the server lists them.
 *
 * The counts are the server's -- resolved, reachable, why the rest drop, by
 * stage. Below them, **a sample and a search, not a paged list**, decided with
 * the user: twenty reachable recipients, or the ones matching what the manager
 * typed (identifier or address), and how many match. Resolving and the search
 * both happen on the server, so a segment of thousands is searched whole.
 */
function Reach({ groupId, channel }: { groupId: number; channel: string }) {
  // Its own name in the address, `?who=`: the list beside it searches by `?q=`.
  const q = useSearch(WHO)
  const preview = useAudiencePreview(groupId, channel, q)

  return (
    <DetailSection id="reach" title="Who a send reaches">
      <ScreenState query={preview}>
        {preview.data && (
          <>
            <Working arithmetic={preview.data.arithmetic} channel={channel} />
            <p className="muted">As of now: a send works this out again when it goes out.</p>
            <dl className="fact-list">
              <Fact label={`Reachable on ${channel}`}>{preview.data.reachable_count}</Fact>
              {Object.entries(preview.data.dropped_by_stage).map(([stage, count]) => (
                <Fact key={stage} label={`Not reachable: ${stage}`}>
                  {count}
                </Fact>
              ))}
            </dl>
            {/* `/` stays with the list's search (task-266: one per screen). */}
            <SearchBox
              label="Find a recipient (identifier or address)"
              compact
              param={WHO}
              pageParam={null}
              shortcut={false}
            />
            <DataTable
              label={`Reachable on ${channel}`}
              columns={[
                { key: 'who', header: 'Recipient', isRowHeader: true, render: (r) => r.external_id },
                { key: 'address', header: 'Address', render: (r) => r.address ?? '—' },
                { key: 'language', header: 'Language', render: (r) => r.language ?? '—' },
              ]}
              items={preview.data.sample.map((r) => ({ ...r, id: r.recipient_id }))}
              emptyMessage={q ? 'Nobody reachable matches that.' : 'Nobody in this group is reachable on this channel.'}
            />
            <p className="muted" role="status">
              {q
                ? `${preview.data.sample_matching} matching “${q}”, showing ${preview.data.sample.length}.`
                : `Showing ${preview.data.sample.length} of ${preview.data.reachable_count}. Search to find someone.`}
            </p>
          </>
        )}
      </ScreenState>
    </DetailSection>
  )
}

/** The address's name for this page's recipient search (task-372: the list beside it has `q`). */
const WHO = 'who'
