import { NavLink } from 'react-router-dom'

import { useAuth } from '../../contexts/AuthContext.jsx'
import Icon from '../common/Icon.jsx'

const NAV_GROUPS = [
  {
    title: 'Tổng quan',
    items: [
      { to: '/', end: true, label: 'Bảng điều khiển', icon: 'dashboard' },
      { to: '/products', label: 'Sản phẩm', icon: 'box' },
    ],
  },
  {
    title: 'Vận hành',
    items: [
      { label: 'Tồn kho', icon: 'inventory', soon: true },
      { label: 'Đơn hàng', icon: 'orders', soon: true },
      { label: 'Dự báo nhu cầu', icon: 'forecast', soon: true },
      { label: 'Cảnh báo', icon: 'alerts', soon: true },
    ],
  },
  {
    title: 'Phân tích',
    adminOnly: true,
    items: [
      { label: 'Đề xuất nhập hàng', icon: 'recommendations', soon: true },
      { label: 'Báo cáo', icon: 'reports', soon: true },
    ],
  },
]

function NavigationItem({ item }) {
  if (item.soon) {
    return (
      <div
        className="flex cursor-not-allowed items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-400 dark:text-slate-500"
        title="Sẽ triển khai ở bước tiếp theo"
      >
        <Icon name={item.icon} className="h-5 w-5 shrink-0" />
        <span className="flex-1 truncate">{item.label}</span>
        <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:bg-slate-800 dark:text-slate-500">
          Sắp
        </span>
      </div>
    )
  }

  return (
    <NavLink
      to={item.to}
      end={item.end}
      className={({ isActive }) =>
        [
          'group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors',
          isActive
            ? 'bg-brand-600 text-white shadow-sm'
            : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white',
        ].join(' ')
      }
    >
      <Icon name={item.icon} className="h-5 w-5 shrink-0" />
      <span className="flex-1 truncate">{item.label}</span>
    </NavLink>
  )
}

export default function Sidebar({ open, onClose }) {
  const { roleLabel, isAdmin } = useAuth()

  return (
    <>
      {/* Mobile backdrop */}
      <div
        onClick={onClose}
        aria-hidden="true"
        className={[
          'fixed inset-0 z-40 bg-slate-950/50 backdrop-blur-sm transition-opacity lg:hidden',
          open ? 'opacity-100' : 'pointer-events-none opacity-0',
        ].join(' ')}
      />

      <aside
        className={[
          'fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-slate-200 bg-white transition-transform duration-200 dark:border-slate-800 dark:bg-slate-900 lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full',
        ].join(' ')}
        aria-label="Điều hướng chính"
      >
        <div className="flex h-16 items-center gap-3 border-b border-slate-200 px-5 dark:border-slate-800">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm">
            <Icon name="leaf" className="h-6 w-6" />
          </span>
          <div className="min-w-0">
            <p className="truncate text-base font-bold tracking-tight text-slate-900 dark:text-white">
              FreshChain
            </p>
            <p className="truncate text-xs text-slate-500 dark:text-slate-400">Chống lãng phí thực phẩm</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="ml-auto rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800 lg:hidden"
            aria-label="Đóng menu"
          >
            <Icon name="close" />
          </button>
        </div>

        <nav className="scrollbar-thin flex-1 space-y-6 overflow-y-auto px-3 py-5">
          {NAV_GROUPS.filter((group) => !group.adminOnly || isAdmin).map((group) => (
            <div key={group.title}>
              <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                {group.title}
              </p>
              <div className="space-y-1">
                {group.items.map((item) => (
                  <NavigationItem key={item.label} item={item} />
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div className="border-t border-slate-200 p-4 dark:border-slate-800">
          <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
            <p className="text-xs font-semibold text-slate-700 dark:text-slate-200">
              Vai trò của bạn: {roleLabel}
            </p>
            <p className="mt-1 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">
              {isAdmin
                ? 'Bạn có toàn quyền quản trị dữ liệu và báo cáo.'
                : 'Bạn thao tác tồn kho, đơn hàng và trạng thái cảnh báo.'}
            </p>
          </div>
          <p className="mt-3 text-center text-[11px] text-slate-400 dark:text-slate-500">
            Đồ án tốt nghiệp · v0.1
          </p>
        </div>
      </aside>
    </>
  )
}
