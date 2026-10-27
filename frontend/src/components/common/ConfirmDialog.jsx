import Icon from './Icon.jsx'
import Modal from './Modal.jsx'

/**
 * Destructive-action confirmation.
 *
 * `busy` keeps the dialog open but disables both buttons while the DELETE
 * request is in flight, so the user cannot fire it twice.
 */
export default function ConfirmDialog({
  open,
  title = 'Xác nhận xoá',
  message,
  confirmLabel = 'Xoá',
  cancelLabel = 'Huỷ',
  busy = false,
  onCancel,
  onConfirm,
}) {
  return (
    <Modal
      open={open}
      title={title}
      onClose={busy ? undefined : onCancel}
      size="sm"
      footer={
        <>
          <button type="button" onClick={onCancel} disabled={busy} className="btn-secondary">
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={busy}
            className="btn inline-flex bg-red-600 text-white hover:bg-red-700 active:bg-red-800"
          >
            {busy ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                Đang xoá…
              </>
            ) : (
              <>
                <Icon name="trash" className="h-4 w-4" />
                {confirmLabel}
              </>
            )}
          </button>
        </>
      }
    >
      <div className="flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-50 text-red-600 dark:bg-red-950/50 dark:text-red-400">
          <Icon name="warning" className="h-5 w-5" />
        </span>
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">{message}</p>
      </div>
    </Modal>
  )
}
