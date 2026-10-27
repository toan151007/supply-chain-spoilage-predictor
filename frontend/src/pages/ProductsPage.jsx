import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import ConfirmDialog from '../components/common/ConfirmDialog.jsx'
import Field from '../components/common/Field.jsx'
import Icon from '../components/common/Icon.jsx'
import Modal from '../components/common/Modal.jsx'
import Spinner from '../components/common/Spinner.jsx'
import Toast from '../components/common/Toast.jsx'
import { useAuth } from '../contexts/AuthContext.jsx'
import api from '../services/api.js'
import { formatCurrency, formatNumber, getErrorMessage } from '../utils/format.js'

const PAGE_SIZE = 10

const EMPTY_FORM = {
  product_code: '',
  product_name: '',
  category_id: '',
  unit: 'cái',
  unit_cost: '0',
  selling_price: '0',
  shelf_life_days: '30',
  min_stock: '0',
  max_stock: '',
  reorder_point: '',
  supplier: '',
  is_perishable: true,
  is_active: true,
}

/** Empty input means "no value"; anything else must parse as a finite number. */
function toNumberOrNull(value) {
  const text = String(value ?? '').trim()
  if (text === '') return null
  const parsed = Number(text)
  return Number.isFinite(parsed) ? parsed : Number.NaN
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
      {active ? 'Đang bán' : 'Ngừng bán'}
    </span>
  )
}

