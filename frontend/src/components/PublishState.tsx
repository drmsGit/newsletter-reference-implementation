import { Button } from 'react-aria-components'

import { usePublishRecord } from '../api/resources'
import { SaveState } from './EditorFields'

/**
 * Design pass D5: a send uses the published version, so say when that lags,
 * with a one-click Publish. Shared by the composer's catalogue module and the
 * record page (Content Write Surface pass, decision 3), so the two say it the
 * same way.
 */
export default function PublishState({
  recordId,
  detail,
}: {
  recordId: number
  detail: { latest_version_number?: number | null; unpublished_changes: boolean }
}) {
  const publish = usePublishRecord(recordId)
  if (!detail.unpublished_changes) return null
  return (
    <p className="publish-state" role="status">
      {detail.latest_version_number == null
        ? 'Not published yet, so it cannot be sent until it is.'
        : `Changed since version ${detail.latest_version_number} was published — sends still use version ${detail.latest_version_number}.`}{' '}
      <Button isDisabled={publish.isPending} onPress={() => publish.mutate()}>
        {publish.isPending ? 'Publishing…' : 'Publish'}
      </Button>
      <SaveState mutation={publish} what="the record" />
    </p>
  )
}
