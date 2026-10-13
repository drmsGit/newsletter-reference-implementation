import { useState, type FormEvent } from 'react'
import { Button, Checkbox, Input, Label, TextField } from 'react-aria-components'
import { Link, useParams, useSearchParams } from 'react-router'

import {
  useAudienceGroups,
  useAudiencePreview,
  useComposition,
  useFireSend,
  useFramePreview,
  useOpenSends,
  usePlanVariantSend,
  useRecipientsNow,
  useSettings,
  useTestVariant,
} from '../api/resources'
import { HttpError } from '../api/session'
import Choice from '../components/Choice'
import RecipientPicker, { type PickedRecipient } from '../components/RecipientPicker'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'

/**
 * Sending one variant (task-67; ADR-183 addenda 2026-10-12 and 2026-10-13).
 *
 * 1. **What goes out**: the email as planning would freeze it now. Nothing is
 *    stored by looking.
 * 2. **Test** (optional, any time): that email to one address, as a chosen
 *    recipient, through a chosen provider. Not a delivery; nothing stored.
 * 3. **Plan**: freezing happens here, together with the plan, and only here,
 *    so no frozen version is left behind that nobody sends.
 * 4. **Send**: the recipients as of now, and a button that says what it does.
 *
 * Sends of this variant that are planned or scheduled are listed to continue,
 * and the one being worked on is kept in the address (`?send=`). A person who
 * may fire a send is its approval (ADR-174). Every rule -- the cap, the legal
 * details, who may fire -- is the server's.
 */
