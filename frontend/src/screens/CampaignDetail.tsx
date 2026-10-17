import { Button } from 'react-aria-components'
import { Link, useNavigate, useParams } from 'react-router'

import {
  useComposition,
  useCreateVariant,
  useDuplicateVariant,
  type ComposedModule,
  type ComposedVariant,
} from '../api/resources'
import { HttpError } from '../api/session'
import CampaignResults from '../components/CampaignResults'
import DataTable, { type DataColumn } from '../components/DataTable'
import Fact from '../components/Fact'
import NameAndChannel from '../components/NameAndChannel'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'

/**
 * One campaign, variant by variant (inventory B11).
 *
 * Everything comes from one read, `GET /campaigns/{id}/composition`, which
 * already carries what the Jinja page used to compute for itself: whether a
 * module may be overridden, the channel's module limit, which module is the
 * envelope. **This screen derives none of it.** It shows the server's answers,
 * so there is one place those rules live.
 *
 * The one write is Duplicate, the primary way a variant comes into being
 * (Variant Editor interview Q5.1). Editing modules, overrides and slots comes
 * with the rest of the write surface.
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
                <VariantSection key={composed.variant.id} campaignId={id} composed={composed} />
              ))}
              <BlankVariant campaignId={id} />
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
}: {
  campaignId: number
  composed: ComposedVariant
}) {
  const duplicate = useDuplicateVariant(campaignId)
  const { variant } = composed
  const slotNames = new Map(composed.decision_slots.map((s) => [s.id, s.name]))
  const envelope = composed.envelope_modules[0]?.module_data ?? {}

  const columns: DataColumn<ComposedModule>[] = [
    { key: 'position', header: 'Position', render: (m) => m.position },
    {
      key: 'type',
      header: 'Module',
      isRowHeader: true,
      render: (m) => (m.known ? m.module_type : `${m.module_type} (not on this channel)`),
    },
    {
      key: 'source',
      header: 'Content',
      /**
       * Where the module's content comes from, in the three ways a module can
       * have it: bound to a record, filled by a decision slot per recipient, or
       * typed into the module itself.
       */
      render: (m) =>
        m.content_record_id != null ? (
          <Link to={`/content/${m.content_record_id}`}>
            {m.content_record_title ?? `Record #${m.content_record_id}`}
          </Link>
        ) : m.decision_slot_id != null ? (
          <Link to={`/decision-slots/${m.decision_slot_id}`}>
            Slot: {slotNames.get(m.decision_slot_id) ?? `#${m.decision_slot_id}`}
          </Link>
        ) : (
          'Typed in the module'
        ),
    },
    {
      key: 'override',
      header: 'Overridden here',
      /**
       * Which fields this module overrides, not just that it has an override
       * (task-262): a module with one overridden headline still takes its body
       * from the catalogue, and a catalogue edit to that body is not an
       * override. Every other field is the catalogue's.
       */
      render: (m) => {
        const fields = Object.keys(m.active_override?.field_overrides ?? {})
        if (!m.active_override || fields.length === 0) return '—'
        const by = m.active_override.overridden_by ? ` by ${m.active_override.overridden_by}` : ''
        return `${fields.join(', ')}${by}`
      },
    },
  ]

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
            <Link className="btn-link" to={`/campaigns/${campaignId}/variants/${variant.id}/send`}>
              Send {variant.name}…
            </Link>
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

      <div className="group table-card">
        <h4 className="table-card__title">Modules of {variant.name}</h4>
        <DataTable
          label={`Modules of ${variant.name}`}
          columns={columns}
          items={composed.modules}
          emptyMessage="This variant has no modules yet."
        />
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
