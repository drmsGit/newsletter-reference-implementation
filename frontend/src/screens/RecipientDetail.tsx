import { Link, useParams, useSearchParams } from 'react-router'

import { useRecipientActivity, useRecipientGroups, useSettings } from '../api/resources'
import Choice from '../components/Choice'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'

type Activity = NonNullable<ReturnType<typeof useRecipientActivity>['data']>
type Group = NonNullable<ReturnType<typeof useRecipientGroups>['data']>['items'][number]

/**
 * One person: why did they get this (task-292; Manager Workflow interview
 * Q4.5). Their consent, which audiences they are in and why, what was sent
 * and the decisions behind it, from the working brand. **Read-only, with a
 * planned end of life**: the CRM owns the person (ADR-120) and a projection
 * that can be edited is a second source of truth (ADR-126); this page exists
 * because the reasoning lives here, until a CRM can receive it.
 */
export default function RecipientDetail() {
  const { id } = useParams()
  const activity = useRecipientActivity(Number(id))
  return (
    // Column 3 of the recipients (task-372, render 38).
    <div className="detail">
      <div className="detail-scroll">
        <ScreenState query={activity}>{activity.data && <Person activity={activity.data} />}</ScreenState>
      </div>
    </div>
  )
}

function Person({ activity: a }: { activity: Activity }) {
  return (
    <>
      <div className="detail-head">
        <h2>{a.external_id}</h2>
        <p className="muted">
          Read-only: the CRM owns this person. This page shows why they were chosen and what they were sent.
        </p>
      </div>
      <Section title="Consent" note="This brand, per channel and purpose.">
        <Table label="Consent" columns={['Channel', 'Purpose', 'Status', 'Source', 'Recorded']}>
          {a.consent_grid.map((cell) => {
            const c = cell as { channel: string; purpose: string; status: string | null; source?: string | null;
              recorded_at?: string | null }
            return (
              <tr key={`${c.channel}-${c.purpose}`}>
                <th scope="row">{c.channel}</th>
                <td>{c.purpose}</td>
                <td>{c.status ?? 'Not asked'}</td>
                <td className="muted">{c.source ?? ''}</td>
                <td className="muted">{c.recorded_at ? formatDate(c.recorded_at) : ''}</td>
              </tr>
            )
          })}
        </Table>
      </Section>
      <Groups recipientId={a.recipient_id} />
      <Section title="Deliveries" note="What this brand sent them, newest first.">
        {a.deliveries.length === 0 ? (
          <p className="muted">Nothing sent yet.</p>
        ) : (
          <Table label="Deliveries" columns={['Send', 'Channel', 'Status', 'Excluded because', 'Sent']}>
            {a.deliveries.map((d) => (
              <tr key={d.id}>
                <th scope="row"><Link to={`/deliveries/${d.send_instance_id}`}>{d.send_instance_name}</Link></th>
                <td>{d.channel}</td>
                <td>{d.status}</td>
                <td className="muted">{d.exclusion_reason ?? ''}</td>
                <td className="muted">{formatDate(d.sent_at ?? d.created_at)}</td>
              </tr>
            ))}
          </Table>
        )}
      </Section>
      <Section title="Decisions" note="What decision slots picked for them, newest first.">
        {a.decisions.length === 0 ? (
          <p className="muted">No decision has picked for them yet.</p>
        ) : (
          <Table label="Decisions" columns={['Content', 'Score', 'Reason', 'Picked']}>
            {a.decisions.map((d) => (
              <tr key={d.id}>
                <th scope="row">
                  <Link to={`/content/${d.content_record_id}`}>{d.content_title}</Link>
                  {d.content_version != null && <span className="muted"> · version {d.content_version}</span>}
                </th>
                <td className="num">{d.score ?? ''}</td>
                <td>{d.reason ?? ''}</td>
                <td className="muted">{formatDate(d.created_at)}</td>
              </tr>
            ))}
          </Table>
        )}
      </Section>
      <Section title="Interests" note="Their interest profile, one per person across brands.">
        {a.preferences.length === 0 ? (
          <p className="muted">No interests recorded.</p>
        ) : (
          <Table label="Interests" columns={['Category', 'Score']}>
            {a.preferences.map((p) => (
              <tr key={p.category_id}>
                <th scope="row">{p.category_name}</th>
                <td className="num">{p.score}</td>
              </tr>
            ))}
          </Table>
        )}
      </Section>
      <Section title="Consent history" note="Every brand, each event labelled with its brand.">
        <Table label="Consent history" columns={['Brand', 'Channel', 'Purpose', 'Status', 'Source', 'Recorded']}>
          {a.consent_history.map((e, i) => (
            <tr key={i}>
              <th scope="row">{e.brand_name ?? `Brand ${e.brand_id}`}</th>
              <td>{e.channel}</td>
              <td>{e.purpose}</td>
              <td>{e.status}</td>
              <td className="muted">{e.source ?? ''}</td>
              <td className="muted">{formatDate(e.created_at)}</td>
            </tr>
          ))}
        </Table>
      </Section>
    </>
  )
}

