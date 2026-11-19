import AvatarToan from '../assets/Avatar.jpg'

/**
 * `users.avatar_url` stores a logical key rather than a build path: Vite
 * hashes asset filenames on every build, so a stored `/assets/avatar-abc.jpg`
 * would break after the next deployment. Real URLs still pass through.
 */
const AVATAR_ASSETS = {
  toan: AvatarToan,
}

export function resolveAvatar(avatarUrl) {
  if (!avatarUrl) return null
  if (AVATAR_ASSETS[avatarUrl]) return AVATAR_ASSETS[avatarUrl]
  if (/^(https?:)?\//.test(avatarUrl)) return avatarUrl
  return null
}

export function initials(name = '') {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}
