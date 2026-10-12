import { useState } from 'react'
import { Button, Checkbox, Input, Label, TextField } from 'react-aria-components'
import { Link, useParams, useSearchParams } from 'react-router'

import {
  useAudienceGroups,
  useAudiencePreview,
  useComposition,
  useFireSend,
  useFreezeVariant,
  usePlanSend,
  useRecipientsNow,
  useSettings,
  useTestPlannedSend,
} from '../api/resources'
import { HttpError } from '../api/session'
import Choice from '../components/Choice'
import RecipientPicker, { type PickedRecipient } from '../components/RecipientPicker'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'

/**
 * Sending one variant, in four steps (task-67; ADR-183 addendum 2026-10-12).
 *
 * 1. **Freeze**: the snapshot is what will go out, shown as it will be sent.
 * 2. **Plan**: to whom, through which provider, and when.
 * 3. **Test**: the frozen email to one address, as a chosen recipient would
 *    get it. A test, not a delivery: nothing is counted or tracked.
 * 4. **Send**: the recipients as of now, and a button that says what it does.
 *
 * A person who may fire a send is its approval (ADR-174), so there is no
 * approval step here; sends fired by a CRM or n8n wait in the approvals inbox.
 * Where the screen is, is kept in the address (`?snapshot=`, `?send=`), so a
 * reload does not lose the frozen version or the planned send. Every rule --
 * the cap, the legal details, who may fire -- is the server's.
 */
export default function SendVariant() {
  const params = useParams()
  const campaignId = Number(params.id)
  const variantId = Number(params.variantId)
  const composition = useComposition(campaignId)
  const [search, setSearch] = useSearchParams()
  const snapshotId = search.get('snapshot') ? Number(search.get('snapshot')) : null
  const sendId = search.get('send') ? Number(search.get('send')) : null

  function go(changes: Record<string, string | null>) {
    const next = new URLSearchParams(search)
    for (const [key, value] of Object.entries(changes)) {
      if (value === null) next.delete(key)
      else next.set(key, value)
    }
    setSearch(next)
  }

  return (
    <>
      <p>
        <Link to={`/campaigns/${campaignId}`}>← Campaign</Link>
      </p>
      <ScreenState query={composition}>
        {composition.data &&
          (() => {
            const composed = composition.data.variants.find((v) => v.variant.id === variantId)
            if (!composed) return <p role="alert">This variant is not part of the campaign.</p>
            const { variant } = composed
            return (
              <>
                <h1>Send {variant.name}</h1>
                <p className="muted">
                  {composition.data.campaign.name} · {variant.channel}
                </p>
                <FreezeStep
                  variantId={variantId}
                  channel={variant.channel}
                  snapshotId={snapshotId}
                  onFrozen={(id) => go({ snapshot: String(id), send: null })}
                />
                {snapshotId != null && sendId == null && (
                  <PlanStep
                    snapshotId={snapshotId}
                    channel={variant.channel}
                    defaultName={composition.data.campaign.name}
                    onPlanned={(id) => go({ send: String(id) })}
                  />
                )}
                {sendId != null && variant.channel === 'email' && <TestStep sendId={sendId} />}
                {sendId != null && <SendStep sendId={sendId} campaignId={campaignId} />}
              </>
            )
          })()}
      </ScreenState>
    </>
  )
}

function refused(error: unknown, action: string) {
  if (error instanceof HttpError && error.status === 403) return `You do not have permission to ${action}.`
  return `${(error instanceof HttpError && error.detail) || 'The server refused it.'}`
}

