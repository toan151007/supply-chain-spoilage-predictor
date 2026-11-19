import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import Avatar from '../components/common/Avatar.jsx'
import ConfirmDialog from '../components/common/ConfirmDialog.jsx'
import Field from '../components/common/Field.jsx'
import Icon from '../components/common/Icon.jsx'
import Modal from '../components/common/Modal.jsx'
import Toast from '../components/common/Toast.jsx'
import Toggle from '../components/common/Toggle.jsx'
import { useAuth } from '../contexts/AuthContext.jsx'
import api from '../services/api.js'
import { formatDate, getErrorMessage } from '../utils/format.js'

const ROLE_META = {
  owner: {
    label: 'Chủ sở hữu',
    badge: 'bg-violet-50 text-violet-700 dark:bg-violet-950/50 dark:text-violet-300',
  },
  manager: {
    label: 'Quản lý',
    badge: 'bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300',
  },
  staff: {
    label: 'Nhân viên',
    badge: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  },
}

const PERMISSION_OPTIONS = [
  {
    key: 'can_edit_product',
    label: 'Thêm / sửa sản phẩm',
    short: 'Sửa sản phẩm',
    hint: 'Tạo mới và cập nhật thông tin sản phẩm.',
  },
  {
    key: 'can_delete_product',
    label: 'Xoá sản phẩm',
    short: 'Xoá sản phẩm',
    hint: 'Cho phép xoá sản phẩm khỏi danh mục.',
  },
  {
    key: 'can_view_report',
    label: 'Xem báo cáo',
    short: 'Báo cáo',
    hint: 'Hiện mục Báo cáo ở thanh điều hướng và cho phép xuất dữ liệu.',
  },
  {
    key: 'can_manage_inventory',
    label: 'Quản lý kho hàng',
    short: 'Kho hàng',
    hint: 'Nhập, điều chỉnh và theo dõi tồn kho theo lô.',
  },
  {
    key: 'can_manage_order',
    label: 'Quản lý đơn hàng',
    short: 'Đơn hàng',
    hint: 'Tạo, sửa và cập nhật trạng thái đơn hàng.',
  },
  {
    key: 'can_manage_transfer',
    label: 'Điều chuyển hàng',
    short: 'Điều chuyển',
    hint: 'Đề xuất và xử lý yêu cầu chuyển hàng giữa cửa hàng.',
  },
  {
    key: 'can_manage_user',
    label: 'Quản lý người dùng',
    short: 'Người dùng',
    hint: 'Tạo tài khoản và phân quyền cho người khác.',
  },
]

const ALL_PERMISSIONS = PERMISSION_OPTIONS.reduce((flags, option) => {
  flags[option.key] = true
  return flags
}, {})

const ROLE_DEFAULTS = {
  owner: { ...ALL_PERMISSIONS },
  manager: {
    ...ALL_PERMISSIONS,
    can_delete_product: false,
    can_manage_user: false,
  },
  staff: {
    ...ALL_PERMISSIONS,
    can_edit_product: false,
    can_delete_product: false,
    can_view_report: false,
    can_manage_user: false,
  },
}

const PERMISSION_KEYS = PERMISSION_OPTIONS.map((option) => option.key)

const EMPTY_FORM = {
  full_name: '',
  username: '',
  password: '',
  email: '',
  role: 'manager',
  is_active: true,
  avatar_url: '',
  ...ROLE_DEFAULTS.manager,
}

