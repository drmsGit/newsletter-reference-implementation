import { useEffect, useState, type ReactNode } from 'react'
import { Button, VisuallyHidden } from 'react-aria-components'

const WAITING = 'Asking the model…'

/**
 * The button for every model call (task-100). A real call takes seconds and
 * every press is a paid generation, so while one runs the button ignores
 * presses (React Aria's `isPending`, which keeps focus where `isDisabled`
 * would drop it), says so, and counts the seconds after two, so a long call
 * visibly is not stuck. No cancel: the tokens are spent either way.
 *
 * The count is hidden from screen readers, so the button's name does not
 * change every second; they hear once, from the status line, that the model
 * was asked.
 */
export default function AIButton({
  onPress,
  pending,
  children,
}: {
  onPress: () => void
  pending: boolean
  children: ReactNode
}) {
  return (
    <>
      <Button onPress={onPress} isPending={pending}>
        {pending ? (
          <>
            {WAITING}
            <Elapsed />
          </>
        ) : (
          children
        )}
      </Button>
      <VisuallyHidden role="status">{pending ? WAITING : ''}</VisuallyHidden>
    </>
  )
}

/** Mounted only while a call runs, so each call counts from zero. */
function Elapsed() {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => clearInterval(timer)
  }, [])
  return seconds >= 2 ? <span aria-hidden="true"> {seconds} s</span> : null
}
