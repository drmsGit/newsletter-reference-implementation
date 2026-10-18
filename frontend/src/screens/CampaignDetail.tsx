import { useState } from 'react'
import { Button } from 'react-aria-components'
import { Link, useNavigate, useParams } from 'react-router'

import {
  useComposition,
  useCreateVariant,
  useDuplicateVariant,
  useModuleManifests,
  type ComposedVariant,
} from '../api/resources'
import { HttpError } from '../api/session'
import CampaignResults from '../components/CampaignResults'
import DataTable from '../components/DataTable'
import Fact from '../components/Fact'
import NameAndChannel from '../components/NameAndChannel'
import ScreenState from '../components/ScreenState'
import { SuggestForVariant } from './AudienceCreate'
import { formatDate } from './Campaigns'
import { PreviewSheet } from './Preview'

/**
 * One campaign, variant by variant (inventory B11).
 *
 * Everything comes from one read, `GET /campaigns/{id}/composition`, which
 * already carries what the Jinja page used to compute for itself: whether a
 * module may be overridden, the channel's module limit, which module is the
 * envelope. **This screen derives none of it.** It shows the server's answers,
 * so there is one place those rules live.
 *
 * Its writes: Duplicate, the primary way a variant comes into being (Variant
 * Editor interview Q5.1), a blank variant, and a variant's Suggest an
 * audience, which makes a group from its content in its language (ADR-188
 * addendum 2026-10-18). Modules, overrides
 * and slots are edited in the editor; a variant here is a summary with Edit,
 * Preview and Send (2026-10-18: the module table went, to keep the page short).
 *
 * Column 3 of the campaigns screen (task-372, render 20): the list sits
 * beside it, so there is no way back to draw; each part is a card.
 */
export default function CampaignDetail() {
  const id = Number(useParams().id)
  const composition = useComposition(id)

  return (
    <div className="detail">
      <div className="detail-scroll">
        <ScreenState query={composition}>
          {composition.data && (
            <>
              <div className="detail-head">
                <h2>{composition.data.campaign.name}</h2>
              </div>
              <dl className="group fact-list">
                <Fact label="Status">{composition.data.campaign.status}</Fact>
                <Fact label="Variants">{composition.data.variants.length}</Fact>
                <Fact label="Updated">{formatDate(composition.data.campaign.updated_at)}</Fact>
              </dl>
              <CampaignResults campaignId={id} />
              {composition.data.variants.map((composed) => (
                <VariantSection key={composed.variant.id} campaignId={id} composed={composed}
                  stamp={composition.dataUpdatedAt} />
              ))}
              {/* Keyed by the campaign: a name typed here belongs to this campaign,
                  not the next one opened beside the list. */}
              <BlankVariant key={id} campaignId={id} />
            </>
          )}
        </ScreenState>
      </div>
    </div>
  )
}

/**
 * A variant from nothing. Secondary on purpose: duplicating is the primary way
 * a variant comes into being (Variant Editor interview Q5.1), so this sits
 * after the variants, below every Duplicate button.
 */
function BlankVariant({ campaignId }: { campaignId: number }) {
  const create = useCreateVariant(campaignId)
  const navigate = useNavigate()
  return (
    <section aria-labelledby="blank-variant" className="detail-section">
      <h3 id="blank-variant" className="group-title">
        New blank variant
      </h3>
      <div className="group group-body">
        <NameAndChannel
          nameLabel="Name"
          submitLabel="Create blank variant"
          pending={create.isPending}
          error={create.error}
          onSubmit={(value) =>
            create.mutate(value, {
              onSuccess: (created) => navigate(`/campaigns/${campaignId}/variants/${created.id}`),
            })
          }
        />
      </div>
    </section>
  )
}

