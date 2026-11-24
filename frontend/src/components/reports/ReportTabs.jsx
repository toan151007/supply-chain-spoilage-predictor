import { NavLink } from 'react-router-dom'

import Icon from '../common/Icon.jsx'

const TABS = [
  { to: '/reports/spoilage', label: 'Rủi ro hao hụt', icon: 'shield' },
  { to: '/reports/top-selling', label: 'Mặt hàng bán chạy', icon: 'trendingUp' },
]

/**
 * Shared tab bar for the two report screens. The sidebar has one report
 * entry, so these tabs are what move the user between them without a
 * second menu item.
 */
export default function ReportTabs() {
  return (
    <div className="card flex flex-wrap gap-1.5 p-1.5">
      {TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          className={({ isActive }) =>
            [
              'btn flex-1 justify-center sm:flex-none',
              isActive
                ? 'bg-brand-600 text-white hover:bg-brand-700'
                : 'bg-transparent text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800',
            ].join(' ')
          }
        >
          <Icon name={tab.icon} className="h-4 w-4" />
          {tab.label}
        </NavLink>
      ))}
    </div>
  )
}
