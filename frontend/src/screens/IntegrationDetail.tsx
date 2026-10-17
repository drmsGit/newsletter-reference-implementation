import { useState } from 'react'
import { Button, Checkbox, Dialog, Heading, Input, Label, Modal, ModalOverlay, TextField } from 'react-aria-components'
import { useParams } from 'react-router'

import {
  useAddIntegrationGrant, useDeactivateIntegration, useGrantablePermissions, useIntegrations, useIssueKey,
  useRemoveIntegrationGrant, useRevokeKey, useSetUnattended, type Integration,
} from '../api/resources'
import { useSession } from '../api/session'
import DetailSection from '../components/DetailSection'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'
import { refused } from './People'

/** One integration: its keys, what it may do on which brand, and how much it may send unattended. */
export default function IntegrationDetail() {
  const { id } = useParams()
  const integrations = useIntegrations()
  const integration = integrations.data?.find((i) => i.id === Number(id))
  return (
    // Column 3 of the integrations (task-372, render 36). Keyed by the
    // integration: a label or ceiling typed for one is not carried to the next.
    <div className="detail">
      <div className="detail-scroll">
        <ScreenState query={integrations}>
          {integrations.data &&
            (integration ? (
              <Page key={integration.id} integration={integration} />
            ) : (
              <p role="alert" className="quiet">This integration does not exist.</p>
            ))}
        </ScreenState>
      </div>
    </div>
  )
}

function Page({ integration }: { integration: Integration }) {
  const deactivate = useDeactivateIntegration(integration.id)
  return (
    <>
      <div className="detail-head">
        <h2>{integration.name}</h2>
        {integration.description && <p className="muted">{integration.description}</p>}
      </div>
      {!integration.is_active && (
        <p role="status" className="group group-body">
          Deactivated: none of its keys work any more.
        </p>
      )}
      <Keys integration={integration} />
      <Grants integration={integration} />
      <Unattended integration={integration} />
      {integration.is_active && (
        <p className="group group-body">
          <Button className="btn-destructive" onPress={() => deactivate.mutate(undefined)}>
            Deactivate {integration.name}
          </Button>
          {deactivate.error != null && <span role="alert"> Not deactivated: {refused(deactivate.error)}</span>}
        </p>
      )}
    </>
  )
}

function Keys({ integration }: { integration: Integration }) {
  // The secret lives here and only here: never in a client cache or the URL,
  // and gone when the dialog closes (ADR-166 addendum 2026-10-16).
  const [secret, setSecret] = useState<string | null>(null)
  const issue = useIssueKey(integration.id, setSecret)
  const revoke = useRevokeKey(integration.id)
  const [label, setLabel] = useState('')
  const [days, setDays] = useState(integration.suggested_expiry_days ? String(integration.suggested_expiry_days) : '')
  const live = integration.credentials.filter((c) => !c.revoked_at)
  return (
    <DetailSection id="integration-keys" title="Keys">
      {live.length === 0 ? (
        <p className="muted">No live key: it cannot call the platform.</p>
      ) : (
        <ul aria-label="Live keys" className="link-list">
          {live.map((c) => (
            <li key={c.id}>
              <span>
              <code>{c.key_id}</code> {c.label && <strong>{c.label}</strong>} · issued {formatDate(c.created_at)} · last used{' '}
              {c.last_used_at ? formatDate(c.last_used_at) : 'never'} ·{' '}
              {c.expires_at ? `expires ${formatDate(c.expires_at)}${c.expiring_soon ? ' (soon)' : ''}` : 'no expiry'}
              </span>
              <Button className="btn-plain btn-sm" onPress={() => revoke.mutate(c.id)}>
                Revoke
              </Button>
            </li>
          ))}
        </ul>
      )}
      {integration.is_active && (
        <div className="inline-form">
          <TextField value={label} onChange={setLabel}>
            <Label>New key's label</Label>
            <Input />
          </TextField>
          <TextField value={days} onChange={setDays} type="number">
            <Label>Expires after (days, empty for never)</Label>
            <Input />
          </TextField>
          <Button
            isDisabled={issue.isPending}
            onPress={() =>
              issue.mutate({ label: label.trim() || undefined, expires_in_days: days.trim() ? Number(days) : null },
                { onSuccess: () => setLabel('') })
            }
          >
            Issue a key
          </Button>
        </div>
      )}
      {(issue.error ?? revoke.error) != null && <p role="alert">Not done: {refused(issue.error ?? revoke.error)}</p>}
      <ModalOverlay isOpen={secret != null} onOpenChange={(open) => !open && setSecret(null)} className="preview-overlay">
        <Modal className="create-modal">
          <Dialog aria-label="The new key">
            {({ close }) => (
              <>
                <Heading slot="title">The new key</Heading>
                <p><strong>This is the only time it is shown.</strong> Store it in the calling system now; it cannot be seen again.</p>
                <p><code className="secret">{secret}</code></p>
                <p>
                  <Button onPress={() => void navigator.clipboard?.writeText(secret ?? '')}>Copy</Button>{' '}
                  <Button onPress={close}>I have stored it</Button>
                </p>
              </>
            )}
          </Dialog>
        </Modal>
      </ModalOverlay>
    </DetailSection>
  )
}

