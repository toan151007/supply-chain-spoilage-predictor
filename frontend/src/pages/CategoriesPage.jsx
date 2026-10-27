import { Fragment, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import ConfirmDialog from '../components/common/ConfirmDialog.jsx'
import Field from '../components/common/Field.jsx'
import Icon from '../components/common/Icon.jsx'
import Modal from '../components/common/Modal.jsx'
import Toast from '../components/common/Toast.jsx'
import { useAuth } from '../contexts/AuthContext.jsx'
import api from '../services/api.js'
import { formatDate, getErrorMessage } from '../utils/format.js'

const EMPTY_FORM = {
  category_name: '',
  description: '',
  parent_category_id: '',
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

export default function CategoriesPage() {
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
      .get('/categories', { params: { page_size: 100 } })
      .then((res) => {
        if (!cancelled) setItems(res.data.items || [])
      })
      .catch((err) => {
        if (!cancelled) setError(getErrorMessage(err, 'Không tải được danh sách nhóm hàng.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [reloadKey])

  const roots = items.filter((c) => !c.parent_category_id)
  const childrenOf = (id) => items.filter((c) => c.parent_category_id === id)

  /* A category cannot be its own parent, so drop it from the options. */
  const parentOptions = useMemo(
    () => items.filter((c) => c.category_id !== editing?.category_id),
    [items, editing],
  )

  const setField = (name, value) => {
    setForm((previous) => ({ ...previous, [name]: value }))
  }

  const openCreate = () => {
    setEditing(null)
    setForm({ ...EMPTY_FORM })
    setFormError('')
    setFormOpen(true)
  }

  const openEdit = (category) => {
    setEditing(category)
    setForm({
      category_name: category.category_name ?? '',
      description: category.description ?? '',
      parent_category_id: category.parent_category_id
        ? String(category.parent_category_id)
        : '',
    })
    setFormError('')
    setFormOpen(true)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    const name = form.category_name.trim()
    if (!name) {
      setFormError('Vui lòng nhập tên nhóm hàng.')
      return
    }

    const payload = {
      category_name: name,
      description: form.description.trim() || null,
      parent_category_id: form.parent_category_id ? Number(form.parent_category_id) : null,
    }

    setSaving(true)
    setFormError('')

    try {
      if (editing) {
        await api.put(`/categories/${editing.category_id}`, payload)
      } else {
        await api.post('/categories', payload)
      }

      setFormOpen(false)
      setToast({
        type: 'success',
        message: editing ? 'Đã cập nhật nhóm hàng.' : 'Đã thêm nhóm hàng mới.',
      })
      setReloadKey((key) => key + 1)
    } catch (requestError) {
      setFormError(getErrorMessage(requestError, 'Không lưu được nhóm hàng.'))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return

    setDeleting(true)
    try {
      await api.delete(`/categories/${deleteTarget.category_id}`)
      setToast({ type: 'success', message: `Đã xoá nhóm hàng "${deleteTarget.category_name}".` })
      setDeleteTarget(null)
      setReloadKey((key) => key + 1)
    } catch (requestError) {
      setToast({
        type: 'error',
        message: getErrorMessage(requestError, 'Không xoá được nhóm hàng.'),
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
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-2xl">Nhóm hàng</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Phân cấp nhóm hàng (cha / con) dùng cho sản phẩm.</p>
        </div>
        <div className="flex items-center gap-2">
          {isAdmin && (
            <button type="button" onClick={openCreate} className="btn-primary w-fit">
              <Icon name="plus" className="h-4 w-4" />
              Thêm nhóm hàng
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
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/70 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-400">
                  <th className="px-4 py-3 font-semibold">Tên nhóm hàng</th>
                  <th className="px-4 py-3 font-semibold">Mô tả</th>
                  <th className="px-4 py-3 font-semibold">Cấp</th>
                  <th className="px-4 py-3 font-semibold">Ngày tạo</th>
                  {isAdmin && <th className="px-4 py-3 text-right font-semibold">Thao tác</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {loading ? (
                  <TableSkeleton cols={isAdmin ? 5 : 4} />
                ) : roots.length === 0 ? (
                  <tr>
                    <td colSpan={isAdmin ? 5 : 4} className="px-6 py-16 text-center">
                      <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
                        <Icon name="box" className="h-6 w-6" />
                      </span>
                      <p className="mt-3 font-semibold text-slate-700 dark:text-slate-200">Không có nhóm hàng</p>
                    </td>
                  </tr>
                ) : (
                  roots.map((root) => (
                    <Fragment key={root.category_id}>
                      <tr className="bg-slate-50/40 dark:bg-slate-800/30">
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-2">
                            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-300">
                              <Icon name="box" className="h-4 w-4" />
                            </span>
                            <span className="font-semibold text-slate-900 dark:text-white">{root.category_name}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">{root.description || '—'}</td>
                        <td className="px-4 py-3.5"><span className="badge bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">Nhóm cha</span></td>
                        <td className="px-4 py-3.5 text-slate-500 dark:text-slate-400">{formatDate(root.created_at)}</td>
                        {isAdmin && (
                          <td className="px-4 py-3.5 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <button
                                type="button"
                                onClick={() => openEdit(root)}
                                className="rounded-lg p-2 text-slate-500 hover:bg-sky-50 hover:text-sky-600 dark:text-slate-400 dark:hover:bg-sky-950/50 dark:hover:text-sky-400"
                                aria-label={`Sửa ${root.category_name}`}
                                title="Sửa nhóm hàng"
                              >
                                <Icon name="pencil" className="h-4 w-4" />
                              </button>
                              <button
                                type="button"
                                onClick={() => setDeleteTarget(root)}
                                className="rounded-lg p-2 text-slate-500 hover:bg-red-50 hover:text-red-600 dark:text-slate-400 dark:hover:bg-red-950/50 dark:hover:text-red-400"
                                aria-label={`Xoá ${root.category_name}`}
                                title="Xoá nhóm hàng"
                              >
                                <Icon name="trash" className="h-4 w-4" />
                              </button>
                            </div>
                          </td>
                        )}
                      </tr>
                      {childrenOf(root.category_id).map((child) => (
                        <tr key={child.category_id} className="transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-800/40">
                          <td className="px-4 py-3.5 pl-8">
                            <div className="flex items-center gap-2">
                              <span className="text-slate-300 dark:text-slate-600">└</span>
                              <span className="text-slate-700 dark:text-slate-200">{child.category_name}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">{child.description || '—'}</td>
                          <td className="px-4 py-3.5"><span className="badge bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">Nhóm con</span></td>
                          <td className="px-4 py-3.5 text-slate-500 dark:text-slate-400">{formatDate(child.created_at)}</td>
                          {isAdmin && (
                            <td className="px-4 py-3.5 text-right">
                              <div className="flex items-center justify-end gap-1">
                                <button
                                  type="button"
                                  onClick={() => openEdit(child)}
                                  className="rounded-lg p-2 text-slate-500 hover:bg-sky-50 hover:text-sky-600 dark:text-slate-400 dark:hover:bg-sky-950/50 dark:hover:text-sky-400"
                                  aria-label={`Sửa ${child.category_name}`}
                                  title="Sửa nhóm hàng"
                                >
                                  <Icon name="pencil" className="h-4 w-4" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setDeleteTarget(child)}
                                  className="rounded-lg p-2 text-slate-500 hover:bg-red-50 hover:text-red-600 dark:text-slate-400 dark:hover:bg-red-950/50 dark:hover:text-red-400"
                                  aria-label={`Xoá ${child.category_name}`}
                                  title="Xoá nhóm hàng"
                                >
                                  <Icon name="trash" className="h-4 w-4" />
                                </button>
                              </div>
                            </td>
                          )}
                        </tr>
                      ))}
                    </Fragment>
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
          Chỉ owner/manager mới có quyền thêm/sửa/xoá nhóm hàng.
        </p>
      )}

      <Modal
        open={formOpen}
        title={editing ? 'Sửa nhóm hàng' : 'Thêm nhóm hàng'}
        description={
          editing
            ? `Cập nhật thông tin cho "${editing.category_name}".`
            : 'Tạo nhóm hàng mới. Để trống "Nhóm cha" nếu đây là nhóm gốc.'
        }
        onClose={() => {
          if (!saving) setFormOpen(false)
        }}
        footer={
          <>
            <button type="button" onClick={() => setFormOpen(false)} disabled={saving} className="btn-secondary">
              Huỷ
            </button>
            <button type="submit" form="category-form" disabled={saving} className="btn-primary">
              {saving ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                  Đang lưu…
                </>
              ) : (
                <>
                  <Icon name="check" className="h-4 w-4" />
                  {editing ? 'Lưu thay đổi' : 'Thêm nhóm hàng'}
                </>
              )}
            </button>
          </>
        }
      >
        <form id="category-form" onSubmit={handleSubmit} className="space-y-4">
          {formError && (
            <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300">
              <Icon name="warning" className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <Field label="Tên nhóm hàng" htmlFor="category_name" required>
            <input
              id="category_name"
              value={form.category_name}
              onChange={(event) => setField('category_name', event.target.value)}
              className="input"
              maxLength={150}
              placeholder="VD: Đồ uống"
              required
            />
          </Field>

          <Field label="Nhóm cha" htmlFor="parent_category_id" hint="Bỏ trống để tạo nhóm gốc.">
            <select
              id="parent_category_id"
              value={form.parent_category_id}
              onChange={(event) => setField('parent_category_id', event.target.value)}
              className="input"
            >
              <option value="">— Không có (nhóm gốc) —</option>
              {parentOptions.map((category) => (
                <option key={category.category_id} value={category.category_id}>
                  {category.category_name}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Mô tả" htmlFor="description">
            <textarea
              id="description"
              value={form.description}
              onChange={(event) => setField('description', event.target.value)}
              className="input min-h-[88px] resize-y"
              placeholder="Mô tả ngắn về nhóm hàng…"
            />
          </Field>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Xoá nhóm hàng"
        message={
          deleteTarget
            ? `Bạn có chắc muốn xoá nhóm hàng "${deleteTarget.category_name}"? Các nhóm con sẽ trở thành nhóm gốc. Hành động này không thể hoàn tác.`
            : ''
        }
        busy={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  )
}
