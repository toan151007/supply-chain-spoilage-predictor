import { useEffect, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../../contexts/AuthContext.jsx'
import Header from './Header.jsx'
import Sidebar from './Sidebar.jsx'

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const { logout } = useAuth()

  /* Close the mobile drawer after navigating; otherwise it covers the page
     the user just asked for. */
  useEffect(() => {
    setSidebarOpen(false)
  }, [location.pathname])

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-slate-950">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex min-h-screen flex-col lg:pl-72">
        <Header onOpenMenu={() => setSidebarOpen(true)} onLogout={handleLogout} />

        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>

        <footer className="border-t border-slate-200 px-4 py-4 text-center text-xs text-slate-400 dark:border-slate-800 dark:text-slate-500">
          FreshChain · Nền tảng quản trị chuỗi cung ứng chống lãng phí thực phẩm
        </footer>
      </div>
    </div>
  )
}