function TableSkeleton() {
  return (
    <>
      {Array.from({ length: 6 }).map((_, index) => (
        <tr key={index} className="animate-pulse">
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

export default function ProductsPage() {
  const navigate = useNavigate()
  const { isAdmin } = useAuth()

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)

  const [data, setData] = useState({ items: [], total: 0, pages: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  /* Category options for the create/edit form. */
  const [categories, setCategories] = useState([])

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const [toast, setToast] = useState(null)

  /* Debounce the search box: one request after the user stops typing
     instead of one per keystroke. */
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 350)
    return () => clearTimeout(timer)
  }, [searchInput])

  useEffect(() => {
    let cancelled = false

    setLoading(true)
    setError('')

    api
      .get('/products', {
        params: {
          page,
          page_size: PAGE_SIZE,
          search: search || undefined,
          is_active: status === '' ? undefined : status === 'active',
        },
      })
      .then((response) => {
        if (!cancelled) setData(response.data)
      })
      .catch((requestError) => {
        if (!cancelled) setError(getErrorMessage(requestError, 'Không tải được danh sách sản phẩm.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [page, search, status, reloadKey])

  /* The category list only changes when an admin edits it, so load it once. */
  useEffect(() => {
    if (!isAdmin) return undefined
    let cancelled = false

    api
      .get('/categories', { params: { page_size: 100 } })
      .then((response) => {
        if (!cancelled) setCategories(response.data.items || [])
      })
      .catch(() => {
        /* The form still works without options; the select shows a hint. */
      })

    return () => {
      cancelled = true
    }
  }, [isAdmin])

  const activeCount = useMemo(
    () => data.items.filter((item) => item.is_active).length,
    [data.items],
  )

  const goToPage = (nextPage) => {
    if (nextPage < 1 || nextPage > data.pages || nextPage === page) return
    setPage(nextPage)
  }

  const setField = (name, value) => {
    setForm((previous) => ({ ...previous, [name]: value }))
  }

  const openCreate = () => {
    setEditing(null)
    setForm({ ...EMPTY_FORM })
    setFormError('')
    setFormOpen(true)
  }

  const openEdit = (product) => {
    setEditing(product)
    setForm({
      product_code: product.product_code ?? '',
      product_name: product.product_name ?? '',
      category_id: String(product.category_id ?? ''),
      unit: product.unit ?? '',
      unit_cost: String(product.unit_cost ?? 0),
      selling_price: String(product.selling_price ?? 0),
      shelf_life_days: String(product.shelf_life_days ?? ''),
      min_stock: String(product.min_stock ?? 0),
      max_stock: product.max_stock == null ? '' : String(product.max_stock),
      reorder_point: product.reorder_point == null ? '' : String(product.reorder_point),
      supplier: product.supplier ?? '',
      is_perishable: Boolean(product.is_perishable),
      is_active: Boolean(product.is_active),
    })
    setFormError('')
    setFormOpen(true)
  }

  const buildPayload = () => {
    const code = form.product_code.trim()
    const name = form.product_name.trim()
    const unit = form.unit.trim()

    if (!code) return { error: 'Vui lòng nhập mã sản phẩm.' }
    if (!name) return { error: 'Vui lòng nhập tên sản phẩm.' }
    if (!form.category_id) return { error: 'Vui lòng chọn nhóm hàng.' }
    if (!unit) return { error: 'Vui lòng nhập đơn vị tính.' }

    const shelfLife = Number(form.shelf_life_days)
    if (!Number.isFinite(shelfLife) || shelfLife <= 0) {
      return { error: 'Hạn dùng phải là số nguyên lớn hơn 0.' }
    }

    const unitCost = toNumberOrNull(form.unit_cost) ?? 0
    const sellingPrice = toNumberOrNull(form.selling_price) ?? 0
    const minStock = toNumberOrNull(form.min_stock) ?? 0
    const maxStock = toNumberOrNull(form.max_stock)
    const reorderPoint = toNumberOrNull(form.reorder_point)

    if (!Number.isFinite(unitCost) || unitCost < 0) return { error: 'Giá vốn không hợp lệ.' }
    if (!Number.isFinite(sellingPrice) || sellingPrice < 0) return { error: 'Giá bán không hợp lệ.' }
    if (!Number.isFinite(minStock) || minStock < 0) return { error: 'Tồn tối thiểu không hợp lệ.' }
    if (maxStock !== null && (!Number.isFinite(maxStock) || maxStock <= 0)) {
      return { error: 'Tồn tối đa phải lớn hơn 0.' }
    }
    if (maxStock !== null && maxStock < minStock) {
      return { error: 'Tồn tối đa phải lớn hơn hoặc bằng tồn tối thiểu.' }
    }
    if (reorderPoint !== null && (!Number.isFinite(reorderPoint) || reorderPoint < 0)) {
      return { error: 'Điểm đặt hàng lại không hợp lệ.' }
    }

    return {
      payload: {
        product_code: code,
        product_name: name,
        category_id: Number(form.category_id),
        unit,
        unit_cost: unitCost,
        selling_price: sellingPrice,
        shelf_life_days: Math.trunc(shelfLife),
        min_stock: minStock,
        max_stock: maxStock,
        is_perishable: form.is_perishable,
        reorder_point: reorderPoint,
        supplier: form.supplier.trim() || null,
        is_active: form.is_active,
      },
    }
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    const { payload, error: validationError } = buildPayload()
    if (validationError) {
      setFormError(validationError)
      return
    }

    setSaving(true)
    setFormError('')

    try {
      if (editing) {
        await api.put(`/products/${editing.product_id}`, payload)
      } else {
        await api.post('/products', payload)
      }

      setFormOpen(false)
      setToast({
        type: 'success',
        message: editing ? 'Đã cập nhật sản phẩm.' : 'Đã thêm sản phẩm mới.',
      })
      setReloadKey((key) => key + 1)
    } catch (requestError) {
      setFormError(getErrorMessage(requestError, 'Không lưu được sản phẩm.'))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return

    setDeleting(true)
    try {
      await api.delete(`/products/${deleteTarget.product_id}`)
      setToast({ type: 'success', message: `Đã xoá sản phẩm "${deleteTarget.product_name}".` })
      setDeleteTarget(null)

      /* An empty last page would otherwise strand the user on nothing. */
      if (data.items.length === 1 && page > 1) {
        setPage((current) => current - 1)
      } else {
        setReloadKey((key) => key + 1)
      }
    } catch (requestError) {
      setToast({
        type: 'error',
        message: getErrorMessage(requestError, 'Không xoá được sản phẩm.'),
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
      {/* Heading */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-2xl">
            Quản lý sản phẩm
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Danh mục sản phẩm dùng chung cho mọi cửa hàng trong chuỗi.
          </p>
        </div>

        {isAdmin && (
          <button type="button" onClick={openCreate} className="btn-primary w-fit">
            <Icon name="plus" className="h-4 w-4" />
            Thêm sản phẩm
          </button>
        )}
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div className="card px-4 py-3">
          <p className="text-xs text-slate-500 dark:text-slate-400">Tổng sản phẩm</p>
          <p className="mt-0.5 text-xl font-bold text-slate-900 dark:text-white">
            {loading ? '—' : formatNumber(data.total)}
          </p>
        </div>
        <div className="card px-4 py-3">
          <p className="text-xs text-slate-500 dark:text-slate-400">Đang bán (trang này)</p>
          <p className="mt-0.5 text-xl font-bold text-emerald-600 dark:text-emerald-400">
            {loading ? '—' : formatNumber(activeCount)}
          </p>
        </div>
        <div className="card col-span-2 px-4 py-3 sm:col-span-1">
          <p className="text-xs text-slate-500 dark:text-slate-400">Trang hiện tại</p>
          <p className="mt-0.5 text-xl font-bold text-slate-900 dark:text-white">
            {loading ? '—' : `${data.pages === 0 ? 0 : page}/${data.pages}`}
          </p>
        </div>
      </div>

      {/* Toolbar */}
      <div className="card p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="relative flex-1">
            <Icon
              name="search"
              className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
            />
            <input
              type="search"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Tìm theo mã hoặc tên sản phẩm…"
              className="input pl-10"
              aria-label="Tìm sản phẩm"
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={status}
              onChange={(event) => {
                setStatus(event.target.value)
                setPage(1)
              }}
              className="input w-auto min-w-[150px]"
              aria-label="Lọc theo trạng thái"
            >
              <option value="">Tất cả trạng thái</option>
              <option value="active">Đang bán</option>
              <option value="inactive">Ngừng bán</option>
            </select>

            <button
              type="button"
              onClick={() => setReloadKey((key) => key + 1)}
              className="btn-secondary px-3"
              title="Tải lại"
              aria-label="Tải lại danh sách"
            >
              <Icon name="refresh" className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      {/* Table */}
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
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[820px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/70 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-400">
                    <th className="px-4 py-3 font-semibold">Sản phẩm</th>
                    <th className="px-4 py-3 font-semibold">Nhóm hàng</th>
                    <th className="px-4 py-3 font-semibold">Đơn vị</th>
                    <th className="px-4 py-3 text-right font-semibold">Giá vốn</th>
                    <th className="px-4 py-3 text-right font-semibold">Giá bán</th>
                    <th className="px-4 py-3 text-right font-semibold">Hạn dùng</th>
                    <th className="px-4 py-3 font-semibold">Trạng thái</th>
                    {isAdmin && <th className="px-4 py-3 text-right font-semibold">Thao tác</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {loading ? (
                    <TableSkeleton />
                  ) : data.items.length === 0 ? (
                    <tr>
                      <td colSpan={isAdmin ? 8 : 7} className="px-6 py-16 text-center">
                        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
                          <Icon name="box" className="h-6 w-6" />
                        </span>
                        <p className="mt-3 font-semibold text-slate-700 dark:text-slate-200">
                          Không tìm thấy sản phẩm
                        </p>
                        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                          Thử thay đổi từ khoá hoặc bộ lọc trạng thái.
                        </p>
                      </td>
                    </tr>
                  ) : (
                    data.items.map((product) => (
                      <tr
                        key={product.product_id}
                        className="transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-800/40"
                      >
                        <td className="px-4 py-3.5">
                          <p className="font-medium text-slate-900 dark:text-white">{product.product_name}</p>
                          <p className="mt-0.5 font-mono text-xs text-slate-400 dark:text-slate-500">
                            {product.product_code}
                          </p>
                        </td>
                        <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">
                          {product.category?.category_name ?? `#${product.category_id}`}
                        </td>
                        <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">{product.unit}</td>
                        <td className="px-4 py-3.5 text-right tabular-nums text-slate-600 dark:text-slate-300">
                          {formatCurrency(product.unit_cost)}
                        </td>
                        <td className="px-4 py-3.5 text-right tabular-nums font-medium text-slate-800 dark:text-slate-100">
                          {formatCurrency(product.selling_price)}
                        </td>
                        <td className="px-4 py-3.5 text-right tabular-nums text-slate-600 dark:text-slate-300">
                          {formatNumber(product.shelf_life_days)} ngày
                        </td>
                        <td className="px-4 py-3.5">
                          <StatusBadge active={product.is_active} />
                        </td>
                        {isAdmin && (
                          <td className="px-4 py-3.5">
                            <div className="flex items-center justify-end gap-1">
                              <button
                                type="button"
                                onClick={() => openEdit(product)}
                                className="rounded-lg p-2 text-slate-500 transition-colors hover:bg-sky-50 hover:text-sky-600 dark:text-slate-400 dark:hover:bg-sky-950/50 dark:hover:text-sky-400"
                                aria-label={`Sửa ${product.product_name}`}
                                title="Sửa sản phẩm"
                              >
                                <Icon name="pencil" className="h-4 w-4" />
                              </button>
                              <button
                                type="button"
                                onClick={() => setDeleteTarget(product)}
                                className="rounded-lg p-2 text-slate-500 transition-colors hover:bg-red-50 hover:text-red-600 dark:text-slate-400 dark:hover:bg-red-950/50 dark:hover:text-red-400"
                                aria-label={`Xoá ${product.product_name}`}
                                title="Xoá sản phẩm"
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

            {/* Pagination */}
            <div className="flex flex-col items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 dark:border-slate-800 sm:flex-row">
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {loading
                  ? 'Đang tải…'
                  : data.total === 0
                    ? '0 sản phẩm'
                    : `Hiển thị ${(page - 1) * PAGE_SIZE + 1}–${Math.min(page * PAGE_SIZE, data.total)} trong ${formatNumber(data.total)} sản phẩm`}
              </p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => goToPage(page - 1)}
                  disabled={loading || page <= 1}
                  className="btn-secondary px-3 py-2"
                  aria-label="Trang trước"
                >
                  <Icon name="chevronLeft" className="h-4 w-4" />
                </button>
                <span className="min-w-[72px] text-center text-sm font-medium text-slate-600 dark:text-slate-300">
                  {loading ? <Spinner label="" /> : `${data.pages === 0 ? 0 : page} / ${data.pages}`}
                </span>
                <button
                  type="button"
                  onClick={() => goToPage(page + 1)}
                  disabled={loading || page >= data.pages}
                  className="btn-secondary px-3 py-2"
                  aria-label="Trang sau"
                >
                  <Icon name="chevronRight" className="h-4 w-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {!isAdmin && (
        <p className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500">
          <Icon name="shield" className="h-4 w-4" />
          Tài khoản nhân viên chỉ được xem danh mục. Nút thêm / sửa / xoá được ẩn theo phân quyền.
        </p>
      )}

      {/* Create / edit form */}
      <Modal
        open={formOpen}
        title={editing ? 'Sửa sản phẩm' : 'Thêm sản phẩm'}
        description={
          editing
            ? `Cập nhật thông tin cho "${editing.product_name}".`
            : 'Điền thông tin sản phẩm mới. Các trường có dấu * là bắt buộc.'
        }
        onClose={() => {
          if (!saving) setFormOpen(false)
        }}
        size="lg"
        footer={
          <>
            <button
              type="button"
              onClick={() => setFormOpen(false)}
              disabled={saving}
              className="btn-secondary"
            >
              Huỷ
            </button>
            <button type="submit" form="product-form" disabled={saving} className="btn-primary">
              {saving ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                  Đang lưu…
                </>
              ) : (
                <>
                  <Icon name="check" className="h-4 w-4" />
                  {editing ? 'Lưu thay đổi' : 'Thêm sản phẩm'}
                </>
              )}
            </button>
          </>
        }
      >
        <form id="product-form" onSubmit={handleSubmit} className="space-y-4">
          {formError && (
            <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300">
              <Icon name="warning" className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Mã sản phẩm" htmlFor="product_code" required>
              <input
                id="product_code"
                value={form.product_code}
                onChange={(event) => setField('product_code', event.target.value)}
                className="input"
                maxLength={50}
                placeholder="VD: SP051"
                required
              />
            </Field>

            <Field label="Nhóm hàng" htmlFor="category_id" required>
              <select
                id="category_id"
                value={form.category_id}
                onChange={(event) => setField('category_id', event.target.value)}
                className="input"
                required
              >
                <option value="">— Chọn nhóm hàng —</option>
                {categories.map((category) => (
                  <option key={category.category_id} value={category.category_id}>
                    {category.category_name}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Tên sản phẩm" htmlFor="product_name" required className="sm:col-span-2">
              <input
                id="product_name"
                value={form.product_name}
                onChange={(event) => setField('product_name', event.target.value)}
                className="input"
                maxLength={255}
                placeholder="VD: Nước suối 330ml"
                required
              />
            </Field>

            <Field label="Đơn vị tính" htmlFor="unit" required>
              <input
                id="unit"
                value={form.unit}
                onChange={(event) => setField('unit', event.target.value)}
                className="input"
                maxLength={20}
                placeholder="chai, hộp, kg…"
                required
              />
            </Field>

            <Field label="Hạn dùng (ngày)" htmlFor="shelf_life_days" required>
              <input
                id="shelf_life_days"
                type="number"
                min="1"
                step="1"
                value={form.shelf_life_days}
                onChange={(event) => setField('shelf_life_days', event.target.value)}
                className="input"
                required
              />
            </Field>

            <Field label="Giá vốn (đ)" htmlFor="unit_cost">
              <input
                id="unit_cost"
                type="number"
                min="0"
                step="1"
                value={form.unit_cost}
                onChange={(event) => setField('unit_cost', event.target.value)}
                className="input"
              />
            </Field>

            <Field label="Giá bán (đ)" htmlFor="selling_price">
              <input
                id="selling_price"
                type="number"
                min="0"
                step="1"
                value={form.selling_price}
                onChange={(event) => setField('selling_price', event.target.value)}
                className="input"
              />
            </Field>

            <Field label="Tồn tối thiểu" htmlFor="min_stock">
              <input
                id="min_stock"
                type="number"
                min="0"
                step="1"
                value={form.min_stock}
                onChange={(event) => setField('min_stock', event.target.value)}
                className="input"
              />
            </Field>

            <Field label="Tồn tối đa" htmlFor="max_stock" hint="Để trống nếu không giới hạn.">
              <input
                id="max_stock"
                type="number"
                min="0"
                step="1"
                value={form.max_stock}
                onChange={(event) => setField('max_stock', event.target.value)}
                className="input"
              />
            </Field>

            <Field label="Điểm đặt hàng lại" htmlFor="reorder_point" hint="Ngưỡng cảnh báo sắp hết hàng.">
              <input
                id="reorder_point"
                type="number"
                min="0"
                step="1"
                value={form.reorder_point}
                onChange={(event) => setField('reorder_point', event.target.value)}
                className="input"
              />
            </Field>

            <Field label="Nhà cung cấp" htmlFor="supplier">
              <input
                id="supplier"
                value={form.supplier}
                onChange={(event) => setField('supplier', event.target.value)}
                className="input"
                maxLength={200}
                placeholder="VD: Vinamilk"
              />
            </Field>

            <div className="flex flex-wrap items-center gap-5 sm:col-span-2">
              <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={form.is_perishable}
                  onChange={(event) => setField('is_perishable', event.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500 dark:border-slate-600 dark:bg-slate-800"
                />
                Hàng dễ hỏng
              </label>

              <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(event) => setField('is_active', event.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500 dark:border-slate-600 dark:bg-slate-800"
                />
                Đang bán
              </label>
            </div>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Xoá sản phẩm"
        message={
          deleteTarget
            ? `Bạn có chắc muốn xoá sản phẩm "${deleteTarget.product_name}" (${deleteTarget.product_code})? Hành động này không thể hoàn tác.`
            : ''
        }
        busy={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  )
}