function TableSkeleton() {
  return (
    <>
      {Array.from({ length: 4 }).map((_, idx) => (
        <tr key={idx} className="animate-pulse">
          {Array.from({ length: 5 }).map((__, cell) => (
            <td key={cell} className="px-4 py-4">
              <div className="h-3 rounded bg-slate-100 dark:bg-slate-800" />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}

export default function UsersPage() {
  const navigate = useNavigate()
  const { user: currentUser, isOwner } = useAuth()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [items, setItems] = useState([])
  const [reloadKey, setReloadKey] = useState(0)

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const [toast, setToast] = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')

    api
      .get('/users', { params: { page_size: 200 } })
      .then((response) => {
        if (!cancelled) setItems(response.data.items || [])
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(getErrorMessage(requestError, 'Không tải được danh sách người dùng.'))
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [reloadKey])

  const setField = (name, value) => {
    setForm((previous) => ({ ...previous, [name]: value }))
  }

  const applyRoleDefaults = (role) => {
    setForm((previous) => ({ ...previous, role, ...ROLE_DEFAULTS[role] }))
  }

  const openCreate = () => {
    setEditing(null)
    setForm({ ...EMPTY_FORM })
    setFormError('')
    setFormOpen(true)
  }

  const openEdit = (account) => {
    setEditing(account)
    setForm({
      full_name: account.full_name ?? '',
      username: account.username ?? '',
      password: '',
      email: account.email ?? '',
      role: account.role,
      is_active: Boolean(account.is_active),
      avatar_url: account.avatar_url ?? '',
      ...PERMISSION_KEYS.reduce((flags, key) => {
        flags[key] = Boolean(account[key])
        return flags
      }, {}),
    })
    setFormError('')
    setFormOpen(true)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    const fullName = form.full_name.trim()
    const username = form.username.trim()
    const password = form.password
    const creating = !editing

    if (!fullName) {
      setFormError('Vui lòng nhập họ tên.')
      return
    }
    if (!username) {
      setFormError('Vui lòng nhập tên đăng nhập.')
      return
    }
    if (creating && password.length < 6) {
      setFormError('Mật khẩu phải có ít nhất 6 ký tự.')
      return
    }
    if (!creating && password && password.length < 6) {
      setFormError('Mật khẩu mới phải có ít nhất 6 ký tự.')
      return
    }

    const permissionPayload = PERMISSION_KEYS.reduce((flags, key) => {
      flags[key] = Boolean(form[key])
      return flags
    }, {})

    const payload = {
      full_name: fullName,
      username,
      email: form.email.trim() || null,
      role: form.role,
      is_active: Boolean(form.is_active),
      avatar_url: form.avatar_url || null,
      ...permissionPayload,
    }

    setSaving(true)
    setFormError('')

    try {
      if (creating) {
        await api.post('/users', { ...payload, password })
      } else {
        const update = { ...payload }
        if (password) update.password = password
        await api.put(`/users/${editing.user_id}`, update)
      }

      setFormOpen(false)
      setToast({
        type: 'success',
        message: creating ? 'Đã tạo tài khoản mới.' : 'Đã cập nhật tài khoản.',
      })
      setReloadKey((key) => key + 1)
    } catch (requestError) {
      setFormError(getErrorMessage(requestError, 'Không lưu được tài khoản.'))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return

    setDeleting(true)
    try {
      await api.delete(`/users/${deleteTarget.user_id}`)
      setToast({
        type: 'success',
        message: `Đã xoá tài khoản "${deleteTarget.full_name || deleteTarget.username}".`,
      })
      setDeleteTarget(null)
      setReloadKey((key) => key + 1)
    } catch (requestError) {
      setToast({
        type: 'error',
        message: getErrorMessage(requestError, 'Không xoá được tài khoản.'),
      })
      setDeleteTarget(null)
    } finally {
      setDeleting(false)
    }
  }

  if (!isOwner) {
    return (
      <div className="card mx-auto max-w-md px-6 py-14 text-center">
        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-400">
          <Icon name="shield" className="h-6 w-6" />
        </span>
        <p className="mt-3 font-semibold text-slate-900 dark:text-white">Không có quyền truy cập</p>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Chỉ chủ sở hữu hệ thống mới quản lý được tài khoản và phân quyền.
        </p>
        <button type="button" onClick={() => navigate('/')} className="btn-secondary mx-auto mt-4">
          Về bảng điều khiển
        </button>
      </div>
    )
  }

  const roleOptions = editing?.role === 'owner' ? ['owner', 'manager', 'staff'] : ['manager', 'staff']

  return (
    <div className="animate-fade-in space-y-5">
      <Toast type={toast?.type} message={toast?.message} onClose={() => setToast(null)} />

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="btn-secondary inline-flex items-center gap-2 px-3 py-2"
        >
          <Icon name="chevronLeft" className="h-4 w-4" />
          <span>Quay lại</span>
        </button>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-2xl">
            Quản lý người dùng
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Tạo tài khoản và bật/tắt từng quyền hạn chi tiết cho quản lý và nhân viên.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={openCreate} className="btn-primary w-fit">
            <Icon name="plus" className="h-4 w-4" />
            Thêm tài khoản
          </button>
          <button
            type="button"
            onClick={() => setReloadKey((key) => key + 1)}
            className="btn-secondary w-fit"
          >
            <Icon name="refresh" className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Tải lại
          </button>
        </div>
      </div>

      <div className="card overflow-hidden">
        {error ? (
          <div className="flex flex-col items-center gap-3 px-6 py-16 text-center">
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-red-50 text-red-600 dark:bg-red-950/50 dark:text-red-400">
              <Icon name="warning" className="h-6 w-6" />
            </span>
            <div>
              <p className="font-semibold text-slate-900 dark:text-white">Không tải được dữ liệu</p>
              <p className="mt-1 max-w-md text-sm text-slate-500 dark:text-slate-400">{error}</p>
            </div>
            <button type="button" onClick={() => setReloadKey((key) => key + 1)} className="btn-secondary mt-1">
              <Icon name="refresh" className="h-4 w-4" />
              Thử lại
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/70 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-400">
                  <th className="px-4 py-3 font-semibold">Người dùng</th>
                  <th className="px-4 py-3 font-semibold">Vai trò</th>
                  <th className="px-4 py-3 font-semibold">Quyền hạn</th>
                  <th className="px-4 py-3 font-semibold">Trạng thái</th>
                  <th className="px-4 py-3 font-semibold">Ngày tạo</th>
                  <th className="px-4 py-3 text-right font-semibold">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {loading ? (
                  <TableSkeleton />
                ) : items.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-16 text-center">
                      <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
                        <Icon name="users" className="h-6 w-6" />
                      </span>
                      <p className="mt-3 font-semibold text-slate-700 dark:text-slate-200">Chưa có tài khoản nào</p>
                    </td>
                  </tr>
                ) : (
                  items.map((account) => {
                    const meta = ROLE_META[account.role] ?? ROLE_META.staff
                    const granted = PERMISSION_OPTIONS.filter((option) => account[option.key])
                    const isSelf = account.user_id === currentUser?.user_id

                    return (
                      <tr
                        key={account.user_id}
                        className="transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-800/40"
                      >
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-3">
                            <Avatar user={account} size="md" />
                            <div className="min-w-0">
                              <p className="flex items-center gap-2 font-semibold text-slate-900 dark:text-white">
                                <span className="truncate">{account.full_name}</span>
                                {isSelf && (
                                  <span className="badge bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
                                    Bạn
                                  </span>
                                )}
                              </p>
                              <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                                @{account.username}
                                {account.email ? ` · ${account.email}` : ''}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3.5">
                          <span className={`badge ${meta.badge}`}>{meta.label}</span>
                        </td>
                        <td className="px-4 py-3.5">
                          {granted.length === 0 ? (
                            <span className="text-xs text-slate-400 dark:text-slate-500">Không có quyền</span>
                          ) : (
                            <div className="flex max-w-sm flex-wrap gap-1">
                              {granted.map((option) => (
                                <span
                                  key={option.key}
                                  className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                                >
                                  {option.short}
                                </span>
                              ))}
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3.5">
                          <span className="inline-flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
                            <span
                              className={`h-1.5 w-1.5 rounded-full ${
                                account.is_active ? 'bg-emerald-500' : 'bg-slate-400'
                              }`}
                            />
                            {account.is_active ? 'Hoạt động' : 'Đã khoá'}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 text-slate-500 dark:text-slate-400">
                          {formatDate(account.created_at)}
                        </td>
                        <td className="px-4 py-3.5 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              type="button"
                              onClick={() => openEdit(account)}
                              className="rounded-lg p-2 text-slate-500 hover:bg-sky-50 hover:text-sky-600 dark:text-slate-400 dark:hover:bg-sky-950/50 dark:hover:text-sky-400"
                              aria-label={`Sửa ${account.username}`}
                            >
                              <Icon name="pencil" className="h-4 w-4" />
                            </button>
                            <button
                              type="button"
                              onClick={() => setDeleteTarget(account)}
                              disabled={isSelf}
                              className="rounded-lg p-2 text-slate-500 hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-40 dark:text-slate-400 dark:hover:bg-red-950/50 dark:hover:text-red-400"
                              aria-label={`Xoá ${account.username}`}
                              title={isSelf ? 'Không thể xoá tài khoản đang đăng nhập' : undefined}
                            >
                              <Icon name="trash" className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500">
        <Icon name="shield" className="h-4 w-4" />
        Quyền hạn có hiệu lực ngay ở lần tải trang tiếp theo; hệ thống luôn giữ ít nhất một chủ sở hữu đang hoạt động.
      </p>

      <Modal
        open={formOpen}
        size="lg"
        title={editing ? 'Sửa tài khoản' : 'Thêm tài khoản'}
        description={
          editing
            ? `Cập nhật thông tin và quyền hạn cho "${editing.username}".`
            : 'Tạo tài khoản mới và chọn các quyền hạn được phép sử dụng.'
        }
        onClose={() => {
          if (!saving) setFormOpen(false)
        }}
        footer={
          <>
            <button type="button" onClick={() => setFormOpen(false)} disabled={saving} className="btn-secondary">
              Huỷ
            </button>
            <button type="submit" form="user-form" disabled={saving} className="btn-primary">
              {saving ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                  Đang lưu…
                </>
              ) : (
                <>
                  <Icon name="check" className="h-4 w-4" />
                  {editing ? 'Lưu thay đổi' : 'Tạo tài khoản'}
                </>
              )}
            </button>
          </>
        }
      >
        <form id="user-form" onSubmit={handleSubmit} className="space-y-4">
          {formError && (
            <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300">
              <Icon name="warning" className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Họ và tên" htmlFor="full_name" required>
              <input
                id="full_name"
                value={form.full_name}
                onChange={(event) => setField('full_name', event.target.value)}
                className="input"
                maxLength={150}
                placeholder="VD: Nguyễn Văn A"
                required
              />
            </Field>

            <Field label="Username" htmlFor="username" required>
              <input
                id="username"
                value={form.username}
                onChange={(event) => setField('username', event.target.value)}
                className="input"
                maxLength={50}
                autoComplete="off"
                placeholder="VD: manager_hcm"
                required
              />
            </Field>

            <Field
              label={editing ? 'Mật khẩu mới' : 'Mật khẩu'}
              htmlFor="password"
              required={!editing}
              hint={editing ? 'Để trống nếu không đổi mật khẩu.' : 'Tối thiểu 6 ký tự.'}
            >
              <input
                id="password"
                type="password"
                value={form.password}
                onChange={(event) => setField('password', event.target.value)}
                className="input"
                maxLength={72}
                autoComplete="new-password"
                placeholder={editing ? '••••••••' : 'Tối thiểu 6 ký tự'}
                required={!editing}
              />
            </Field>

            <Field label="Vai trò" htmlFor="role" required>
              <select
                id="role"
                value={form.role}
                onChange={(event) => applyRoleDefaults(event.target.value)}
                className="input"
              >
                {roleOptions.map((role) => (
                  <option key={role} value={role}>
                    {ROLE_META[role].label}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Email" htmlFor="email" hint="Không bắt buộc.">
              <input
                id="email"
                type="email"
                value={form.email}
                onChange={(event) => setField('email', event.target.value)}
                className="input"
                maxLength={150}
                placeholder="ten@cuahang.vn"
              />
            </Field>

            <div className="flex items-end">
              <div className="w-full">
                <Toggle
                  label="Tài khoản đang hoạt động"
                  hint="Tài khoản bị khoá sẽ không đăng nhập được."
                  checked={Boolean(form.is_active)}
                  onChange={(value) => setField('is_active', value)}
                />
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">Quyền hạn chi tiết</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Bật các quyền mà tài khoản này được phép sử dụng.
                </p>
              </div>
              <div className="flex gap-1">
                <button
                  type="button"
                  onClick={() => PERMISSION_KEYS.forEach((key) => setField(key, true))}
                  className="rounded-lg px-2 py-1 text-xs font-medium text-brand-700 hover:bg-brand-50 dark:text-brand-300 dark:hover:bg-brand-950/50"
                >
                  Chọn tất cả
                </button>
                <button
                  type="button"
                  onClick={() => PERMISSION_KEYS.forEach((key) => setField(key, false))}
                  className="rounded-lg px-2 py-1 text-xs font-medium text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                >
                  Bỏ chọn
                </button>
              </div>
            </div>

            <div className="grid gap-2 sm:grid-cols-2">
              {PERMISSION_OPTIONS.map((option) => (
                <Toggle
                  key={option.key}
                  label={option.label}
                  hint={option.hint}
                  checked={Boolean(form[option.key])}
                  onChange={(value) => setField(option.key, value)}
                />
              ))}
            </div>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Xoá tài khoản"
        message={
          deleteTarget
            ? `Bạn có chắc muốn xoá tài khoản "${deleteTarget.full_name || deleteTarget.username}"? Hành động này không thể hoàn tác.`
            : ''
        }
        busy={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  )
}
