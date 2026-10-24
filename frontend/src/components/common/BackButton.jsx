import { useNavigate } from 'react-router-dom'

import Icon from './Icon.jsx'

export default function BackButton({ to = null, label = 'Quay lại', className = '' }) {
  const navigate = useNavigate()

  const handleClick = () => {
    if (to) {
      navigate(to)
      return
    }
    navigate(-1)
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className={[
        'btn-secondary inline-flex items-center gap-2 px-3 py-2',
        className,
      ].join(' ')}
    >
      <Icon name="chevronLeft" className="h-4 w-4" />
      <span>{label}</span>
    </button>
  )
}
