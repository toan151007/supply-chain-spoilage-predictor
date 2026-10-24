import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import Icon from '../components/common/Icon.jsx'
import { useAuth } from '../contexts/AuthContext.jsx'
import { useTheme } from '../contexts/ThemeContext.jsx'
import { getErrorMessage } from '../utils/format.js'

const DEMO_ACCOUNTS = [
  { role: 'Chủ sở hữu', username: 'owner', password: 'Owner@2026' },
  { role: 'Quản lý', username: 'manager', password: 'Manager@2026' },
  { role: 'Nhân viên', username: 'staff', password: 'Staff@2026' },
]

const HIGHLIGHTS = [
  'Dự báo nhu cầu bằng Prophet trên 5 năm dữ liệu',
  'Cảnh báo hàng sắp hết hạn và đề xuất nhập hàng',
  'Phân quyền owner / manager / staff rõ ràng',
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
    <div className="flex min-h-screen bg-slate-100 dark:bg-slate-950">
      {/* Brand panel */}
      <section className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-gradient-to-br from-brand-700 via-brand-600 to-emerald-500 p-10 text-white lg:flex xl:p-14">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-24 -top-24 h-80 w-80 rounded-full bg-white/10 blur-2xl"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-32 -left-16 h-96 w-96 rounded-full bg-emerald-300/20 blur-3xl"
        />

        <div className="relative flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/15 ring-1 ring-white/30">
            <Icon name="leaf" className="h-6 w-6" />
          </span>
          <div>
            <p className="text-lg font-bold tracking-tight">FreshChain</p>
            <p className="text-xs text-emerald-100">Quản trị chuỗi cung ứng chống lãng phí</p>
          </div>
        </div>

        <div className="relative max-w-lg">
          <p className="mb-3 inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-xs font-semibold ring-1 ring-white/25">
            <Icon name="sparkles" className="h-4 w-4" />
            AI dự báo nhu cầu &amp; hạn sử dụng
          </p>
          <h1 className="text-4xl font-bold leading-tight tracking-tight xl:text-5xl">
            Giảm lãng phí thực phẩm,
            <br />
            tăng hiệu quả vận hành.
          </h1>
          <p className="mt-5 max-w-md text-sm leading-relaxed text-emerald-50/90">
            Nền tảng quản trị chuỗi cung ứng cho chuỗi cửa hàng bán lẻ và F&amp;B: dự báo nhu cầu,
            tối ưu nhập hàng và kiểm soát hàng cận hạn trên một màn hình duy nhất.
          </p>

          <ul className="mt-8 space-y-3">
            {HIGHLIGHTS.map((item) => (
              <li key={item} className="flex items-start gap-3 text-sm text-emerald-50">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/20">
                  <Icon name="check" className="h-3.5 w-3.5" strokeWidth={2.4} />
                </span>
                {item}
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-emerald-100/80">
          Đồ án tốt nghiệp · Microsoft SQL Server 2025 · FastAPI · React
        </p>
      </section>

      {/* Form panel */}
      <section className="relative flex w-full flex-col justify-center px-5 py-10 sm:px-10 lg:w-1/2 lg:px-16">
        <button
          type="button"
          onClick={toggleTheme}
          className="absolute right-5 top-5 rounded-xl border border-slate-200 bg-white p-2.5 text-slate-600 shadow-sm transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
          aria-label={isDark ? 'Chuyển sang chế độ sáng' : 'Chuyển sang chế độ tối'}
        >
          <Icon name={isDark ? 'sun' : 'moon'} />
        </button>

        <div className="mx-auto w-full max-w-md animate-fade-in">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-600 text-white">
              <Icon name="leaf" className="h-6 w-6" />
            </span>
            <div>
              <p className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">FreshChain</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Quản trị chuỗi cung ứng chống lãng phí</p>
            </div>
          </div>

          <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-3xl">
            Đăng nhập
          </h2>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            Sử dụng tài khoản được cấp để truy cập hệ thống.
          </p>

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
                  className="input pl-10"
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
                  className="input pl-10 pr-12"
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

            <button type="submit" disabled={submitting} className="btn-primary w-full py-3">
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

          <div className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-white/60 p-4 dark:border-slate-700 dark:bg-slate-900/60">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Tài khoản dùng thử
            </p>
            <div className="mt-3 grid gap-2 sm:grid-cols-3">
              {DEMO_ACCOUNTS.map((account) => (
                <button
                  key={account.username}
                  type="button"
                  onClick={() => fillDemo(account)}
                  className="rounded-xl border border-slate-200 bg-white px-2.5 py-2 text-left transition-colors hover:border-brand-400 hover:bg-brand-50 dark:border-slate-700 dark:bg-slate-800 dark:hover:border-brand-600 dark:hover:bg-slate-700"
                >
                  <span className="block text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                    {account.role}
                  </span>
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
      </section>
    </div>
  )
}
