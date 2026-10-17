import { useState } from 'react'
import { Button, Dialog, Heading, Input, Label, Modal, ModalOverlay, Text, TextArea, TextField } from 'react-aria-components'
import { Link } from 'react-router'

import {
  useAddPerson,
  useAudienceMembers,
  usePastePeople,
  usePastePreview,
  useRemovePerson,
  type AudienceGroupMember,
} from '../api/resources'
import { HttpError } from '../api/session'
import { DialogActions } from '../components/NewDialog'
import DataTable from '../components/DataTable'
import DetailSection from '../components/DetailSection'
import { SaveState } from '../components/EditorFields'
import Pager, { useOffset } from '../components/Pager'
import RecipientPicker, { type PickedRecipient } from '../components/RecipientPicker'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'

/**
 * The people added by hand (Audience Write Surface decision 5): each with the
 * reason, who added them and when, and — on the channel shown — the leave-out
 * rules that remove them anyway, since an exclusion beats a hand-add (ADR-176
 * point 1). Add one with the recipient search, or paste a list; remove one.
 * Adding and removing take effect at once.
 */
/** The address's name for this list's page (task-372: the audiences list beside it has `offset`). */
export const PEOPLE_PAGE = 'people'

export default function AudiencePeople({
  groupId,
  channel,
  reload,
}: {
  groupId: number
  channel: string
  reload: () => void
}) {
  const members = useAudienceMembers(groupId, channel, useOffset(PEOPLE_PAGE))
  const remove = useRemovePerson(groupId)
  const [pasted, setPasted] = useState<string | null>(null)

  return (
    <DetailSection id="people" title="Added by hand">
      <ScreenState query={members}>
        <DataTable<AudienceGroupMember>
          label="People added by hand"
          columns={[
            {
              key: 'who',
              header: 'Person',
              isRowHeader: true,
              render: (m) => <Link to={`/recipients/${m.recipient_id}`}>{m.external_id ?? `#${m.recipient_id}`}</Link>,
            },
            { key: 'reason', header: 'Reason', render: (m) => m.reason || <span className="muted">—</span> },
            { key: 'by', header: 'Added by', render: (m) => m.added_by || <span className="muted">—</span> },
            { key: 'when', header: 'Added', render: (m) => formatDate(m.added_at) },
            {
              key: 'left-out',
              header: `On ${channel}`,
              render: (m) =>
                m.left_out_by.length > 0
                  ? `Left out by ${m.left_out_by.map((l) => `“${l}”`).join(', ')} on ${channel}`
                  : '',
            },
            {
              key: 'remove',
              header: '',
              render: (m) => (
                <Button
                  className="btn-plain btn-sm"
                  aria-label={`Remove ${m.external_id ?? m.recipient_id}`}
                  isDisabled={remove.isPending}
                  onPress={() => remove.mutate(m.recipient_id)}
                >
                  Remove
                </Button>
              ),
            },
          ]}
          items={members.data?.items ?? []}
          emptyMessage="Nobody added by hand."
        />
        <Pager page={members.data} param={PEOPLE_PAGE} />
      </ScreenState>
      <SaveState mutation={remove} what="this audience" reload={reload} />
      <AddOne groupId={groupId} reload={reload} />
      <div>
        <PastePeople groupId={groupId} channel={channel} onAdded={setPasted} reload={reload} />
      </div>
      {pasted && (
        <p role="status" className="muted">
          {pasted}
        </p>
      )}
    </DetailSection>
  )
}

