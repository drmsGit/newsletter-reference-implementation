import type { ReactNode } from 'react'

/**
 * One part of a details column (task-372; HANDOFF section 6): its title on the
 * ground, its content in a white card of rows, a line between each row.
 */
export default function DetailSection({
  id,
  title,
  className,
  children,
}: {
  /** The title's id, which names the section for assistive technology. */
  id: string
  title: ReactNode
  className?: string
  children: ReactNode
}) {
  return (
    <section aria-labelledby={id} className={className ? `detail-section ${className}` : 'detail-section'}>
      <h3 id={id} className="group-title">
        {title}
      </h3>
      <div className="group card-rows">{children}</div>
    </section>
  )
}
