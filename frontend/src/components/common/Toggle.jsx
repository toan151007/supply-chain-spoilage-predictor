/**
 * Switch used for the per-user permission flags.
 *
 * A real `role="switch"` button keeps keyboard and screen-reader behaviour
 * correct without pulling in a UI library. The visual knob is a span so the
 * control can be styled entirely with Tailwind classes already in the theme.
 */
export default function Toggle({ checked, onChange, label, hint, disabled = false }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 px-3.5 py-2.5 dark:border-slate-700">
      <div className="min-w-0">
        <p className="text-sm font-medium text-slate-800 dark:text-slate-100">{label}</p>
        {hint && <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{hint}</p>}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={[
          'relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-slate-900',
          checked ? 'bg-brand-600' : 'bg-slate-300 dark:bg-slate-600',
          disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer',
        ].join(' ')}
      >
        <span
          aria-hidden="true"
          className={[
            'inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform',
            checked ? 'translate-x-5' : 'translate-x-0.5',
          ].join(' ')}
        />
      </button>
    </div>
  )
}
