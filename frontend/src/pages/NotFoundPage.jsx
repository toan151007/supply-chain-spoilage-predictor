import { Link } from 'react-router-dom'

import Icon from '../components/common/Icon.jsx'

export default function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-300">
        <Icon name="search" className="h-8 w-8" />
      </span>
      <p className="mt-6 text-4xl font-bold tracking-tight text-slate-900 dark:text-white">404</p>
      <h1 className="mt-2 text-lg font-semibold text-slate-800 dark:text-slate-100">
        Trang bạn tìm không tồn tại
      </h1>
      <p className="mt-2 max-w-sm text-sm text-slate-500 dark:text-slate-400">
        Đường dẫn có thể đã thay đổi hoặc tính năng này chưa được triển khai.
      </p>
      <Link to="/" className="btn-primary mt-6">
        <Icon name="dashboard" className="h-4 w-4" />
        Về bảng điều khiển
      </Link>
    </div>
  )
}
