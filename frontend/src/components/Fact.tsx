import type { ReactNode } from 'react'

/** One label and value in a details card (`dl.group.fact-list`; HANDOFF section 6). */
export default function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="fact">
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}
