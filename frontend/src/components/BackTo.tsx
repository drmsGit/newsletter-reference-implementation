import { ChevronLeft } from 'lucide-react'
import { Link } from 'react-router'

/** The way back up a drill-in (task-372): "‹ Content" above a list's title. */
export default function BackTo({ to, label }: { to: string; label: string }) {
  return (
    <Link className="back-link" to={to}>
      <ChevronLeft size={14} strokeWidth={1.75} aria-hidden="true" />
      {label}
    </Link>
  )
}
