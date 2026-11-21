import { useEffect, useMemo, useState } from 'react'
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
import { formatDateTime, getErrorMessage } from '../utils/format.js'

/*
 * The page is split into two jobs that used to share one table:
 *
 *   1. "Danh sách tài khoản"  - who exists, when it was created, is it locked.
 *      Actions here only touch the profile (name, email) and the active flag.
 *   2. "Cấp phép & Phân quyền" - the seven switches, on their own screen, so a
 *      save cannot silently rewrite a username or reset a password.
 *
 * Keeping the two apart also matches the API: PUT /users/{id} for the profile,
 * PUT /users/{id}/permissions for the switches, PUT /users/{id}/status for the
 * lock.
 */

const TABS = [
  { id: 'list', label: 'Danh sách tài khoản', icon: 'users' },
  { id: 'permissions', label: 'Cấp phép & Phân quyền', icon: 'shield' },
]

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

const PERMISSION_KEYS = PERMISSION_OPTIONS.map((option) => option.key)

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

function permissionSnapshot(account) {
  return PERMISSION_KEYS.reduce((flags, key) => {
    flags[key] = Boolean(account?.[key])
    return flags
  }, {})
}

const EMPTY_CREATE = {
  full_name: '',
  username: '',
  password: '',
  email: '',
  role: 'manager',
  is_active: true,
  avatar_url: '',
  ...ROLE_DEFAULTS.manager,
}

