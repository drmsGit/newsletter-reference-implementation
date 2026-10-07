import { Button, Input, Label, TextField } from 'react-aria-components'

import { useCampaigns, useSentSends } from '../api/resources'
import Choice from '../components/Choice'

/**
 * What a person did with a mailing, as one field of an audience rule
 * (task-298; ADR-188 points 4 and 5): what happened, to which mailing, and
 * when. One per rule, as the server stores it. "Did not" is not a choice
 * here: it is a leave-out rule (point 5), and the form says so.
 */
export type EngagementDraft = {
  event: 'received' | 'opened' | 'clicked'
  mailing: 'any' | 'campaign' | 'send'
  campaignId: number | null
  sendId: number | null
  when: 'any' | 'within' | 'more' | 'between'
  days: string
  from: string
  to: string
}

export const NEW_ENGAGEMENT: EngagementDraft = {
  event: 'received', mailing: 'any', campaignId: null, sendId: null, when: 'any', days: '', from: '', to: '',
}

type Stored = {
  event?: string
  send_instance_id?: number
  campaign_id?: number
  within_days?: number
  more_than_days?: number
  from?: string
  to?: string
}

/** The stored field as the form edits it. */
export function engagementDraftOf(raw: unknown): EngagementDraft | null {
  if (raw == null || typeof raw !== 'object') return null
  const e = raw as Stored
  return {
    event: e.event === 'opened' || e.event === 'clicked' ? e.event : 'received',
    mailing: e.send_instance_id != null ? 'send' : e.campaign_id != null ? 'campaign' : 'any',
    campaignId: e.campaign_id ?? null,
    sendId: e.send_instance_id ?? null,
    when: e.within_days != null ? 'within' : e.more_than_days != null ? 'more' : e.from || e.to ? 'between' : 'any',
    days: String(e.within_days ?? e.more_than_days ?? ''),
    from: e.from ?? '',
    to: e.to ?? '',
  }
}

/** The form's draft in the server's shape; a value left out is the server's to refuse by name. */
export function engagementOf(draft: EngagementDraft): Stored {
  const out: Stored = { event: draft.event }
  if (draft.mailing === 'campaign' && draft.campaignId != null) out.campaign_id = draft.campaignId
  if (draft.mailing === 'send' && draft.sendId != null) out.send_instance_id = draft.sendId
  if (draft.when === 'within') out.within_days = Number(draft.days)
  if (draft.when === 'more') out.more_than_days = Number(draft.days)
  if (draft.when === 'between') {
    if (draft.from) out.from = draft.from
    if (draft.to) out.to = draft.to
  }
  return out
}

const WHAT = [
  { id: 'received', name: 'Received it' },
  { id: 'opened', name: 'Opened it' },
  { id: 'clicked', name: 'Clicked in it' },
]
const WHICH = [
  { id: 'any', name: 'Any send' },
  { id: 'campaign', name: 'Any send of a campaign' },
  { id: 'send', name: 'One send' },
]
const WHEN = [
  { id: 'any', name: 'Any time' },
  { id: 'within', name: 'In the last … days' },
  { id: 'more', name: 'More than … days ago' },
  { id: 'between', name: 'Between two dates' },
]

/** A list of choices that still offers a stored id the first page does not hold. */
function withStored(options: { id: string; name: string }[], stored: number | null, none: string, named: string) {
  const all = [{ id: '', name: none }, ...options]
  if (stored != null && !options.some((o) => o.id === String(stored))) all.push({ id: String(stored), name: `${named} #${stored}` })
  return all
}