function VariantSection({
  campaignId,
  composed,
  stamp,
}: {
  campaignId: number
  composed: ComposedVariant
  stamp: number
}) {
  const duplicate = useDuplicateVariant(campaignId)
  const { variant } = composed
  const envelope = composed.envelope_modules[0]?.module_data ?? {}

  return (
    <section aria-labelledby={`variant-${variant.id}`} className="detail-section">
      <h3 id={`variant-${variant.id}`} className="group-title">
        {variant.name}
      </h3>
      <div className="group">
        <dl className="fact-list">
          <Fact label="Channel">{variant.channel}</Fact>
          <Fact label="Status">{variant.status}</Fact>
          {/*
            The envelope is the header module's own fields (ADR-162 point 1),
            kept apart from the body by the server. Rendered generically: email
            has subject and preheader, and a channel without an envelope has none.
          */}
          {Object.entries(envelope).map(([key, value]) => (
            <Fact key={key} label={key}>
              {String(value ?? '—')}
            </Fact>
          ))}
          <Fact label="Modules">
            {composed.modules.length}
            {composed.module_limit != null ? ` of ${composed.module_limit}` : ''}
          </Fact>
        </dl>
        <div className="group-actions">
          <p className="btnrow">
            <Link className="btn-link" to={`/campaigns/${campaignId}/variants/${variant.id}`}>
              Edit {variant.name}
            </Link>
            <VariantPreview variant={variant} stamp={stamp} />
            <Link className="btn-link" to={`/campaigns/${campaignId}/variants/${variant.id}/send`}>
              Send {variant.name}…
            </Link>
            {/* Per variant: its topics in its language (ADR-188 addendum 2026-10-18). */}
            <SuggestForVariant variantId={variant.id} variantName={variant.name}
              language={composed.brand_profile?.language} />
            <Button
              className="btn-plain"
              isDisabled={duplicate.isPending}
              onPress={() => duplicate.mutate(variant.id)}
            >
              {duplicate.isPending ? 'Duplicating…' : 'Duplicate this variant'}
            </Button>
          </p>
          {duplicate.isSuccess && (
            <p role="status">
              {/* The mode is the server's answer, not assumed: it decides the default. */}
              Copied into this campaign as a draft,{' '}
              {duplicate.data.content_mode === 'keep'
                ? 'pointing at the same content.'
                : 'with the layout only — content is unbound.'}
              {duplicate.data.overrides_carried > 0 &&
                ` ${duplicate.data.overrides_carried} override(s) came across, now in your name.`}
            </p>
          )}
          {duplicate.isError && (
            <p role="alert">
              {duplicate.error instanceof HttpError && duplicate.error.status === 403
                ? // Two refusals share 403: no campaigns.manage, or a copy that would
                  // carry overrides without overrides.manage (task-113).
                  'You do not have permission for this copy. If the variant has overrides, ' +
                  'copying it needs permission to manage overrides as well.'
                : 'The variant could not be duplicated.'}
            </p>
          )}
        </div>
      </div>

      {composed.decision_slots.length > 0 && (
        <div className="group table-card">
          <h4 className="table-card__title">Decision slots</h4>
          <DataTable
            label={`Decision slots of ${variant.name}`}
            columns={[
              {
                key: 'name',
                header: 'Slot',
                isRowHeader: true,
                render: (s) => <Link to={`/decision-slots/${s.id}`}>{s.name}</Link>,
              },
              { key: 'strategy', header: 'Strategy', render: (s) => s.decision_strategy },
              { key: 'picks', header: 'Picks made', numeric: true, render: (s) => s.resolution_count },
              { key: 'unique', header: 'Distinct content', numeric: true, render: (s) => s.unique_content_count },
            ]}
            items={composed.decision_slots}
            emptyMessage=""
          />
        </div>
      )}
    </section>
  )
}

/**
 * A variant's Preview on the campaign page (2026-10-18): the editor's preview
 * sheet, so the email can be looked at without opening the editor. A summary
 * stands in for the module table; the modules are the editor's.
 */
function VariantPreview({ variant, stamp }: { variant: ComposedVariant['variant']; stamp: number }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <Button onPress={() => setOpen(true)}>Preview</Button>
      {open && <OpenPreview variant={variant} stamp={stamp} onClose={() => setOpen(false)} />}
    </>
  )
}

/** Mounted only while open: the manifests and the render are read then, not for every variant up front. */
function OpenPreview({ variant, stamp, onClose }: {
  variant: ComposedVariant['variant']
  stamp: number
  onClose: () => void
}) {
  const manifests = useModuleManifests(variant.channel)
  const byName = new Map((manifests.data ?? []).map((m) => [m.name, m]))
  return (
    <PreviewSheet variantId={variant.id} variantName={variant.name} stamp={stamp} byName={byName}
      isOpen onOpenChange={(next) => !next && onClose()} />
  )
}

