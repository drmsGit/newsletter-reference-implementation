import { useState, type ReactNode } from 'react'
import { Button, Dialog, Heading, Modal, ModalOverlay } from 'react-aria-components'

/**
 * A list's "New ..." button and the dialog it opens (task-372, decision 22;
 * render 45): the title, the form the list already had, Cancel and Create.
 * The form is given a way to close the dialog; Esc closes it too.
 */
export default function NewDialog({
  label,
  children,
}: {
  label: string
  children: (close: () => void) => ReactNode
}) {
  const [open, setOpen] = useState(false)
  const id = `new-${label.toLowerCase().replace(/\W+/g, '-')}`
  return (
    <>
      <Button className="btn-primary" onPress={() => setOpen(true)}>
        {label}
      </Button>
      <ModalOverlay isOpen={open} onOpenChange={setOpen} isDismissable className="preview-overlay">
        <Modal className="create-modal">
          <Dialog aria-labelledby={id}>
            <Heading slot="title" id={id}>
              {label}
            </Heading>
            {children(() => setOpen(false))}
          </Dialog>
        </Modal>
      </ModalOverlay>
    </>
  )
}

/** Cancel and the form's submit, at the dialog's foot. */
export function DialogActions({ onCancel, children }: { onCancel: () => void; children: ReactNode }) {
  return (
    <div className="dialog-actions">
      <Button onPress={onCancel}>Cancel</Button>
      {children}
    </div>
  )
}