export function EngagementFields({
  draft,
  onChange,
  onRemove,
  kind,
}: {
  draft: EngagementDraft
  onChange: (draft: EngagementDraft) => void
  onRemove: () => void
  kind: 'include' | 'exclude'
}) {
  const campaigns = useCampaigns(0, '')
  const sends = useSentSends()
  const set = (changes: Partial<EngagementDraft>) => onChange({ ...draft, ...changes })
  return (
    <div role="group" aria-label="What they did with a mailing" className="rule__engagement">
      <Choice label="What happened" options={WHAT} selected={draft.event} onChange={(event) => set({ event: event as EngagementDraft['event'] })} />
      <Choice
        label="Which mailing"
        options={WHICH}
        selected={draft.mailing}
        onChange={(mailing) => set({ mailing: mailing as EngagementDraft['mailing'] })}
      />
      {draft.mailing === 'any' && (
        <p className="muted">Counts any send on the channel this audience is sent on.</p>
      )}
      {draft.mailing === 'campaign' && (
        <Choice
          label="Campaign"
          options={withStored(
            (campaigns.data?.items ?? []).map((c) => ({ id: String(c.id), name: c.name })),
            draft.campaignId, 'Choose a campaign', 'Campaign')}
          selected={draft.campaignId == null ? '' : String(draft.campaignId)}
          onChange={(id) => set({ campaignId: id ? Number(id) : null })}
        />
      )}
      {draft.mailing === 'send' && (
        <Choice
          label="Send"
          options={withStored(
            (sends.data?.items ?? []).map((s) => ({ id: String(s.id), name: s.name })),
            draft.sendId, 'Choose a send', 'Send')}
          selected={draft.sendId == null ? '' : String(draft.sendId)}
          onChange={(id) => set({ sendId: id ? Number(id) : null })}
        />
      )}
      <Choice label="When" options={WHEN} selected={draft.when} onChange={(when) => set({ when: when as EngagementDraft['when'] })} />
      {(draft.when === 'within' || draft.when === 'more') && (
        <TextField value={draft.days} onChange={(days) => set({ days })} inputMode="numeric">
          <Label>Days</Label>
          <Input />
        </TextField>
      )}
      {draft.when === 'between' && (
        <>
          <TextField value={draft.from} onChange={(from) => set({ from })}>
            <Label>From</Label>
            <Input type="date" />
          </TextField>
          <TextField value={draft.to} onChange={(to) => set({ to })}>
            <Label>To</Label>
            <Input type="date" />
          </TextField>
        </>
      )}
      {kind === 'include' && (
        // ADR-188 point 5: "did not" is a leave-out rule, explained where it is wanted.
        <p className="muted">To reach people who did not click, include who received it and leave out who clicked.</p>
      )}
      <Button onPress={onRemove}>Remove engagement</Button>
    </div>
  )
}

function CampaignName({ id }: { id: number }) {
  const campaigns = useCampaigns(0, '')
  return <>{campaigns.data?.items.find((c) => c.id === id)?.name ?? `campaign #${id}`}</>
}

function SendName({ id }: { id: number }) {
  const sends = useSentSends()
  return <>{sends.data?.items.find((s) => s.id === id)?.name ?? `send #${id}`}</>
}

const VERB = { received: 'Received', opened: 'Opened', clicked: 'Clicked in' }

/** "Clicked in Spring send in the last 30 days". */
export function EngagementSummary({ engagement }: { engagement: unknown }) {
  const draft = engagementDraftOf(engagement)
  if (!draft) return null
  const time =
    draft.when === 'within'
      ? ` in the last ${draft.days} days`
      : draft.when === 'more'
        ? ` more than ${draft.days} days ago`
        : draft.from && draft.to
          ? ` between ${draft.from} and ${draft.to}`
          : draft.from
            ? ` since ${draft.from}`
            : draft.to
              ? ` until ${draft.to}`
              : ''
  return (
    <>
      {VERB[draft.event]}{' '}
      {draft.mailing === 'send' && draft.sendId != null ? (
        <SendName id={draft.sendId} />
      ) : draft.mailing === 'campaign' && draft.campaignId != null ? (
        <>
          a send of <CampaignName id={draft.campaignId} />
        </>
      ) : (
        'any send'
      )}
      {time}
    </>
  )
}