export default function SendVariant() {
  const params = useParams()
  const campaignId = Number(params.id)
  const variantId = Number(params.variantId)
  const composition = useComposition(campaignId)
  const [search, setSearch] = useSearchParams()
  const sendId = search.get('send') ? Number(search.get('send')) : null

  function continueWith(id: number | null) {
    const next = new URLSearchParams(search)
    if (id == null) next.delete('send')
    else next.set('send', String(id))
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
                {sendId == null && <OpenSends variantId={variantId} onContinue={continueWith} />}
                <WhatGoesOut variantId={variantId} />
                {variant.channel === 'email' && <TestStep variantId={variantId} channel={variant.channel} />}
                {sendId == null ? (
                  <PlanStep
                    variantId={variantId}
                    channel={variant.channel}
                    defaultName={composition.data.campaign.name}
                    onPlanned={continueWith}
                  />
                ) : (
                  <SendStep sendId={sendId} campaignId={campaignId} onAnother={() => continueWith(null)} />
                )}
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

/** Sends of this variant that were planned and not sent yet. */
function OpenSends({ variantId, onContinue }: { variantId: number; onContinue: (id: number) => void }) {
  const open = useOpenSends(variantId)
  if (!open.data || open.data.length === 0) return null
  return (
    <section aria-labelledby="open-sends">
      <h2 id="open-sends">Planned and not sent yet</h2>
      <ul>
        {open.data.map((send) => (
          <li key={send.id}>
            {send.name} — {send.status === 'scheduled' && send.scheduled_at
              ? `scheduled for ${formatDate(send.scheduled_at)}`
              : `planned ${formatDate(send.created_at)}`}{' '}
            <Button onPress={() => onContinue(send.id)}>Continue</Button>
          </li>
        ))}
      </ul>
    </section>
  )
}

/** Step 1: the email as planning would freeze it now; looking stores nothing. */
function WhatGoesOut({ variantId }: { variantId: number }) {
  const preview = useFramePreview(variantId)
  return (
    <section aria-labelledby="step-what">
      <h2 id="step-what">1. What goes out</h2>
      <p className="muted">As it would be frozen now. It is frozen when you plan the send.</p>
      {preview.isError && <p role="alert">Cannot be sent yet: {refused(preview.error, 'see it')}</p>}
      {preview.data &&
        (preview.data.html ? (
          <>
            <p>
              <strong>Subject:</strong> {preview.data.subject || '—'}
            </p>
            <iframe
              title="What goes out"
              srcDoc={preview.data.html}
              sandbox=""
              style={{ width: '100%', height: 480, border: '1px solid currentColor' }}
            />
          </>
        ) : (
          <dl className="facts">
            {Object.entries(preview.data.fields ?? {}).map(([key, value]) => (
              <div key={key} style={{ display: 'contents' }}>
                <dt>{key}</dt>
                <dd>{String(value) || '—'}</dd>
              </div>
            ))}
          </dl>
        ))}
    </section>
  )
}

/** The providers that can carry this channel, with the sender field where one is used. */
function ProviderFields({
  channel,
  provider,
  setProvider,
  sender,
  setSender,
}: {
  channel: string
  provider: string
  setProvider: (name: string) => void
  sender: string | null
  setSender: (value: string) => void
}) {
  const settings = useSettings()
  const providers = (settings.data?.delivery_providers ?? []).filter((p) => p.channels.includes(channel))
  const chosen = providers.find((p) => p.name === provider)
  return (
    <>
      <Choice
        label="Provider"
        options={providers.map((p) => ({ id: p.name, name: p.label }))}
        selected={provider}
        onChange={setProvider}
      />
      {chosen?.needs_from_address && (
        <TextField value={sender ?? chosen.default_from_address ?? ''} onChange={setSender}>
          <Label>Sender address</Label>
          <Input />
        </TextField>
      )}
    </>
  )
}

/** The sender to send with: only for a provider that uses one. */
function useSender(channel: string, provider: string, typed: string | null) {
  const settings = useSettings()
  const chosen = (settings.data?.delivery_providers ?? []).find(
    (p) => p.name === provider && p.channels.includes(channel),
  )
  if (!chosen?.needs_from_address) return null
  return (typed ?? chosen.default_from_address ?? '').trim() || null
}

/** Step 2: a test, any time: the email to one address; nothing is stored. */
function TestStep({ variantId, channel }: { variantId: number; channel: string }) {
  const test = useTestVariant(variantId)
  const [to, setTo] = useState('')
  const [as, setAs] = useState<PickedRecipient | null>(null)
  const [provider, setProvider] = useState('mock')
  const [sender, setSender] = useState<string | null>(null)
  const from = useSender(channel, provider, sender)
  return (
    <section aria-labelledby="step-test">
      <h2 id="step-test">2. Send a test (optional)</h2>
      <p className="muted">
        The email above with its subject marked [Test]. Not a delivery: no unsubscribe link, nothing counted or stored.
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
      <ProviderFields channel={channel} provider={provider} setProvider={setProvider} sender={sender} setSender={setSender} />
      <Button
        onPress={() => test.mutate({ to: to.trim(), provider, from_address: from, recipient_id: as?.id ?? null })}
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

/** A complete local date and time for a datetime-local field: tomorrow, 09:00. */
function tomorrowAtNine() {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T09:00`
}

/** Step 3: to whom, through which provider, and when. Freezing happens here. */
function PlanStep({
  variantId,
  channel,
  defaultName,
  onPlanned,
}: {
  variantId: number
  channel: string
  defaultName: string
  onPlanned: (id: number) => void
}) {
  const groups = useAudienceGroups()
  const plan = usePlanVariantSend(variantId)
  const [name, setName] = useState(defaultName)
  const [groupId, setGroupId] = useState('')
  const [provider, setProvider] = useState('mock')
  const [sender, setSender] = useState<string | null>(null)
  const [timing, setTiming] = useState('now')
  const [at, setAt] = useState('')
  const [skip, setSkip] = useState(false)
  const [missing, setMissing] = useState<string[]>([])
  const from = useSender(channel, provider, sender)

  function submit(event: FormEvent) {
    event.preventDefault()
    const lacking = [
      !name.trim() && 'a name for the send',
      !groupId && 'an audience',
      timing === 'at' && Number.isNaN(new Date(at).getTime()) && 'a date and a time to send at',
    ].filter((item): item is string => Boolean(item))
    setMissing(lacking)
    if (lacking.length > 0) return
    plan.mutate(
      {
        name: name.trim(),
        audience_group_id: Number(groupId),
        provider,
        from_address: from,
        scheduled_at: timing === 'at' ? new Date(at).toISOString() : null,
        skip_without_resolution: skip,
      },
      { onSuccess: (send) => onPlanned(send.id) },
    )
  }

  return (
    <section aria-labelledby="step-plan">
      <h2 id="step-plan">3. Plan the send</h2>
      <p className="muted">Planning freezes the email as it is now; later edits need a new send.</p>
      <form onSubmit={submit}>
        <TextField value={name} onChange={setName}>
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
        <ProviderFields channel={channel} provider={provider} setProvider={setProvider} sender={sender} setSender={setSender} />
        <Choice
          label="When"
          options={[
            { id: 'now', name: 'When I send it' },
            { id: 'at', name: 'At a time' },
          ]}
          selected={timing}
          onChange={(value) => {
            setTiming(value)
            if (value === 'at' && !at) setAt(tomorrowAtNine())
          }}
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
        <Button type="submit" isDisabled={plan.isPending}>
          {plan.isPending ? 'Planning…' : 'Plan the send'}
        </Button>
        {missing.length > 0 && <p role="alert">Still needed: {missing.join(', ')}.</p>}
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

/** Step 4: the recipients as of now, and a button that says what it does. */
function SendStep({ sendId, campaignId, onAnother }: { sendId: number; campaignId: number; onAnother: () => void }) {
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
                <Link to={`/campaigns/${campaignId}`}>The campaign's results</Link> ·{' '}
                <Button onPress={onAnother}>Plan another send</Button>
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