/* Pragmatic email shape check: the API is the authority, this only stops a
   typo from becoming an account nobody can log into. */
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function TableSkeleton() {
  return (
    <>
      {Array.from({ length: 4 }).map((_, idx) => (
        <tr key={idx} className="animate-pulse">
          {Array.from({ length: 7 }).map((__, cell) => (
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
  const currentUserId = currentUser?.user_id

  const [tab, setTab] = useState('list')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [items, setItems] = useState([])
  const [reloadKey, setReloadKey] = useState(0)

  /* Create dialog */
  const [createOpen, setCreateOpen] = useState(false)
  const [createForm, setCreateForm] = useState(EMPTY_CREATE)
  const [createError, setCreateError] = useState('')
  const [creating, setCreating] = useState(false)

  /* Basic-info dialog */
  const [editTarget, setEditTarget] = useState(null)
  const [editForm, setEditForm] = useState({ full_name: '', email: '' })
  const [editError, setEditError] = useState('')
  const [savingEdit, setSavingEdit] = useState(false)

  /* Lock / unlock */
  const [statusTarget, setStatusTarget] = useState(null)
  const [statusBusy, setStatusBusy] = useState(false)

  /* Delete */
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  /* Permissions tab */
  const [selectedId, setSelectedId] = useState(null)
  const [draft, setDraft] = useState(null)
  const [draftError, setDraftError] = useState('')
  const [savingDraft, setSavingDraft] = useState(false)

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

  const selected = useMemo(
    () => items.find((account) => account.user_id === selectedId) ?? null,
    [items, selectedId],
  )

  /* Reload the draft whenever the list is refreshed or another row is picked,
     so the switches always start from what the database actually holds. */
  useEffect(() => {
    if (!selected) {
      setDraft(null)
      return
    }
    setDraft({ role: selected.role, ...permissionSnapshot(selected) })
    setDraftError('')
  }, [selected, reloadKey])

  const reload = () => setReloadKey((key) => key + 1)

  const isSelf = (account) => Boolean(account) && account.user_id === currentUserId
  const editingSelf = isSelf(selected)

  const draftDirty = useMemo(() => {
    if (!selected || !draft) return false
    if (draft.role !== selected.role) return true
    return PERMISSION_KEYS.some((key) => Boolean(draft[key]) !== Boolean(selected[key]))
  }, [selected, draft])

  const draftGrantedCount = draft
    ? PERMISSION_KEYS.filter((key) => Boolean(draft[key])).length
    : 0

  const openCreate = () => {
    setCreateForm({ ...EMPTY_CREATE })
    setCreateError('')
    setCreateOpen(true)
  }

  const setCreateField = (name, value) => {
    setCreateForm((previous) => ({ ...previous, [name]: value }))
  }

  const applyCreateRoleDefaults = (role) => {
    setCreateForm((previous) => ({ ...previous, role, ...ROLE_DEFAULTS[role] }))
  }

  const handleCreate = async (event) => {
    event.preventDefault()

    const fullName = createForm.full_name.trim()
    const username = createForm.username.trim()
    const email = createForm.email.trim()
    const password = createForm.password

    if (!fullName) {
      setCreateError('Vui lòng nhập họ tên.')
      return
    }
    if (!username) {
      setCreateError('Vui lòng nhập tên đăng nhập.')
      return
    }
    if (!email) {
      setCreateError('Vui lòng nhập email để hệ thống gửi thông tin đăng nhập.')
      return
    }
    if (!EMAIL_PATTERN.test(email)) {
      setCreateError('Email chưa đúng định dạng, ví dụ: ten@cuahang.vn')
      return
    }
    if (password.length < 6) {
      setCreateError('Mật khẩu phải có ít nhất 6 ký tự.')
      return
    }

    setCreating(true)
    setCreateError('')

    try {
      const response = await api.post('/users', {
        full_name: fullName,
        username,
        email,
        password,
        role: createForm.role,
        is_active: true,
        avatar_url: createForm.avatar_url || null,
        ...permissionSnapshot(createForm),
      })
      const created = response.data || {}

      setCreateOpen(false)
      /* The account is created even when SMTP is down, so report the two
         outcomes separately instead of a single happy-path toast. */
      setToast({
        type: created.email_sent ? 'success' : 'warning',
        message:
          created.email_message ||
          (created.email_sent
            ? `Đã tạo tài khoản và gửi thông tin về email ${email}.`
            : 'Đã tạo tài khoản nhưng chưa gửi được mail.'),
        duration: created.email_sent ? 4500 : 7000,
      })
      reload()
    } catch (requestError) {
      setCreateError(getErrorMessage(requestError, 'Không tạo được tài khoản.'))
    } finally {
      setCreating(false)
    }
  }

  const openEdit = (account) => {
    setEditTarget(account)
    setEditForm({ full_name: account.full_name ?? '', email: account.email ?? '' })
    setEditError('')
  }

  /* Basic info only: name and email. Username stays as the login key, and the
     role belongs to the permissions tab, not to this dialog. */
  const handleEdit = async (event) => {
    event.preventDefault()
    if (!editTarget) return

    const fullName = editForm.full_name.trim()
    const email = editForm.email.trim()

    if (!fullName) {
      setEditError('Vui lòng nhập họ tên.')
      return
    }
    if (email && !EMAIL_PATTERN.test(email)) {
      setEditError('Email chưa đúng định dạng, ví dụ: ten@cuahang.vn')
      return
    }

    setSavingEdit(true)
    setEditError('')

    try {
      await api.put(`/users/${editTarget.user_id}`, {
        full_name: fullName,
        email: email || null,
      })
      setEditTarget(null)
      setToast({ type: 'success', message: 'Đã cập nhật thông tin tài khoản.' })
      reload()
    } catch (requestError) {
      setEditError(getErrorMessage(requestError, 'Không lưu được tài khoản.'))
    } finally {
      setSavingEdit(false)
    }
  }

  const handleToggleStatus = async () => {
    if (!statusTarget) return

    setStatusBusy(true)
    try {
      await api.put(`/users/${statusTarget.account.user_id}/status`, {
        is_active: statusTarget.nextActive,
      })
      setToast({
        type: 'success',
        message: statusTarget.nextActive
          ? `Đã mở khoá tài khoản "${statusTarget.account.username}".`
          : `Đã khoá tài khoản "${statusTarget.account.username}".`,
      })
      setStatusTarget(null)
      reload()
    } catch (requestError) {
      setStatusTarget(null)
      setToast({
        type: 'error',
        message: getErrorMessage(requestError, 'Không đổi được trạng thái tài khoản.'),
      })
    } finally {
      setStatusBusy(false)
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
      setEditTarget(null)
      if (selectedId === deleteTarget.user_id) setSelectedId(null)
      reload()
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

  const setDraftField = (name, value) => {
    setDraft((previous) => ({ ...previous, [name]: value }))
  }

  const setAllDraftFlags = (value) => {
    setDraft((previous) =>
      PERMISSION_KEYS.reduce(
        (next, key) => {
          next[key] = value
          return next
        },
        { ...previous },
      ),
    )
  }

  const applyDraftRoleDefaults = () => {
    if (!draft) return
    setDraft((previous) => ({ ...previous, ...ROLE_DEFAULTS[previous.role] }))
  }

  const handleSavePermissions = async () => {
    if (!selected || !draft || editingSelf) return

    setSavingDraft(true)
    setDraftError('')

    try {
      await api.put(`/users/${selected.user_id}/permissions`, {
        role: draft.role,
        ...permissionSnapshot(draft),
      })
      setToast({
        type: 'success',
        message: `Đã lưu quyền hạn cho "${selected.full_name || selected.username}".`,
      })
      reload()
    } catch (requestError) {
      setDraftError(getErrorMessage(requestError, 'Không lưu được quyền hạn.'))
    } finally {
      setSavingDraft(false)
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

  const roleOptions = ['owner', 'manager', 'staff']
  const lockedInputClass =
    'disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500 dark:disabled:bg-slate-800/60 dark:disabled:text-slate-400'

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
            Tách riêng danh sách tài khoản và phần cấp phép chi tiết.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {tab === 'list' && (
            <button type="button" onClick={openCreate} className="btn-primary w-fit">
              <Icon name="plus" className="h-4 w-4" />
              Thêm tài khoản mới
            </button>
          )}
          <button type="button" onClick={reload} className="btn-secondary w-fit">
            <Icon name="refresh" className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Tải lại
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-1 rounded-xl border border-slate-200 bg-white p-1 dark:border-slate-800 dark:bg-slate-900 sm:w-fit">
        {TABS.map((item) => {
          const active = tab === item.id
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => setTab(item.id)}
              aria-current={active ? 'page' : undefined}
              className={[
                'inline-flex items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition-colors',
                active
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800',
              ].join(' ')}
            >
              <Icon name={item.icon} className="h-4 w-4" />
              {item.label}
              {item.id === 'list' && !loading && (
                <span
                  className={[
                    'rounded-md px-1.5 py-0.5 text-[11px] font-semibold tabular-nums',
                    active
                      ? 'bg-white/20 text-white'
                      : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
                  ].join(' ')}
                >
                  {items.length}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {tab === 'list' ? (
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
              <button type="button" onClick={reload} className="btn-secondary mt-1">
                <Icon name="refresh" className="h-4 w-4" />
                Thử lại
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/70 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-400">
                    <th className="px-4 py-3 font-semibold">Họ tên</th>
                    <th className="px-4 py-3 font-semibold">Username</th>
                    <th className="px-4 py-3 font-semibold">Email</th>
                    <th className="px-4 py-3 font-semibold">Vai trò</th>
                    <th className="px-4 py-3 font-semibold">Ngày giờ tạo</th>
                    <th className="px-4 py-3 font-semibold">Trạng thái</th>
                    <th className="px-4 py-3 text-right font-semibold">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {loading ? (
                    <TableSkeleton />
                  ) : items.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-6 py-16 text-center">
                        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
                          <Icon name="users" className="h-6 w-6" />
                        </span>
                        <p className="mt-3 font-semibold text-slate-700 dark:text-slate-200">
                          Chưa có tài khoản nào
                        </p>
                      </td>
                    </tr>
                  ) : (
                    items.map((account) => {
                      const meta = ROLE_META[account.role] ?? ROLE_META.staff
                      const own = isSelf(account)

                      return (
                        <tr
                          key={account.user_id}
                          className="transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-800/40"
                        >
                          <td className="px-4 py-3.5">
                            <div className="flex items-center gap-3">
                              <Avatar user={account} size="md" />
                              <div className="flex min-w-0 items-center gap-2">
                                <span className="truncate font-semibold text-slate-900 dark:text-white">
                                  {account.full_name}
                                </span>
                                {own && (
                                  <span className="badge bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
                                    Bạn
                                  </span>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">
                            @{account.username}
                          </td>
                          <td className="px-4 py-3.5 text-slate-500 dark:text-slate-400">
                            {account.email || '—'}
                          </td>
                          <td className="px-4 py-3.5">
                            <span className={`badge whitespace-nowrap ${meta.badge}`}>{meta.label}</span>
                          </td>
                          <td className="whitespace-nowrap px-4 py-3.5 tabular-nums text-slate-500 dark:text-slate-400">
                            {formatDateTime(account.created_at)}
                          </td>
                          <td className="px-4 py-3.5">
                            <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-slate-600 dark:text-slate-300">
                              <span
                                className={`h-1.5 w-1.5 rounded-full ${
                                  account.is_active ? 'bg-emerald-500' : 'bg-slate-400'
                                }`}
                              />
                              {account.is_active ? 'Đang hoạt động' : 'Bị khoá'}
                            </span>
                          </td>
                          <td className="px-4 py-3.5 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <button
                                type="button"
                                onClick={() => openEdit(account)}
                                className="rounded-lg p-2 text-slate-500 hover:bg-sky-50 hover:text-sky-600 dark:text-slate-400 dark:hover:bg-sky-950/50 dark:hover:text-sky-400"
                                aria-label={`Sửa thông tin ${account.username}`}
                              >
                                <Icon name="pencil" className="h-4 w-4" />
                              </button>
                              {/* Locking yourself would need another owner to
                                  undo it, so own row has no lock affordance.
                                  The API refuses it as well. */}
                              {!own && (
                                <button
                                  type="button"
                                  onClick={() =>
                                    setStatusTarget({
                                      account,
                                      nextActive: !account.is_active,
                                    })
                                  }
                                  className={[
                                    'rounded-lg p-2',
                                    account.is_active
                                      ? 'text-slate-500 hover:bg-amber-50 hover:text-amber-600 dark:text-slate-400 dark:hover:bg-amber-950/50 dark:hover:text-amber-400'
                                      : 'text-slate-500 hover:bg-emerald-50 hover:text-emerald-600 dark:text-slate-400 dark:hover:bg-emerald-950/50 dark:hover:text-emerald-400',
                                  ].join(' ')}
                                  aria-label={`${
                                    account.is_active ? 'Khoá' : 'Mở khoá'
                                  } tài khoản ${account.username}`}
                                >
                                  <Icon
                                    name={account.is_active ? 'lock' : 'unlock'}
                                    className="h-4 w-4"
                                  />
                                </button>
                              )}
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

          {!error && !loading && items.length > 0 && (
            <div className="border-t border-slate-100 px-4 py-2.5 text-xs text-slate-400 dark:border-slate-800 dark:text-slate-500">
              Quyền hạn chi tiết được cấu hình ở tab “Cấp phép &amp; Phân quyền”.
            </div>
          )}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-[minmax(240px,320px),1fr]">
          <div className="card overflow-hidden">
            <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-800">
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">Chọn tài khoản</p>
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                {loading ? 'Đang tải…' : `${items.length} tài khoản`}
              </p>
            </div>

            <div className="max-h-[560px] divide-y divide-slate-100 overflow-y-auto scrollbar-thin dark:divide-slate-800">
              {loading ? (
                <div className="space-y-3 p-4">
                  {Array.from({ length: 4 }).map((_, idx) => (
                    <div key={idx} className="h-12 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />
                  ))}
                </div>
              ) : items.length === 0 ? (
                <p className="px-4 py-10 text-center text-sm text-slate-500 dark:text-slate-400">
                  Chưa có tài khoản nào.
                </p>
              ) : (
                items.map((account) => {
                  const meta = ROLE_META[account.role] ?? ROLE_META.staff
                  const active = account.user_id === selectedId
                  const granted = PERMISSION_OPTIONS.filter((option) => account[option.key]).length

                  return (
                    <button
                      key={account.user_id}
                      type="button"
                      onClick={() => setSelectedId(account.user_id)}
                      aria-pressed={active}
                      className={[
                        'flex w-full items-center gap-3 px-4 py-3 text-left transition-colors',
                        active
                          ? 'bg-brand-50 dark:bg-brand-950/40'
                          : 'hover:bg-slate-50 dark:hover:bg-slate-800/40',
                      ].join(' ')}
                    >
                      <Avatar user={account} size="md" />
                      <span className="min-w-0 flex-1">
                        <span className="flex items-center gap-2">
                          <span className="truncate text-sm font-semibold text-slate-900 dark:text-white">
                            {account.full_name}
                          </span>
                          {!account.is_active && (
                            <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                              Đã khoá
                            </span>
                          )}
                        </span>
                        <span className="mt-0.5 flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
                          <span className={`badge ${meta.badge} !px-1.5 !py-0`}>{meta.label}</span>
                          <span className="truncate">@{account.username}</span>
                        </span>
                        <span className="mt-1 block text-[11px] text-slate-400 dark:text-slate-500">
                          {granted}/{PERMISSION_OPTIONS.length} quyền được bật
                        </span>
                      </span>
                      <Icon
                        name="chevronRight"
                        className={`h-4 w-4 shrink-0 ${
                          active ? 'text-brand-600 dark:text-brand-300' : 'text-slate-300 dark:text-slate-600'
                        }`}
                      />
                    </button>
                  )
                })
              )}
            </div>
          </div>

          {!selected || !draft ? (
            <div className="card flex flex-col items-center justify-center px-6 py-16 text-center">
              <span className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
                <Icon name="shield" className="h-6 w-6" />
              </span>
              <p className="mt-3 font-semibold text-slate-700 dark:text-slate-200">
                Chọn một tài khoản để phân quyền
              </p>
              <p className="mt-1 max-w-sm text-sm text-slate-500 dark:text-slate-400">
                Các nút gạt quyền hạn sẽ hiện ở đây. Thay đổi chỉ có hiệu lực sau khi bấm
                “Lưu thay đổi quyền”.
              </p>
            </div>
          ) : (
            <div className="card overflow-hidden">
              <div className="flex flex-wrap items-center gap-3 border-b border-slate-200 px-4 py-3.5 dark:border-slate-800">
                <Avatar user={selected} size="lg" />
                <div className="min-w-0 flex-1">
                  <p className="flex items-center gap-2 font-semibold text-slate-900 dark:text-white">
                    <span className="truncate">{selected.full_name}</span>
                    {editingSelf && (
                      <span className="badge bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
                        Bạn
                      </span>
                    )}
                  </p>
                  <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                    @{selected.username}
                    {selected.email ? ` · ${selected.email}` : ''}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-slate-400 dark:text-slate-500">Đang bật</p>
                  <p className="text-sm font-semibold tabular-nums text-slate-700 dark:text-slate-200">
                    {draftGrantedCount}/{PERMISSION_OPTIONS.length}
                  </p>
                </div>
              </div>

              <div className="space-y-4 px-4 py-4">
                {draftError && (
                  <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300">
                    <Icon name="warning" className="mt-0.5 h-4 w-4 shrink-0" />
                    <span>{draftError}</span>
                  </div>
                )}

                {editingSelf && (
                  <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-2.5 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-200">
                    <Icon name="shield" className="mt-0.5 h-4 w-4 shrink-0" />
                    <span>
                      Đây là tài khoản của bạn. Vai trò và quyền hạn được khoá để bạn không tự hạ
                      quyền hoặc tự khoá mình khỏi hệ thống.
                    </span>
                  </div>
                )}

                <div className="flex flex-wrap items-end gap-3">
                  <div className="w-full sm:w-56">
                    <Field
                      label="Vai trò"
                      htmlFor="perm-role"
                      hint={editingSelf ? 'Không thể tự đổi vai trò.' : 'Vai trò là mức nền cho các quyền bên dưới.'}
                    >
                      <select
                        id="perm-role"
                        value={draft.role}
                        onChange={(event) => setDraftField('role', event.target.value)}
                        disabled={editingSelf}
                        className={`input ${lockedInputClass}`}
                      >
                        {roleOptions.map((role) => (
                          <option key={role} value={role}>
                            {ROLE_META[role].label}
                          </option>
                        ))}
                      </select>
                    </Field>
                  </div>

                  <div className="flex flex-wrap gap-1 pb-1">
                    <button
                      type="button"
                      onClick={() => setAllDraftFlags(true)}
                      disabled={editingSelf}
                      className="rounded-lg px-2 py-1 text-xs font-medium text-brand-700 hover:bg-brand-50 disabled:cursor-not-allowed disabled:opacity-40 dark:text-brand-300 dark:hover:bg-brand-950/50"
                    >
                      Chọn tất cả
                    </button>
                    <button
                      type="button"
                      onClick={() => setAllDraftFlags(false)}
                      disabled={editingSelf}
                      className="rounded-lg px-2 py-1 text-xs font-medium text-slate-500 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 dark:text-slate-400 dark:hover:bg-slate-800"
                    >
                      Bỏ chọn
                    </button>
                    <button
                      type="button"
                      onClick={applyDraftRoleDefaults}
                      disabled={editingSelf}
                      className="rounded-lg px-2 py-1 text-xs font-medium text-slate-500 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 dark:text-slate-400 dark:hover:bg-slate-800"
                    >
                      Mặc định theo vai trò
                    </button>
                  </div>
                </div>

                <div className="grid gap-2 sm:grid-cols-2">
                  {PERMISSION_OPTIONS.map((option) => (
                    <Toggle
                      key={option.key}
                      label={option.label}
                      hint={option.hint}
                      checked={Boolean(draft[option.key])}
                      onChange={(value) => setDraftField(option.key, value)}
                      disabled={editingSelf}
                    />
                  ))}
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 bg-slate-50/70 px-4 py-3 dark:border-slate-800 dark:bg-slate-800/40">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {editingSelf
                    ? 'Bạn không thể tự thu hồi quyền hạn của chính mình.'
                    : draftDirty
                      ? 'Có thay đổi chưa lưu.'
                      : 'Chưa có thay đổi nào.'}
                </p>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setDraft({ role: selected.role, ...permissionSnapshot(selected) })}
                    disabled={!draftDirty || savingDraft}
                    className="btn-secondary"
                  >
                    Hoàn tác
                  </button>
                  <button
                    type="button"
                    onClick={handleSavePermissions}
                    disabled={editingSelf || !draftDirty || savingDraft}
                    className="btn-primary"
                  >
                    {savingDraft ? (
                      <>
                        <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                        Đang lưu…
                      </>
                    ) : (
                      <>
                        <Icon name="check" className="h-4 w-4" />
                        Lưu thay đổi quyền
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <p className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500">
        <Icon name="shield" className="h-4 w-4" />
        Quyền hạn có hiệu lực ngay ở lần tải trang tiếp theo; hệ thống luôn giữ ít nhất một chủ sở
        hữu đang hoạt động.
      </p>

      {/* Create: needs a username, a password and a role, so it stays here
          rather than in the basic-info dialog. */}
      <Modal
        open={createOpen}
        size="lg"
        title="Thêm tài khoản"
        description="Tạo tài khoản mới; quyền hạn chi tiết có thể chỉnh ở tab Cấp phép & Phân quyền."
        onClose={() => {
          if (!creating) setCreateOpen(false)
        }}
        footer={
          <>
            <button
              type="button"
              onClick={() => setCreateOpen(false)}
              disabled={creating}
              className="btn-secondary"
            >
              Huỷ
            </button>
            <button type="submit" form="user-create-form" disabled={creating} className="btn-primary">
              {creating ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                  Đang lưu…
                </>
              ) : (
                <>
                  <Icon name="check" className="h-4 w-4" />
                  Tạo tài khoản
                </>
              )}
            </button>
          </>
        }
      >
        <form id="user-create-form" onSubmit={handleCreate} className="space-y-4" noValidate>
          {createError && (
            <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300">
              <Icon name="warning" className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{createError}</span>
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Họ và tên" htmlFor="create_full_name" required>
              <input
                id="create_full_name"
                value={createForm.full_name}
                onChange={(event) => setCreateField('full_name', event.target.value)}
                className="input"
                maxLength={150}
                placeholder="VD: Nguyễn Văn A"
                required
              />
            </Field>

            <Field label="Username" htmlFor="create_username" required>
              <input
                id="create_username"
                value={createForm.username}
                onChange={(event) => setCreateField('username', event.target.value)}
                className="input"
                maxLength={50}
                autoComplete="off"
                placeholder="VD: manager_hcm"
                required
              />
            </Field>

            <Field label="Mật khẩu" htmlFor="create_password" required hint="Tối thiểu 6 ký tự.">
              <input
                id="create_password"
                type="password"
                value={createForm.password}
                onChange={(event) => setCreateField('password', event.target.value)}
                className="input"
                maxLength={72}
                autoComplete="new-password"
                placeholder="Tối thiểu 6 ký tự"
                required
              />
            </Field>

            <Field
              label="Email"
              htmlFor="create_email"
              required
              hint="Tên đăng nhập và mật khẩu sẽ được gửi tới email này."
            >
              <input
                id="create_email"
                type="email"
                value={createForm.email}
                onChange={(event) => setCreateField('email', event.target.value)}
                className="input"
                maxLength={150}
                placeholder="ten@cuahang.vn"
                autoComplete="off"
                required
              />
            </Field>

            <Field
              label="Vai trò"
              htmlFor="create_role"
              required
              hint="Đổi vai trò sẽ đặt lại các quyền bên dưới theo mức mặc định."
            >
              <select
                id="create_role"
                value={createForm.role}
                onChange={(event) => applyCreateRoleDefaults(event.target.value)}
                className="input"
              >
                {roleOptions.map((role) => (
                  <option key={role} value={role}>
                    {ROLE_META[role].label}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <p className="flex items-start gap-2 rounded-xl bg-slate-50 px-3.5 py-2.5 text-xs text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">
            <Icon name="info" className="mt-0.5 h-4 w-4 shrink-0" />
            Tài khoản được tạo với {PERMISSION_KEYS.filter((key) => createForm[key]).length} quyền
            hạn mặc định của vai trò {ROLE_META[createForm.role].label.toLowerCase()}.
          </p>
        </form>
      </Modal>

      {/* Basic info: name and email only. Role and flags live in the other tab. */}
      <Modal
        open={Boolean(editTarget)}
        title="Sửa thông tin cơ bản"
        description={
          editTarget ? `Cập nhật họ tên và email của "${editTarget.username}".` : undefined
        }
        onClose={() => {
          if (!savingEdit) setEditTarget(null)
        }}
        footer={
          <>
            {/* Delete stays reachable but out of the list, so the table only
                offers the three actions the tab is meant to have. */}
            {editTarget && !isSelf(editTarget) && (
              <button
                type="button"
                onClick={() => setDeleteTarget(editTarget)}
                disabled={savingEdit}
                className="btn mr-auto inline-flex bg-red-50 text-red-700 hover:bg-red-100 dark:bg-red-950/40 dark:text-red-300 dark:hover:bg-red-950/70"
              >
                <Icon name="trash" className="h-4 w-4" />
                Xoá tài khoản
              </button>
            )}
            <button
              type="button"
              onClick={() => setEditTarget(null)}
              disabled={savingEdit}
              className="btn-secondary"
            >
              Huỷ
            </button>
            <button type="submit" form="user-edit-form" disabled={savingEdit} className="btn-primary">
              {savingEdit ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                  Đang lưu…
                </>
              ) : (
                <>
                  <Icon name="check" className="h-4 w-4" />
                  Lưu thay đổi
                </>
              )}
            </button>
          </>
        }
      >
        <form id="user-edit-form" onSubmit={handleEdit} className="space-y-4" noValidate>
          {editError && (
            <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300">
              <Icon name="warning" className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{editError}</span>
            </div>
          )}

          <div className="grid gap-4">
            <Field label="Họ và tên" htmlFor="edit_full_name" required>
              <input
                id="edit_full_name"
                value={editForm.full_name}
                onChange={(event) => setEditForm((prev) => ({ ...prev, full_name: event.target.value }))}
                className="input"
                maxLength={150}
                required
              />
            </Field>

            <Field label="Email" htmlFor="edit_email" hint="Dùng để liên hệ và gửi lại thông tin khi cần.">
              <input
                id="edit_email"
                type="email"
                value={editForm.email}
                onChange={(event) => setEditForm((prev) => ({ ...prev, email: event.target.value }))}
                className="input"
                maxLength={150}
                placeholder="ten@cuahang.vn"
                autoComplete="off"
              />
            </Field>
          </div>

          <p className="flex items-start gap-2 rounded-xl bg-slate-50 px-3.5 py-2.5 text-xs text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">
            <Icon name="info" className="mt-0.5 h-4 w-4 shrink-0" />
            Username là khoá đăng nhập nên không sửa ở đây. Vai trò và quyền hạn nằm ở tab
            “Cấp phép &amp; Phân quyền”.
          </p>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(statusTarget)}
        title={statusTarget?.nextActive ? 'Mở khoá tài khoản' : 'Khoá tài khoản'}
        message={
          statusTarget
            ? statusTarget.nextActive
              ? `Mở khoá "${statusTarget.account.full_name || statusTarget.account.username}"? Tài khoản sẽ đăng nhập được trở lại với nguyên quyền hạn cũ.`
              : `Khoá "${statusTarget.account.full_name || statusTarget.account.username}"? Tài khoản sẽ không đăng nhập được cho tới khi được mở khoá lại.`
            : ''
        }
        confirmLabel={statusTarget?.nextActive ? 'Mở khoá' : 'Khoá tài khoản'}
        busyLabel={statusTarget?.nextActive ? 'Đang mở khoá…' : 'Đang khoá…'}
        tone={statusTarget?.nextActive ? 'brand' : 'warning'}
        icon={statusTarget?.nextActive ? 'unlock' : 'lock'}
        busy={statusBusy}
        onCancel={() => setStatusTarget(null)}
        onConfirm={handleToggleStatus}
      />

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