function AddOne({ groupId, reload }: { groupId: number; reload: () => void }) {
  const add = useAddPerson(groupId)
  const [chosen, setChosen] = useState<PickedRecipient | null>(null)
  const [reason, setReason] = useState('')
  if (!chosen) return <RecipientPicker label="Add a person (identifier or address)" onChoose={setChosen} />
  return (
    <div className="recipient-choice">
      <p>
        Adding <strong>{chosen.label}</strong>.
      </p>
      <TextField value={reason} onChange={setReason}>
        <Label>Reason (optional)</Label>
        <Input />
      </TextField>
      <Button
        isDisabled={add.isPending}
        onPress={() =>
          add.mutate(
            { recipientId: chosen.id, reason: reason.trim() },
            {
              onSuccess: () => {
                setChosen(null)
                setReason('')
              },
            },
          )
        }
      >
        Add
      </Button>{' '}
      <Button onPress={() => setChosen(null)}>Choose someone else</Button>
      <SaveState mutation={add} what="this audience" reload={reload} />
    </div>
  )
}

/**
 * "Paste people" (decision 6): a list of identifiers or addresses, a report of
 * what it would do, then "Add N". Nobody is created — the CRM owns people
 * (ADR-120) — and people who have not agreed are added but counted, not
 * listed (ADR-163's addendum).
 */
function PastePeople({
  groupId,
  channel,
  onAdded,
  reload,
}: {
  groupId: number
  channel: string
  onAdded: (message: string) => void
  reload: () => void
}) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [reason, setReason] = useState('')
  const check = usePastePreview(groupId)
  const apply = usePastePeople(groupId)
  const report = check.data

  function close() {
    setOpen(false)
    setText('')
    setReason('')
    check.reset()
    apply.reset()
  }

  return (
    <>
      <Button onPress={() => setOpen(true)}>Paste people</Button>
      <ModalOverlay isOpen={open} onOpenChange={(next) => (next ? setOpen(true) : close())} isDismissable className="preview-overlay">
        <Modal className="create-modal">
          <Dialog aria-label="Paste people">
            <Heading slot="title">Paste people</Heading>
            <TextField
              value={text}
              onChange={(next) => {
                setText(next)
                check.reset()
              }}
            >
              <Label>Identifiers or email addresses</Label>
              <TextArea rows={8} style={{ width: '100%' }} />
              <Text slot="description" className="muted">
                Separated by new lines, commas, semicolons or spaces. An entry with @ is matched as an email address.
                Up to 5,000; a bigger list belongs in the CRM as a segment.
              </Text>
            </TextField>
            <TextField value={reason} onChange={setReason}>
              <Label>Reason (optional)</Label>
              <Input />
            </TextField>
            {check.isError && (
              <p role="alert">{(check.error instanceof HttpError && check.error.detail) || 'The list could not be checked.'}</p>
            )}
            {report && (
              <div role="status">
                <p>
                  {report.to_add} will be added, {report.already_in} already in.
                </p>
                {report.not_agreed > 0 && (
                  <p>
                    {report.not_agreed} have not agreed to {report.channel}: added, but will not receive it there.
                  </p>
                )}
                {report.not_found.length > 0 && (
                  <>
                    <p>{report.not_found.length} not found:</p>
                    <ul>
                      {report.not_found.map((entry) => (
                        <li key={entry}>{entry}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}
            <SaveState mutation={apply} what="this audience" reload={reload} />
            {/* One action at the foot: Check, then Add N once the list is checked
                (task-392 item 14; render 45's Cancel and action). */}
            <DialogActions onCancel={close}>
              {report ? (
                <Button
                  isDisabled={report.to_add === 0 || apply.isPending}
                  onPress={() =>
                    apply.mutate(
                      { text, reason: reason.trim() },
                      {
                        onSuccess: (result) => {
                          onAdded(
                            `Added ${result.added} (${result.already_in} already in, ${result.not_found} not found).`,
                          )
                          close()
                        },
                      },
                    )
                  }
                >
                  Add {report.to_add}
                </Button>
              ) : (
                <Button isDisabled={!text.trim() || check.isPending} onPress={() => check.mutate({ text, channel })}>
                  Check
                </Button>
              )}
            </DialogActions>
          </Dialog>
        </Modal>
      </ModalOverlay>
    </>
  )
}
