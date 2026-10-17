import { CircleCheck, CircleSlash, Clock, Loader, OctagonX, type LucideIcon } from 'lucide-react'

/** A status as a chip: a glyph and a word, never colour alone (HANDOFF section 4). */
const STATUS: Record<string, { chip: string; icon: LucideIcon }> = {
  pending: { chip: 'chip-wait', icon: Clock },
  executing: { chip: 'chip-run', icon: Loader },
  approved: { chip: 'chip-ok', icon: CircleCheck },
  failed: { chip: 'chip-bad', icon: OctagonX },
  rejected: { chip: '', icon: CircleSlash },
  expired: { chip: '', icon: CircleSlash },
  withdrawn: { chip: '', icon: CircleSlash },
}

export default function StatusChip({ status }: { status: string }) {
  const { chip, icon: Icon } = STATUS[status] ?? { chip: '', icon: CircleSlash }
  return (
    <span className={`chip ${chip}`}>
      <Icon size={12} strokeWidth={2} aria-hidden="true" />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}
