import { useState } from 'react'
import { Button, Dialog, Heading, Input, Label, Modal, ModalOverlay, TextField } from 'react-aria-components'
import { Link, useParams } from 'react-router'

import {
  useAddIntegrationGrant, useAdminBrands, useDeactivateIntegration, useIntegrations, useIssueKey,
  usePermissionCatalogue, useRemoveIntegrationGrant, useRevokeKey, useSetUnattended, type Integration,
} from '../api/resources'
import Choice from '../components/Choice'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'
import { refused } from './People'
import { INTEGRATIONS } from './Integrations'

/** One integration: its keys, what it may do on which brand, and how much it may send unattended. */
export default function IntegrationDetail() {
  const { id } = useParams()
  const integrations = useIntegrations()
  const integration = integrations.data?.find((i) => i.id === Number(id))
  return (
    <ScreenState query={integrations}>
      {integrations.data && (integration ? <Page integration={integration} /> : <p role="alert">This integration does not exist.</p>)}
    </ScreenState>
  )
}

function Page({ integration }: { integration: Integration }) {
  const deactivate = useDeactivateIntegration(integration.id)
  return (
    <>
      <p><Link to={INTEGRATIONS}>← Integrations</Link></p>
      <h1>{integration.name}</h1>
      {integration.description && <p>{integration.description}</p>}
      {!integration.is_active && <p role="status">Deactivated: none of its keys work any more.</p>}
      <Keys integration={integration} />
      <Grants integration={integration} />
      <Unattended integration={integration} />
      {integration.is_active && (
        <p>
          <Button onPress={() => deactivate.mutate(undefined)}>Deactivate {integration.name}</Button>
          {deactivate.error != null && <span role="alert"> Not deactivated: {refused(deactivate.error)}</span>}
        </p>
      )}
    </>
  )
}

function Keys({ integration }: { integration: Integration }) {
  const issue = useIssueKey(integration.id)
  const revoke = useRevokeKey(integration.id)
  const [label, setLabel] = useState('')
  const [days, setDays] = useState(integration.suggested_expiry_days ? String(integration.suggested_expiry_days) : '')
  // The secret lives here and only here: never in the query cache or the URL,
  // and gone when the dialog closes (ADR-166 addendum 2026-10-16).
  const [secret, setSecret] = useState<string | null>(null)
  const live = integration.credentials.filter((c) => !c.revoked_at)
  return (
    <section aria-labelledby="integration-keys">
      <h2 id="integration-keys">Keys</h2>
      {live.length === 0 ? (
        <p className="muted">No live key: it cannot call the platform.</p>
      ) : (
        <ul aria-label="Live keys">
          {live.map((c) => (
            <li key={c.id}>
              <code>{c.key_id}</code> {c.label && <strong>{c.label}</strong>} · issued {formatDate(c.created_at)} · last used{' '}
              {c.last_used_at ? formatDate(c.last_used_at) : 'never'} ·{' '}
              {c.expires_at ? `expires ${formatDate(c.expires_at)}${c.expiring_soon ? ' (soon)' : ''}` : 'no expiry'}{' '}
              <Button onPress={() => revoke.mutate(c.id)}>Revoke</Button>
            </li>
          ))}
        </ul>
      )}
      {integration.is_active && (
        <p className="inline-form">
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
                { onSuccess: (issued) => { setSecret(issued.secret_key); setLabel('') } })
            }
          >
            Issue a key
          </Button>
        </p>
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
    </section>
  )
}

function Grants({ integration }: { integration: Integration }) {
  const catalogue = usePermissionCatalogue()
  const brands = useAdminBrands()
  const add = useAddIntegrationGrant(integration.id)
  const remove = useRemoveIntegrationGrant(integration.id)
  const [permission, setPermission] = useState('')
  const [brand, setBrand] = useState('')
  const brandName = new Map((brands.data ?? []).map((b) => [b.id, b.name]))
  const defaultBrand = brands.data?.[0]?.id
  return (
    <section aria-labelledby="integration-grants">
      <h2 id="integration-grants">What it may do</h2>
      {integration.grants.length === 0 ? (
        <p className="muted">Nothing yet: its keys can authenticate but may do nothing.</p>
      ) : (
        <ul aria-label="Grants">
          {integration.grants.map((g) => (
            <li key={`${g.permission}-${g.brand_id}`}>
              <code>{g.permission}</code> on {brandName.get(g.brand_id) ?? `brand ${g.brand_id}`}{' '}
              <Button onPress={() => remove.mutate(g)}>Remove</Button>
            </li>
          ))}
        </ul>
      )}
      <p className="inline-form">
        <Choice label="Allow" options={(catalogue.data ?? []).map((p) => ({ id: p.key, name: p.key }))} selected={permission}
          onChange={setPermission} placeholder="Choose a permission" />
        <Choice label="On brand" options={(brands.data ?? []).map((b) => ({ id: String(b.id), name: b.name }))}
          selected={brand} onChange={setBrand} placeholder="Choose a brand" />
        <Button isDisabled={!permission || !(brand || defaultBrand) || add.isPending}
          onPress={() => add.mutate({ permission, brand_id: Number(brand || defaultBrand) }, { onSuccess: () => setPermission('') })}>
          Allow
        </Button>
      </p>
      {(add.error ?? remove.error) != null && <p role="alert">Not changed: {refused(add.error ?? remove.error)}</p>}
    </section>
  )
}

function Unattended({ integration }: { integration: Integration }) {
  const set = useSetUnattended(integration.id)
  const [ceiling, setCeiling] = useState(String(integration.unattended_ceiling))
  return (
    <section aria-labelledby="integration-unattended">
      <h2 id="integration-unattended">Sending without a person</h2>
      <p className="muted">
        A send it fires to at most this many recipients goes out at once; a bigger one waits for a person in
        Approvals. 0: every send waits.
      </p>
      <p className="inline-form">
        <TextField value={ceiling} onChange={setCeiling} type="number">
          <Label>Recipients per send, unattended</Label>
          <Input />
        </TextField>
        <Button isDisabled={ceiling === String(integration.unattended_ceiling) || ceiling === '' || set.isPending}
          onPress={() => set.mutate(Number(ceiling))}>Save</Button>
      </p>
      {set.error != null && <p role="alert">Not saved: {refused(set.error)}</p>}
    </section>
  )
}
