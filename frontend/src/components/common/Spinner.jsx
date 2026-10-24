import Icon from './Icon.jsx'

export default function Spinner({ label = 'Đang tải…', className = '' }) {
  return (
    <div className={`flex items-center justify-center gap-3 text-sm text-slate-500 dark:text-slate-400 ${className}`}>
      <Icon name="refresh" className="h-5 w-5 animate-spin" />
      <span>{label}</span>
    </div>
  )
}
