/**
 * Label + control wrapper used by every CRUD form.
 *
 * Keeps the required marker, hint text and spacing identical across pages so
 * the forms do not drift apart visually.
 */
export default function Field({ label, htmlFor, required = false, hint, className = '', children }) {
  return (
    <div className={className}>
      <label htmlFor={htmlFor} className="label">
        {label}
        {required && <span className="ml-0.5 text-red-500">*</span>}
      </label>
      {children}
      {hint && <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">{hint}</p>}
    </div>
  )
}
