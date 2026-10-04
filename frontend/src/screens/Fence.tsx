import { Button } from 'react-aria-components'

import { useUnblock, type VariantFence } from '../api/resources'
import { useSession } from '../api/session'
import { SaveState } from '../components/EditorFields'

const time = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

/**
 * "Blocked by X, last updated HH:MM — unblock" (ADR-180, task-254).
 *
 * Advisory for a person: nothing here stops an edit, and anyone may unblock.
 * What a fence holds off is a machine — an automation waits until the fence
 * lapses, 30 minutes after the last edit, or until a person unblocks it. A
 * lapsed fence is just "last edited by X at HH:MM".
 */
export default function Fence({
  campaignId,
  variantId,
  fence,
}: {
  campaignId: number
  variantId: number
  fence: VariantFence | null | undefined
}) {
  const session = useSession()
  const unblock = useUnblock(campaignId)
  if (!fence) return null
  const mine = fence.by != null && fence.by === session.data?.user?.email
  const who = mine ? 'you' : fence.by ?? 'someone'

  if (!fence.active) {
    return <p className="muted fence">Last edited by {who} at {time(fence.at)}.</p>
  }
  return (
    <p className={mine ? 'muted fence' : 'fence fence--other'} role="status">
      {mine ? (
        <>You are editing this variant (last edit {time(fence.at)}). Automations wait until 30 minutes after your last edit.</>
      ) : (
        <>
          <strong>{who}</strong> is working on this variant (last edit {time(fence.at)}). Your edits
          still save; automations wait until it lapses or someone unblocks it.
        </>
      )}{' '}
      <Button isDisabled={unblock.isPending} onPress={() => unblock.mutate(variantId)}>
        Unblock
      </Button>
      <SaveState mutation={unblock} what="the fence" />
    </p>
  )
}