/**
 * What the integration may do: every permission as a row, a checkbox per
 * brand (one column when there is one brand). Ticking or unticking saves that
 * one grant at once; the server still refuses a grant the person does not
 * hold themselves (ADR-166).
 */
function Grants({ integration }: { integration: Integration }) {
  // Neither from the user-administration routes, which need users.manage: the
  // catalogue from the integrations API, the brands from the person's own
  // session — they can only allow what they hold, on brands they hold it on
  // (task-386; ADR-166).
  const catalogue = useGrantablePermissions()
  const session = useSession()
  const add = useAddIntegrationGrant(integration.id)
  const remove = useRemoveIntegrationGrant(integration.id)
  const granted = new Set(integration.grants.map((g) => `${g.permission}@${g.brand_id}`))
  const columns = session.data?.brands ?? []
  const several = columns.length > 1
  const busy = add.isPending || remove.isPending
  const toggle = (permission: string, brand_id: number, on: boolean) =>
    (on ? add : remove).mutate({ permission, brand_id })
  return (
    <DetailSection id="integration-grants" title="What it may do">
      <p className="muted">
        Tick what its keys may do{several ? ', per brand' : ''}. Each tick is saved at once. You can only allow what you
        may do yourself.
      </p>
      <ScreenState query={catalogue}>
        <table className="grant-grid">
          <thead>
            <tr>
              <th scope="col">Permission</th>
              {several ? columns.map((b) => <th key={b.id} scope="col">{b.name}</th>) : <th scope="col">Allowed</th>}
            </tr>
          </thead>
          <tbody>
            {(catalogue.data ?? []).map((p) => (
              <tr key={p.key}>
                <th scope="row">
                  <code>{p.key}</code>
                  <br />
                  <span className="muted">{p.description}</span>
                </th>
                {columns.map((b) => (
                  <td key={b.id}>
                    <Checkbox
                      aria-label={several ? `${p.key} on ${b.name}` : p.key}
                      isSelected={granted.has(`${p.key}@${b.id}`)}
                      isDisabled={busy || !integration.is_active}
                      onChange={(on) => toggle(p.key, b.id, on)}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </ScreenState>
      {(add.error ?? remove.error) != null && <p role="alert">Not changed: {refused(add.error ?? remove.error)}</p>}
    </DetailSection>
  )
}

function Unattended({ integration }: { integration: Integration }) {
  const set = useSetUnattended(integration.id)
  const [ceiling, setCeiling] = useState(String(integration.unattended_ceiling))
  return (
    <DetailSection id="integration-unattended" title="Sending without a person">
      <p className="muted">
        A send it fires to at most this many recipients goes out at once; a bigger one waits for a person in
        Approvals. 0: every send waits.
      </p>
      <div className="inline-form">
        <TextField value={ceiling} onChange={setCeiling} type="number">
          <Label>Recipients per send, unattended</Label>
          <Input />
        </TextField>
        <Button isDisabled={ceiling === String(integration.unattended_ceiling) || ceiling === '' || set.isPending}
          onPress={() => set.mutate(Number(ceiling))}>Save</Button>
      </div>
      {set.error != null && <p role="alert">Not saved: {refused(set.error)}</p>}
    </DetailSection>
  )
}
