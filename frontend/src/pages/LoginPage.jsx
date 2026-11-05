import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import Icon from '../components/common/Icon.jsx'
import { useAuth } from '../contexts/AuthContext.jsx'
import { useTheme } from '../contexts/ThemeContext.jsx'
import { getErrorMessage } from '../utils/format.js'
import lhuLogo from '../assets/lhu-logo.png'

const DEMO_ACCOUNTS = [
  { role: 'Chủ sở hữu', username: 'owner', password: 'Owner@2026' },
  { role: 'Quản lý', username: 'manager', password: 'Manager@2026' },
  { role: 'Nhân viên', username: 'staff', password: 'Staff@2026' },
]

export default function LoginPage() {
  const { isAuthenticated, login } = useAuth()
  const { isDark, toggleTheme } = useTheme()
  const navigate = useNavigate()
  const location = useLocation()

  const [form, setForm] = useState({ username: '', password: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const redirectTo = location.state?.from ?? '/'

  if (isAuthenticated) {
    return <Navigate to={redirectTo} replace />
  }

  const updateField = (field) => (event) => {
    setForm((current) => ({ ...current, [field]: event.target.value }))
  }

  const fillDemo = (account) => {
    setForm({ username: account.username, password: account.password })
    setError('')
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setSubmitting(true)

    try {
      await login(form.username.trim(), form.password)
      navigate(redirectTo, { replace: true })
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Đăng nhập thất bại. Kiểm tra lại tên đăng nhập và mật khẩu.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center bg-slate-50 px-4 py-10 dark:bg-slate-950">
      {/* Theme toggle - top right */}
      <button
        type="button"
        onClick={toggleTheme}
        className="absolute right-5 top-5 rounded-xl border border-slate-200 bg-white p-2.5 text-slate-600 shadow-sm transition-colors hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
        aria-label={isDark ? 'Chuyển sang chế độ sáng' : 'Chuyển sang chế độ tối'}
      >
        <Icon name={isDark ? 'sun' : 'moon'} />
      </button>

      {/* Centered login card */}
      <div className="w-full max-w-md animate-fade-in rounded-2xl border border-slate-200 bg-white p-6 shadow-card sm:p-8 dark:border-slate-800 dark:bg-slate-900">
        {/* LHU logo */}
        <div className="mb-6 flex justify-center">
          <img src={lhuLogo} alt="Logo Đại học Lạc Hồng" className="h-20 w-auto object-contain sm:h-24" />
        </div>

        <h2 className="text-center text-2xl font-bold tracking-tight text-slate-900 dark:text-white">Đăng nhập</h2>
        <p className="mt-1 text-center text-sm text-slate-500 dark:text-slate-400">
          Sử dụng tài khoản được cấp để truy cập hệ thống.
        </p>

        <div className="mx-auto mt-5 h-1 w-16 rounded-full bg-[#2a5aaa]" />

        {error && (
          <div
            role="alert"
            className="mt-6 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300"
          >
            <Icon name="warning" className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-5" noValidate>
          <div>
            <label htmlFor="username" className="label">
              Tên đăng nhập
            </label>
            <div className="relative">
              <Icon
                name="user"
                className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
              />
              <input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                required
                value={form.username}
                onChange={updateField('username')}
                placeholder="owner"
                className="input pl-10 focus:border-[#2a5aaa] focus:ring-2 focus:ring-[#2a5aaa]/30"
              />
            </div>
          </div>

          <div>
            <label htmlFor="password" className="label">
              Mật khẩu
            </label>
            <div className="relative">
              <Icon
                name="shield"
                className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
              />
              <input
                id="password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                required
                value={form.password}
                onChange={updateField('password')}
                placeholder="••••••••"
                className="input pl-10 pr-12 focus:border-[#2a5aaa] focus:ring-2 focus:ring-[#2a5aaa]/30"
              />
              <button
                type="button"
                onClick={() => setShowPassword((current) => !current)}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg px-2 py-1 text-xs font-semibold text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700"
                aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
              >
                {showPassword ? 'Ẩn' : 'Hiện'}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#2a5aaa] px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#20498c] active:bg-[#1a3c75] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? (
              <>
                <Icon name="refresh" className="h-4 w-4 animate-spin" />
                Đang đăng nhập…
              </>
            ) : (
              <>
                Đăng nhập
                <Icon name="chevronRight" className="h-4 w-4" />
              </>
            )}
          </button>
        </form>

        <div className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Tài khoản dùng thử
          </p>
          <div className="mt-3 grid gap-2 sm:grid-cols-3">
            {DEMO_ACCOUNTS.map((account) => (
              <button
                key={account.username}
                type="button"
                onClick={() => fillDemo(account)}
                className="rounded-xl border border-slate-200 bg-white px-2.5 py-2 text-left transition-colors hover:border-[#2a5aaa] hover:bg-blue-50 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700"
              >
                <span className="block text-[11px] font-semibold text-slate-500 dark:text-slate-400">{account.role}</span>
                <span className="block truncate text-xs font-bold text-slate-800 dark:text-slate-100">
                  {account.username}
                </span>
              </button>
            ))}
          </div>
          <p className="mt-2 text-[11px] text-slate-400 dark:text-slate-500">
            Chỉ dùng trong môi trường phát triển. Mật khẩu được điền tự động.
          </p>
        </div>
      </div>
    </div>
  )
}
