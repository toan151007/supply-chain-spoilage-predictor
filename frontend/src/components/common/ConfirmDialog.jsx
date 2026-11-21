import Icon from './Icon.jsx'
import Modal from './Modal.jsx'

/* The dialog is used for more than deletion now (locking an account), so the
   colour of the confirm button follows the action instead of always red. */
const TONES = {
  danger: {
    button: 'bg-red-600 text-white hover:bg-red-700 active:bg-red-800',
    bubble: 'bg-red-50 text-red-600 dark:bg-red-950/50 dark:text-red-400',
  },
  warning: {
    button: 'bg-amber-600 text-white hover:bg-amber-700 active:bg-amber-800',
    bubble: 'bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-400',
  },
  brand: {
    button: 'bg-brand-600 text-white hover:bg-brand-700 active:bg-brand-800',
    bubble: 'bg-brand-50 text-brand-600 dark:bg-brand-950/50 dark:text-brand-300',
  },
}

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
  busyLabel = 'Đang xoá…',
  tone = 'danger',
  icon = 'trash',
  busy = false,
  onCancel,
  onConfirm,
}) {
  const theme = TONES[tone] ?? TONES.danger

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
            className={`btn inline-flex ${theme.button}`}
          >
            {busy ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                {busyLabel}
              </>
            ) : (
              <>
                <Icon name={icon} className="h-4 w-4" />
                {confirmLabel}
              </>
            )}
          </button>
        </>
      }
    >
      <div className="flex items-start gap-3">
        <span
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${theme.bubble}`}
        >
          <Icon name={icon === 'trash' ? 'warning' : icon} className="h-5 w-5" />
        </span>
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">{message}</p>
      </div>
    </Modal>
  )
}
