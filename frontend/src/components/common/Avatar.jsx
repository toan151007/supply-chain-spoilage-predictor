/**
 * Shared avatar: the bundled image when the row has a known avatar key,
 * otherwise the user's initials. Keeps the header and the user table from
 * drifting apart.
 */
import { initials, resolveAvatar } from '../../utils/avatar.js'

const SIZES = {
  sm: 'h-8 w-8 text-xs rounded-lg',
  md: 'h-9 w-9 text-xs rounded-lg',
  lg: 'h-12 w-12 text-sm rounded-xl',
}

export default function Avatar({ user, size = 'md', className = '' }) {
  const src = resolveAvatar(user?.avatar_url)
  const name = user?.full_name || user?.username || ''

  return (
    <span
      className={[
        'flex shrink-0 items-center justify-center overflow-hidden bg-brand-100 font-bold text-brand-700 dark:bg-brand-900/60 dark:text-brand-300',
        SIZES[size] ?? SIZES.md,
        className,
      ].join(' ')}
    >
      {src ? (
        <img src={src} alt={name ? `Ảnh đại diện của ${name}` : 'Ảnh đại diện'} className="h-full w-full object-cover" />
      ) : (
        initials(name)
      )}
    </span>
  )
}
