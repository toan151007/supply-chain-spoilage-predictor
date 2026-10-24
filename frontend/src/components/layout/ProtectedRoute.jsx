import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '../../contexts/AuthContext.jsx'
import Spinner from '../common/Spinner.jsx'

export default function ProtectedRoute() {
  const { isAuthenticated, initializing } = useAuth()
  const location = useLocation()

  if (initializing) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100 dark:bg-slate-950">
        <Spinner label="Đang kiểm tra phiên đăng nhập…" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return <Outlet />
}