/** Step 1: freeze the variant, and show exactly what will go out. */
function FreezeStep({
  variantId,
  channel,
  snapshotId,
  onFrozen,
}: {
  variantId: number
  channel: string
  snapshotId: number | null
  onFrozen: (id: number) => void
}) {
  const freeze = useFreezeVariant(variantId)
  return (
    <section aria-labelledby="step-freeze">
      <h2 id="step-freeze">1. Freeze this version</h2>
      <p className="muted">
        Freezing takes the variant as it is now. What you see below is what goes out; later edits need a new freeze.
      </p>
      <Button onPress={() => freeze.mutate(undefined, { onSuccess: (s) => onFrozen(s.id) })} isDisabled={freeze.isPending}>
        {freeze.isPending ? 'Freezing…' : snapshotId == null ? 'Freeze this version' : 'Freeze again'}
      </Button>
      {freeze.error != null && <p role="alert">Not frozen: {refused(freeze.error, 'freeze it')}</p>}
      {snapshotId != null &&
        (channel === 'email' ? (
          <iframe
            title="The frozen email"
            className="frozen-email"
            src={`/snapshots/${snapshotId}/html`}
            sandbox=""
            style={{ width: '100%', height: 480, border: '1px solid currentColor' }}
          />
        ) : (
          <p className="muted" role="status">
            Frozen (#{snapshotId}). A push is filled per recipient; the preview shows it for one person.
          </p>
        ))}
    </section>
  )
}

/** Step 2: to whom, through which provider, and when. */
function PlanStep({
  snapshotId,
  channel,
  defaultName,
  onPlanned,
}: {
  snapshotId: number
  channel: string
  defaultName: string
  onPlanned: (id: number) => void
}) {
  const groups = useAudienceGroups()
  const settings = useSettings()
  const plan = usePlanSend(snapshotId)
  const providers = (settings.data?.delivery_providers ?? []).filter((p) => p.channels.includes(channel))
  const [name, setName] = useState(defaultName)
  const [groupId, setGroupId] = useState('')
  const [provider, setProvider] = useState('mock')
  const [from, setFrom] = useState<string | null>(null)
  const [timing, setTiming] = useState('now')
  const [at, setAt] = useState('')
  const [skip, setSkip] = useState(false)
  const chosen = providers.find((p) => p.name === provider)
  const sender = from ?? chosen?.default_from_address ?? ''

  return (
    <section aria-labelledby="step-plan">
      <h2 id="step-plan">2. Plan the send</h2>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          plan.mutate(
            {
              name: name.trim(),
              audience_group_id: Number(groupId),
              provider,
              from_address: chosen?.needs_from_address ? sender.trim() || null : null,
              scheduled_at: timing === 'at' && at ? new Date(at).toISOString() : null,
              skip_without_resolution: skip,
            },
            { onSuccess: (send) => onPlanned(send.id) },
          )
        }}
      >
        <TextField value={name} onChange={setName} isRequired>
          <Label>Name of the send</Label>
          <Input />
        </TextField>
        <Choice
          label="Audience"
          options={[
            { id: '', name: 'Choose an audience group' },
            ...(groups.data?.items ?? []).map((g) => ({ id: String(g.id), name: g.name })),
          ]}
          selected={groupId}
          onChange={setGroupId}
        />
        {groupId && <Reachable groupId={Number(groupId)} channel={channel} />}
        <Choice
          label="Provider"
          options={providers.map((p) => ({ id: p.name, name: p.label }))}
          selected={provider}
          onChange={setProvider}
        />
        {chosen?.needs_from_address && (
          <TextField value={sender} onChange={setFrom}>
            <Label>Sender address</Label>
            <Input />
          </TextField>
        )}
        <Choice
          label="When"
          options={[
            { id: 'now', name: 'When I send it' },
            { id: 'at', name: 'At a time' },
          ]}
          selected={timing}
          onChange={setTiming}
        />
        {timing === 'at' && (
          <TextField value={at} onChange={setAt} type="datetime-local">
            <Label>Send at</Label>
            <Input />
          </TextField>
        )}
        <Checkbox isSelected={skip} onChange={setSkip}>
          Don't send to someone who would get no content record
        </Checkbox>
        <Button type="submit" isDisabled={plan.isPending || !groupId || !name.trim() || (timing === 'at' && !at)}>
          {plan.isPending ? 'Planning…' : 'Plan the send'}
        </Button>
        {plan.error != null && <p role="alert">Not planned: {refused(plan.error, 'plan a send')}</p>}
      </form>
    </section>
  )
}