/** A part of the page: its title and what it covers on the ground, its rows in a card. */
/**
 * A table as render 38 draws it, without a header row: its column headers are
 * there for a screen reader only, and the first cell of each row names it
 * (task-392 item 17).
 */
function Table({ label, columns, children }: { label: string; columns: string[]; children: React.ReactNode }) {
  return (
    <table aria-label={label}>
      <thead className="sr-only">
        <tr>
          {columns.map((c) => (
            <th key={c} scope="col">{c}</th>
          ))}
        </tr>
      </thead>
      <tbody>{children}</tbody>
    </table>
  )
}

function Section({ title, note, children }: { title: string; note: string; children: React.ReactNode }) {
  const id = `section-${title.toLowerCase().replace(/\W+/g, '-')}`
  return (
    <section aria-labelledby={id} className="detail-section person-section">
      <div>
        <h3 id={id} className="group-title">
          {title}
        </h3>
        <p className="muted section-note">{note}</p>
      </div>
      <div className="group card-rows">{children}</div>
    </section>
  )
}

const REASON: Record<string, (label: string | null | undefined) => string> = {
  rule: (label) => `Matched rule “${label}”`,
  pinned: () => 'Added by hand',
  excluded: (label) => `Removed by exclusion “${label}”`,
  not_agreed: (label) => `Not agreed to ${label}`,
}

/**
 * Which audiences they are in on one channel, and why (task-214). Worked out
 * for this person now, never stored; the channel is chosen as on the audience
 * screen — there is no channel-less answer (ADR-176 point 5).
 */
function Groups({ recipientId }: { recipientId: number }) {
  const [params, setParams] = useSearchParams()
  const settings = useSettings()
  const channels = (settings.data?.channels ?? []).filter((c) => c.available).map((c) => c.name)
  const channel = params.get('channel') ?? channels[0] ?? 'email'
  const groups = useRecipientGroups(recipientId, channel)
  return (
    <Section title="Audience groups" note="The groups that touch them, and why they are in or out.">
      {channels.length > 1 && (
        <div>
          <Choice
            label="Channel"
            options={channels.map((c) => ({ id: c, name: c }))}
            selected={channel}
            onChange={(next) => {
              const updated = new URLSearchParams(params)
              updated.set('channel', next)
              setParams(updated)
            }}
          />
        </div>
      )}
      <ScreenState query={groups}>
        {groups.data && groups.data.items.length === 0 ? (
          <p className="muted">No audience group touches them on {channel}.</p>
        ) : (
          <Table label="Audience groups" columns={['Group', 'In or out', 'Why']}>
            {groups.data?.items.map((g: Group) => (
              <tr key={g.group_id}>
                <th scope="row"><Link to={`/audiences/${g.group_id}`}>{g.group_name}</Link></th>
                <td>{g.member ? 'In' : 'Out'}</td>
                <td>{g.reasons.map((r) => (REASON[r.kind] ?? (() => r.kind))(r.label)).join(' · ')}</td>
              </tr>
            ))}
          </Table>
        )}
      </ScreenState>
      <p className="muted">As of now: a send works this out again when it goes out.</p>
    </Section>
  )
}
