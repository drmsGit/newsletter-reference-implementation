import { useContentPerformance, type ContentFigures } from '../api/resources'
import DataTable, { type DataColumn } from './DataTable'
import ScreenState from './ScreenState'

/**
 * A record's figures (task-359; ADR-196 addendum 2026-10-16), counted per
 * delivery, all time: the campaign results' definitions, per record. The
 * share is of all clicks in the emails that carried it — does it pull the
 * clicks when it is there — not clicks over deliveries, which reads very low.
 */
export function shareText(figures: ContentFigures | null | undefined): string {
  if (!figures || figures.deliveries === 0) return 'Not sent yet'
  if (figures.click_share == null) return 'No clicks yet'
  return `${Math.round(figures.click_share * 100)} %`
}

/** The columns a list of records shows its figures in (a category's records). */
export function figureColumns<T>(of: (item: T) => ContentFigures | null | undefined): DataColumn<T>[] {
  return [
    { key: 'deliveries', header: 'Sent in', render: (item) => String(of(item)?.deliveries ?? 0) },
    { key: 'clicks', header: 'Clicks', render: (item) => String(of(item)?.clicks ?? 0) },
    { key: 'share', header: 'Share of clicks', render: (item) => shareText(of(item)) },
  ]
}

type CampaignRow = { campaign_id: number; campaign_name: string; figures: ContentFigures }

const BY_CAMPAIGN: DataColumn<CampaignRow>[] = [
  { key: 'campaign', header: 'Campaign', isRowHeader: true, render: (row) => row.campaign_name },
  ...figureColumns<CampaignRow>((row) => row.figures),
]

/** The record page's Performance section. */
export function Performance({ recordId }: { recordId: number }) {
  const performance = useContentPerformance(recordId)
  const overall = performance.data?.overall
  return (
    <section aria-labelledby="record-performance-heading">
      <h2 id="record-performance-heading">Performance</h2>
      <ScreenState query={performance}>
        {overall && overall.deliveries === 0 ? (
          <p className="muted">No email or push that carried this record has been sent yet.</p>
        ) : (
          overall && (
            <>
              <dl className="facts">
                <dt>Sent in</dt>
                <dd>
                  {overall.deliveries} {overall.deliveries === 1 ? 'delivery' : 'deliveries'}
                  {overall.picked > 0 && `, ${overall.picked} of them picked by a personalised block`}
                </dd>
                <dt>Clicks on it</dt>
                <dd>
                  {overall.clicks}, from {overall.unique_clickers}{' '}
                  {overall.unique_clickers === 1 ? 'delivery' : 'deliveries'}
                </dd>
                <dt>Share of clicks</dt>
                <dd>
                  {shareText(overall)}
                  {overall.click_share != null && (
                    <span className="muted"> of the {overall.clicks_in_deliveries} clicks in the emails that carried it</span>
                  )}
                </dd>
              </dl>
              <DataTable
                label="By campaign"
                columns={BY_CAMPAIGN}
                items={(performance.data?.by_campaign ?? []).map((row) => ({ ...row, id: row.campaign_id }))}
                emptyMessage="No campaign has sent it yet."
              />
            </>
          )
        )}
      </ScreenState>
    </section>
  )
}