/** How many of a group the send could reach on this channel, as of now. */
function Reachable({ groupId, channel }: { groupId: number; channel: string }) {
  const preview = useAudiencePreview(groupId, channel)
  if (!preview.data) return null
  const { reachable_count: reachable, resolved_count: resolved } = preview.data
  return (
    <p className="muted" role="status">
      {reachable} of {resolved} in this group can be reached on {channel} now.
    </p>
  )
}

/** Step 3: the frozen email to one address, as a chosen recipient would get it. */
function TestStep({ sendId }: { sendId: number }) {
  const test = useTestPlannedSend(sendId)
  const [to, setTo] = useState('')
  const [as, setAs] = useState<PickedRecipient | null>(null)
  return (
    <section aria-labelledby="step-test">
      <h2 id="step-test">3. Send a test</h2>
      <p className="muted">
        The frozen email with its own subject marked [Test]. Not a delivery: no unsubscribe link, nothing counted.
      </p>
      <TextField value={to} onChange={setTo} type="email">
        <Label>Test address</Label>
        <Input />
      </TextField>
      {as ? (
        <p>
          As {as.label} would get it.{' '}
          <Button onPress={() => setAs(null)}>Show it as nobody in particular</Button>
        </p>
      ) : (
        <RecipientPicker label="Show it as (optional)" onChoose={setAs} />
      )}
      <Button
        onPress={() => test.mutate({ to: to.trim(), recipient_id: as?.id ?? null })}
        isDisabled={test.isPending || !to.trim()}
      >
        {test.isPending ? 'Sending the test…' : 'Send a test'}
      </Button>
      {test.error != null && <p role="alert">No test sent: {refused(test.error, 'send a test')}</p>}
      {test.data &&
        (test.data.success ? (
          <p role="status">
            Test sent to {test.data.to} through {test.data.provider}.
          </p>
        ) : (
          <p role="alert">No test sent: {test.data.message}</p>
        ))}
    </section>
  )
}

/** Step 4: the recipients as of now, and a button that says what it does. */
function SendStep({ sendId, campaignId }: { sendId: number; campaignId: number }) {
  const now = useRecipientsNow(sendId)
  const fire = useFireSend(sendId, campaignId)
  return (
    <section aria-labelledby="step-send">
      <h2 id="step-send">4. Send</h2>
      <ScreenState query={now}>
        {now.data &&
          (() => {
            const n = now.data
            const links = (
              <p>
                <Link to={`/deliveries/${sendId}`}>The delivery</Link> ·{' '}
                <Link to={`/campaigns/${campaignId}`}>The campaign's results</Link>
              </p>
            )
            if (fire.data)
              return (
                <>
                  <p role="status">Sent: {fire.data.status.replace('_', ' ')}.</p>
                  {links}
                </>
              )
            if (n.status !== 'draft' && n.status !== 'scheduled')
              return (
                <>
                  <p role="status">This send is {n.status.replace('_', ' ')}.</p>
                  {links}
                </>
              )
            const over = n.recipients > n.cap
            const label = n.reaches_real_inboxes
              ? `Send real email to ${n.recipients} ${n.recipients === 1 ? 'person' : 'people'}`
              : `Send to ${n.recipients}`
            return (
              <>
                <p>
                  Goes to <strong>{n.recipients}</strong> {n.recipients === 1 ? 'recipient' : 'recipients'} as of now,
                  through {n.provider_label}
                  {n.from_address ? `, from ${n.from_address}` : ''}.
                </p>
                {n.status === 'scheduled' && n.scheduled_at && (
                  <p className="muted">Scheduled for {formatDate(n.scheduled_at)}; it goes out then, or now if you send it.</p>
                )}
                {over && (
                  <p role="alert">
                    That is above the limit of {n.cap} recipients per send, so it will be refused.
                  </p>
                )}
                {n.reaches_real_inboxes && (
                  <p role="note">Real email: it reaches real inboxes and cannot be called back.</p>
                )}
                <Button onPress={() => fire.mutate()} isDisabled={fire.isPending || n.recipients === 0}>
                  {fire.isPending ? 'Sending…' : label}
                </Button>
                {fire.error != null && <p role="alert">Not sent: {refused(fire.error, 'send')}</p>}
                {links}
              </>
            )
          })()}
      </ScreenState>
    </section>
  )
}
