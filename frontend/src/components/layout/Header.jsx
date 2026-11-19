import { useLocation } from 'react-router-dom'

import { useAuth } from '../../contexts/AuthContext.jsx'
import { useTheme } from '../../contexts/ThemeContext.jsx'
import Avatar from '../common/Avatar.jsx'
import Icon from '../common/Icon.jsx'

const PAGE_TITLES = {
  '/': 'Bảng điều khiển',
  '/products': 'Quản lý sản phẩm',
  '/inventory': 'Kho hàng',
  '/orders': 'Đơn hàng',
  '/alerts': 'Cảnh báo',
  '/forecasts': 'Dự báo nhu cầu',
  '/categories': 'Nhóm hàng',
  '/stores': 'Cửa hàng',
  '/transfers': 'Điều chuyển hàng',
  '/users': 'Quản lý người dùng',
}

export default function Header({ onOpenMenu, onLogout }) {
  const location = useLocation()
  const { user, roleLabel } = useAuth()
  const { isDark, toggleTheme } = useTheme()

  const title = PAGE_TITLES[location.pathname] ?? 'FreshChain'

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/80 backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/80">
      <div className="flex h-16 items-center gap-3 px-4 sm:px-6 lg:px-8">
        <button
          type="button"
          onClick={onOpenMenu}
          className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 lg:hidden"
          aria-label="Mở menu"
        >
          <Icon name="menu" />
        </button>

        <div className="min-w-0 flex-1">
          <p className="truncate text-base font-semibold text-slate-900 dark:text-white sm:text-lg">
            {title}
          </p>
          <p className="hidden truncate text-xs text-slate-500 dark:text-slate-400 sm:block">
            Quản trị chuỗi cung ứng · cập nhật theo thời gian thực
          </p>
        </div>

        <button
          type="button"
          onClick={toggleTheme}
          className="rounded-xl p-2.5 text-slate-600 transition-colors hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
          aria-label={isDark ? 'Chuyển sang chế độ sáng' : 'Chuyển sang chế độ tối'}
          title={isDark ? 'Chế độ sáng' : 'Chế độ tối'}
        >
          <Icon name={isDark ? 'sun' : 'moon'} />
        </button>

        <div className="flex items-center gap-3 rounded-xl border border-slate-200 py-1.5 pl-1.5 pr-2 dark:border-slate-700 sm:pr-3">
          <Avatar user={user} size="sm" />
          <div className="hidden leading-tight sm:block">
            <p className="max-w-[150px] truncate text-sm font-semibold text-slate-800 dark:text-slate-100">
              {user?.full_name || user?.username}
            </p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">{roleLabel}</p>
          </div>
        </div>

        <button
          type="button"
          onClick={onLogout}
          className="rounded-xl p-2.5 text-slate-600 transition-colors hover:bg-red-50 hover:text-red-600 dark:text-slate-300 dark:hover:bg-red-950/40 dark:hover:text-red-400"
          aria-label="Đăng xuất"
          title="Đăng xuất"
        >
          <Icon name="logout" />
        </button>
      </div>
    </header>
  )
}
