import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import ConfirmDialog from '../components/common/ConfirmDialog.jsx'
import Field from '../components/common/Field.jsx'
import Icon from '../components/common/Icon.jsx'
import Modal from '../components/common/Modal.jsx'
import Toast from '../components/common/Toast.jsx'
import { useAuth } from '../contexts/AuthContext.jsx'
import api from '../services/api.js'
import { formatDate, getErrorMessage } from '../utils/format.js'

const TYPE_MAP = {
  convenience_store: 'Cửa hàng tiện lợi',
  restaurant: 'Nhà hàng',
  warehouse: 'Kho',
}

const EMPTY_FORM = {
  store_code: '',
  store_name: '',
  store_type: 'convenience_store',
  address: '',
  phone: '',
  opening_date: '',
  is_active: true,
}

function TableSkeleton({ cols }) {
  return (
    <>
      {Array.from({ length: 6 }).map((_, idx) => (
        <tr key={idx} className="animate-pulse">
          {Array.from({ length: cols }).map((__, c) => (
            <td key={c} className="px-4 py-4">
              <div className="h-3 rounded bg-slate-100 dark:bg-slate-800" />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}

function StatusBadge({ active }) {
  return (
    <span
      className={[
        'badge',
        active
          ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
          : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
      ].join(' ')}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${active ? 'bg-emerald-500' : 'bg-slate-400'}`} />
      {active ? 'Hoạt động' : 'Ngừng hoạt động'}
    </span>
  )
}

/** The API expects a plain `YYYY-MM-DD` date, not an ISO timestamp. */
function toDateOnly(value) {
  const text = String(value ?? '').trim()
  return text === '' ? null : text
}

export default function StoresPage() {
  const navigate = useNavigate()
  const { isAdmin } = useAuth()
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
      .get('/stores', { params: { page_size: 100 } })
      .then((res) => {
        if (!cancelled) setItems(res.data.items || [])
      })
      .catch((err) => {
        if (!cancelled) setError(getErrorMessage(err, 'Không tải được danh sách cửa hàng.'))
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

  const openCreate = () => {
    setEditing(null)
    setForm({ ...EMPTY_FORM })
    setFormError('')
    setFormOpen(true)
  }

  const openEdit = (store) => {
    setEditing(store)
    setForm({
      store_code: store.store_code ?? '',
      store_name: store.store_name ?? '',
      store_type: store.store_type ?? 'convenience_store',
      address: store.address ?? '',
      phone: store.phone ?? '',
      opening_date: store.opening_date ? String(store.opening_date).slice(0, 10) : '',
      is_active: Boolean(store.is_active),
    })
    setFormError('')
    setFormOpen(true)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    const code = form.store_code.trim()
    const name = form.store_name.trim()
    const phone = form.phone.trim()

    if (!code) {
      setFormError('Vui lòng nhập mã cửa hàng.')
      return
    }
    if (!name) {
      setFormError('Vui lòng nhập tên cửa hàng.')
      return
    }

    const payload = {
      store_code: code,
      store_name: name,
      store_type: form.store_type,
      address: form.address.trim() || null,
      phone: phone || null,
      opening_date: toDateOnly(form.opening_date),
      is_active: form.is_active,
    }

    setSaving(true)
    setFormError('')

    try {
      if (editing) {
        await api.put(`/stores/${editing.store_id}`, payload)
      } else {
        await api.post('/stores', payload)
      }

      setFormOpen(false)
      setToast({
        type: 'success',
        message: editing ? 'Đã cập nhật cửa hàng.' : 'Đã thêm cửa hàng mới.',
      })
      setReloadKey((key) => key + 1)
    } catch (requestError) {
      setFormError(getErrorMessage(requestError, 'Không lưu được cửa hàng.'))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return

    setDeleting(true)
    try {
      await api.delete(`/stores/${deleteTarget.store_id}`)
      setToast({ type: 'success', message: `Đã xoá cửa hàng "${deleteTarget.store_name}".` })
      setDeleteTarget(null)
      setReloadKey((key) => key + 1)
    } catch (requestError) {
      setToast({
        type: 'error',
        message: getErrorMessage(requestError, 'Không xoá được cửa hàng.'),
      })
      setDeleteTarget(null)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="space-y-5 animate-fade-in">
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
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-2xl">Cửa hàng</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Danh sách cửa hàng, nhà hàng và kho trong chuỗi.</p>
        </div>
        <div className="flex items-center gap-2">
          {isAdmin && (
            <button type="button" onClick={openCreate} className="btn-primary w-fit">
              <Icon name="plus" className="h-4 w-4" />
              Thêm cửa hàng
            </button>
          )}
          <button type="button" onClick={() => setReloadKey((k) => k + 1)} className="btn-secondary w-fit">
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
            <button type="button" onClick={() => setReloadKey((k) => k + 1)} className="btn-secondary mt-1">
              <Icon name="refresh" className="h-4 w-4" />
              Thử lại
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[880px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/70 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-400">
                  <th className="px-4 py-3 font-semibold">Cửa hàng</th>
                  <th className="px-4 py-3 font-semibold">Mã</th>
                  <th className="px-4 py-3 font-semibold">Loại</th>
                  <th className="px-4 py-3 font-semibold">Địa chỉ</th>
                  <th className="px-4 py-3 font-semibold">Điện thoại</th>
                  <th className="px-4 py-3 font-semibold">Ngày mở</th>
                  <th className="px-4 py-3 font-semibold">Trạng thái</th>
                  {isAdmin && <th className="px-4 py-3 text-right font-semibold">Thao tác</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {loading ? (
                  <TableSkeleton cols={isAdmin ? 8 : 7} />
                ) : items.length === 0 ? (
                  <tr>
                    <td colSpan={isAdmin ? 8 : 7} className="px-6 py-16 text-center">
                      <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
                        <Icon name="dashboard" className="h-6 w-6" />
                      </span>
                      <p className="mt-3 font-semibold text-slate-700 dark:text-slate-200">Không có cửa hàng</p>
                    </td>
                  </tr>
                ) : (
                  items.map((store) => (
                    <tr key={store.store_id} className="transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-800/40">
                      <td className="px-4 py-3.5 font-medium text-slate-900 dark:text-white">{store.store_name}</td>
                      <td className="px-4 py-3.5 font-mono text-xs text-slate-500 dark:text-slate-400">{store.store_code}</td>
                      <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">{TYPE_MAP[store.store_type] || store.store_type}</td>
                      <td className="px-4 py-3.5 max-w-xs truncate text-slate-600 dark:text-slate-300">{store.address || '—'}</td>
                      <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">{store.phone || '—'}</td>
                      <td className="px-4 py-3.5 text-slate-500 dark:text-slate-400">{formatDate(store.opening_date)}</td>
                      <td className="px-4 py-3.5"><StatusBadge active={store.is_active} /></td>
                      {isAdmin && (
                        <td className="px-4 py-3.5 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              type="button"
                              onClick={() => openEdit(store)}
                              className="rounded-lg p-2 text-slate-500 hover:bg-sky-50 hover:text-sky-600 dark:text-slate-400 dark:hover:bg-sky-950/50 dark:hover:text-sky-400"
                              aria-label={`Sửa ${store.store_name}`}
                              title="Sửa cửa hàng"
                            >
                              <Icon name="pencil" className="h-4 w-4" />
                            </button>
                            <button
                              type="button"
                              onClick={() => setDeleteTarget(store)}
                              className="rounded-lg p-2 text-slate-500 hover:bg-red-50 hover:text-red-600 dark:text-slate-400 dark:hover:bg-red-950/50 dark:hover:text-red-400"
                              aria-label={`Xoá ${store.store_name}`}
                              title="Xoá cửa hàng"
                            >
                              <Icon name="trash" className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {!isAdmin && (
        <p className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500">
          <Icon name="shield" className="h-4 w-4" />
          Chỉ owner/manager mới có quyền thêm/sửa/xoá cửa hàng.
        </p>
      )}

      <Modal
        open={formOpen}
        title={editing ? 'Sửa cửa hàng' : 'Thêm cửa hàng'}
        description={
          editing
            ? `Cập nhật thông tin cho "${editing.store_name}".`
            : 'Điền thông tin cửa hàng mới. Các trường có dấu * là bắt buộc.'
        }
        onClose={() => {
          if (!saving) setFormOpen(false)
        }}
        size="lg"
        footer={
          <>
            <button type="button" onClick={() => setFormOpen(false)} disabled={saving} className="btn-secondary">
              Huỷ
            </button>
            <button type="submit" form="store-form" disabled={saving} className="btn-primary">
              {saving ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                  Đang lưu…
                </>
              ) : (
                <>
                  <Icon name="check" className="h-4 w-4" />
                  {editing ? 'Lưu thay đổi' : 'Thêm cửa hàng'}
                </>
              )}
            </button>
          </>
        }
      >
        <form id="store-form" onSubmit={handleSubmit} className="space-y-4">
          {formError && (
            <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300">
              <Icon name="warning" className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Mã cửa hàng" htmlFor="store_code" required>
              <input
                id="store_code"
                value={form.store_code}
                onChange={(event) => setField('store_code', event.target.value)}
                className="input"
                maxLength={20}
                placeholder="VD: CH011"
                required
              />
            </Field>

            <Field label="Loại hình" htmlFor="store_type" required>
              <select
                id="store_type"
                value={form.store_type}
                onChange={(event) => setField('store_type', event.target.value)}
                className="input"
                required
              >
                <option value="convenience_store">Cửa hàng tiện lợi</option>
                <option value="restaurant">Nhà hàng</option>
                <option value="warehouse">Kho</option>
              </select>
            </Field>

            <Field label="Tên cửa hàng" htmlFor="store_name" required className="sm:col-span-2">
              <input
                id="store_name"
                value={form.store_name}
                onChange={(event) => setField('store_name', event.target.value)}
                className="input"
                maxLength={200}
                placeholder="VD: Cửa hàng tiện lợi Q.5"
                required
              />
            </Field>

            <Field label="Địa chỉ" htmlFor="address" className="sm:col-span-2">
              <input
                id="address"
                value={form.address}
                onChange={(event) => setField('address', event.target.value)}
                className="input"
                placeholder="Số nhà, đường, quận…"
              />
            </Field>

            <Field label="Điện thoại" htmlFor="phone">
              <input
                id="phone"
                value={form.phone}
                onChange={(event) => setField('phone', event.target.value)}
                className="input"
                maxLength={20}
                placeholder="0901234567"
              />
            </Field>

            <Field label="Ngày mở" htmlFor="opening_date">
              <input
                id="opening_date"
                type="date"
                value={form.opening_date}
                onChange={(event) => setField('opening_date', event.target.value)}
                className="input"
              />
            </Field>

            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300 sm:col-span-2">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(event) => setField('is_active', event.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500 dark:border-slate-600 dark:bg-slate-800"
              />
              Đang hoạt động
            </label>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Xoá cửa hàng"
        message={
          deleteTarget
            ? `Bạn có chắc muốn xoá cửa hàng "${deleteTarget.store_name}" (${deleteTarget.store_code})? Hành động này không thể hoàn tác.`
            : ''
        }
        busy={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  )
}
