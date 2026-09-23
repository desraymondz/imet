// Confirmation dialog for destructive actions

type ConfirmDialogProps = {
  title: string
  message: string
  confirmLabel: string
  cancelLabel?: string
  pending?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export default function ConfirmDialog({
  title,
  message,
  confirmLabel,
  cancelLabel = 'Cancel',
  pending = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    // Dim the page behind the dialog, and close when the backdrop is tapped
    <div
      className="absolute inset-0 z-50 flex items-center justify-center bg-[rgba(20,20,40,0.35)] px-6"
      onClick={() => {
        if (!pending) onCancel()
      }}
    >
      {/* Stop backdrop clicks inside the dialog from closing it */}
      <div
        role="alertdialog"
        aria-modal="true"
        aria-label={title}
        className="w-full max-w-xs rounded-[var(--r-lg)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-lg)]"
        onClick={event => event.stopPropagation()}
      >
        <h2 className="text-[17px] font-bold text-[var(--fg)]">{title}</h2>
        <p className="mt-2 text-[14px] text-[var(--fg-2)]">{message}</p>

        <div className="mt-5 flex flex-col gap-2">
          {/* Cancel button */}
          <button
            type="button"
            className="btn btn--neutral btn--block"
            onClick={onCancel}
            disabled={pending}
          >
            {cancelLabel}
          </button>

          {/* Confirm button */}
          <button
            type="button"
            className="btn btn--danger btn--block"
            onClick={onConfirm}
            disabled={pending}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}