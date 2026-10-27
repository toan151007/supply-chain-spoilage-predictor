import { useEffect } from 'react'

import Icon from './Icon.jsx'

const TONES = {
  success: {
    wrapper:
      'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/60 dark:text-emerald-200',
    icon: 'check',
  },
  error: {
    wrapper:
      'border-red-200 bg-red-50 text-red-800 dark:border-red-900/60 dark:bg-red-950/60 dark:text-red-200',
    icon: 'warning',
  },
  info: {
    wrapper:
      'border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/60 dark:text-sky-200',
    icon: 'info',
  },
}

/**
 * Floating feedback banner.
 *
 * Sits at the top centre so it never overlaps the chatbot bubble in the
 * bottom-right corner, and auto-dismisses so the page does not accumulate
 * stale messages.
 */
export default function Toast({ type = 'success', message, onClose, duration = 4500 }) {
  useEffect(() => {
    if (!message) return undefined
    const timer = setTimeout(() => onClose?.(), duration)
    return () => clearTimeout(timer)
  }, [message, duration, onClose])

  if (!message) return null

  const tone = TONES[type] ?? TONES.info

  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 top-4 z-[60] flex justify-center px-4"
    >
      <div
        className={[
          'pointer-events-auto flex w-full max-w-md items-start gap-2.5 rounded-xl border px-4 py-3 text-sm font-medium shadow-lg',
          tone.wrapper,
        ].join(' ')}
      >
        <Icon name={tone.icon} className="mt-0.5 h-4 w-4 shrink-0" />
        <span className="flex-1 whitespace-pre-line">{message}</span>
        <button
          type="button"
          onClick={() => onClose?.()}
          className="shrink-0 rounded p-0.5 opacity-70 transition-opacity hover:opacity-100"
          aria-label="Đóng thông báo"
        >
          <Icon name="close" className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
