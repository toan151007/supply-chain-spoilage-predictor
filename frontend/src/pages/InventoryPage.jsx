import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import ConfirmDialog from '../components/common/ConfirmDialog.jsx'
import Field from '../components/common/Field.jsx'
import Icon from '../components/common/Icon.jsx'
import Modal from '../components/common/Modal.jsx'
import Toast from '../components/common/Toast.jsx'
import { useAuth } from '../contexts/AuthContext.jsx'
import api from '../services/api.js'
import { formatDate, formatNumber, getErrorMessage } from '../utils/format.js'

const PAGE_SIZE = 20

const EMPTY_FORM = {
  store_id: '',
  product_id: '',
  quantity: '0',
  received_date: '',
  expiry_date: '',
  batch_code: '',
}

function daysBadge(daysLeft) {
  if (daysLeft == null) return { text: 'Không rõ', cls: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300' }
  if (daysLeft <= 0) return { text: `Hết hạn ${Math.abs(daysLeft)} ngày`, cls: 'bg-red-50 text-red-700 dark:bg-red-900/40 dark:text-red-300' }
  if (daysLeft <= 3) return { text: `Còn ${daysLeft} ngày`, cls: 'bg-red-50 text-red-700 dark:bg-red-900/40 dark:text-red-300' }
  if (daysLeft <= 7) return { text: `Còn ${daysLeft} ngày`, cls: 'bg-amber-50 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' }
  return { text: `Còn ${daysLeft} ngày`, cls: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' }
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

/** The API expects a plain `YYYY-MM-DD` date, not an ISO timestamp. */
function toDateOnly(value) {
  const text = String(value ?? '').trim()
  return text === '' ? null : text
}

export default function InventoryPage() {
  const navigate = useNavigate()
  const { isAdmin } = useAuth()
  const [tab, setTab] = useState('all')
  const [page, setPage] = useState(1)
  const [expDays, setExpDays] = useState(7)
  const [reloadKey, setReloadKey] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [data, setData] = useState({ items: [], total: 0, pages: 0 })
  const [expiring, setExpiring] = useState({ items: [], total: 0 })

  /* Reference lists for the create form. */
  const [stores, setStores] = useState([])
  const [products, setProducts] = useState([])

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const [toast, setToast] = useState(null)

  useEffect(() => {
    setPage(1)
  }, [tab, expDays])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')

    if (tab === 'expiring') {
      api
        .get('/inventory/expiring', { params: { days: expDays, include_expired: true } })
        .then((res) => {
          if (cancelled) return
          setExpiring({ items: res.data.items || [], total: res.data.total || 0 })
          setData({ items: [], total: 0, pages: 0 })
        })
        .catch((err) => {
          if (!cancelled) setError(getErrorMessage(err, 'Không tải được danh sách hàng sắp hết hạn.'))
        })
        .finally(() => {
          if (!cancelled) setLoading(false)
        })
    } else {
      api
        .get('/inventory', { params: { page, page_size: PAGE_SIZE } })
        .then((res) => {
          if (cancelled) return
          setData(res.data)
          setExpiring({ items: [], total: 0 })
        })
        .catch((err) => {
          if (!cancelled) setError(getErrorMessage(err, 'Không tải được danh sách tồn kho.'))
        })
        .finally(() => {
          if (!cancelled) setLoading(false)
        })
    }

    return () => {
      cancelled = true
    }
  }, [tab, page, expDays, reloadKey])

  /* Only admins can write, so only they need the dropdown data. */
  useEffect(() => {
    if (!isAdmin) return undefined
    let cancelled = false

    Promise.all([
      api.get('/stores', { params: { page_size: 100 } }),
      api.get('/products', { params: { page_size: 100 } }),
    ])
      .then(([storesRes, productsRes]) => {
        if (cancelled) return
        setStores(storesRes.data.items || [])
        setProducts(productsRes.data.items || [])
      })
      .catch(() => {
        /* The form still opens; the selects just have no options. */
      })

    return () => {
      cancelled = true
    }
  }, [isAdmin])

  const items = tab === 'expiring' ? expiring.items : data.items
  const totalCount = tab === 'expiring' ? expiring.total : data.total
  const columns = isAdmin ? 8 : 7

  const storeNameById = useMemo(() => {
    const map = new Map()
    stores.forEach((store) => map.set(store.store_id, store.store_name))
    return map
  }, [stores])

  const productNameById = useMemo(() => {
    const map = new Map()
    products.forEach((product) => map.set(product.product_id, product.product_name))
    return map
  }, [products])

  const goToPage = (next) => {
    if (next < 1 || next > data.pages || next === page) return
    setPage(next)
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

  const openEdit = (item) => {
    setEditing(item)
    setForm({
      store_id: String(item.store_id ?? ''),
      product_id: String(item.product_id ?? ''),
      quantity: String(item.quantity ?? 0),
      received_date: item.received_date ? String(item.received_date).slice(0, 10) : '',
      expiry_date: item.expiry_date ? String(item.expiry_date).slice(0, 10) : '',
      batch_code: item.batch_code ?? '',
    })
    setFormError('')
    setFormOpen(true)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    const quantity = Number(form.quantity)
    if (!Number.isFinite(quantity) || quantity < 0) {
      setFormError('Số lượng phải là số lớn hơn hoặc bằng 0.')
      return
    }

    if (!editing) {
      if (!form.store_id) {
        setFormError('Vui lòng chọn cửa hàng.')
        return
      }
      if (!form.product_id) {
        setFormError('Vui lòng chọn sản phẩm.')
        return
      }
    }

    const shared = {
      quantity,
      received_date: toDateOnly(form.received_date),
      expiry_date: toDateOnly(form.expiry_date),
      batch_code: form.batch_code.trim() || null,
    }

    setSaving(true)
    setFormError('')

    try {
      if (editing) {
        /* Store and product identify the batch and cannot be changed. */
        await api.put(`/inventory/${editing.inventory_id}`, shared)
      } else {
        await api.post('/inventory', {
          store_id: Number(form.store_id),
          product_id: Number(form.product_id),
          ...shared,
        })
      }

      setFormOpen(false)
      setToast({
        type: 'success',
        message: editing ? 'Đã cập nhật lô hàng.' : 'Đã thêm lô hàng mới.',
      })
      setReloadKey((key) => key + 1)
    } catch (requestError) {
      setFormError(getErrorMessage(requestError, 'Không lưu được lô hàng.'))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return

    setDeleting(true)
    try {
      await api.delete(`/inventory/${deleteTarget.inventory_id}`)
      setToast({ type: 'success', message: 'Đã xoá lô hàng.' })
      setDeleteTarget(null)

      if (tab === 'all' && data.items.length === 1 && page > 1) {
        setPage((current) => current - 1)
      } else {
        setReloadKey((key) => key + 1)
      }
    } catch (requestError) {
      setToast({
        type: 'error',
        message: getErrorMessage(requestError, 'Không xoá được lô hàng.'),
      })
      setDeleteTarget(null)
    } finally {
      setDeleting(false)
    }
  }

  const labelForRow = (item) => {
    const productName =
      item.product?.product_name ||
      productNameById.get(item.product_id) ||
      `sản phẩm #${item.product_id}`
    const storeName =
      item.store?.store_name ||
      storeNameById.get(item.store_id) ||
      `cửa hàng #${item.store_id}`
    return `${productName} tại ${storeName}`
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
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-2xl">Kho hàng</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Quản lý lô hàng tồn kho theo cửa hàng và ngày hết hạn.</p>
        </div>
        <div className="flex items-center gap-2">
          {isAdmin && (
            <button type="button" onClick={openCreate} className="btn-primary w-fit">
              <Icon name="plus" className="h-4 w-4" />
              Thêm lô hàng
            </button>
          )}
          <button type="button" onClick={() => setReloadKey((k) => k + 1)} className="btn-secondary w-fit">
            <Icon name="refresh" className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Tải lại
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setTab('all')}
          className={['btn-secondary px-3', tab === 'all' ? 'border-brand-500 text-brand-700 dark:text-brand-300' : ''].join(' ')}
        >
          <Icon name="inventory" className="h-4 w-4" />
          Tất cả lô hàng
        </button>
        <button
          type="button"
          onClick={() => setTab('expiring')}
          className={['btn-secondary px-3', tab === 'expiring' ? 'border-brand-500 text-brand-700 dark:text-brand-300' : ''].join(' ')}
        >
          <Icon name="clock" className="h-4 w-4" />
          Hàng sắp hết hạn
        </button>
        {tab === 'expiring' && (
          <select value={expDays} onChange={(e) => setExpDays(Number(e.target.value))} className="input w-auto min-w-[140px]">
            <option value={3}>Trong 3 ngày</option>
            <option value={7}>Trong 7 ngày</option>
            <option value={14}>Trong 14 ngày</option>
            <option value={30}>Trong 30 ngày</option>
          </select>
        )}
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
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[880px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/70 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-400">
                    <th className="px-4 py-3 font-semibold">Sản phẩm</th>
                    <th className="px-4 py-3 font-semibold">Cửa hàng</th>
                    <th className="px-4 py-3 font-semibold">Mã lô</th>
                    <th className="px-4 py-3 text-right font-semibold">Số lượng</th>
                    <th className="px-4 py-3 font-semibold">Ngày nhập</th>
                    <th className="px-4 py-3 font-semibold">Hạn sử dụng</th>
                    <th className="px-4 py-3 font-semibold">Tình trạng</th>
                    {isAdmin && <th className="px-4 py-3 text-right font-semibold">Thao tác</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {loading ? (
                    <TableSkeleton cols={columns} />
                  ) : items.length === 0 ? (
                    <tr>
                      <td colSpan={columns} className="px-6 py-16 text-center">
                        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
                          <Icon name="inventory" className="h-6 w-6" />
                        </span>
                        <p className="mt-3 font-semibold text-slate-700 dark:text-slate-200">
                          {tab === 'expiring' ? 'Không có lô hàng sắp hết hạn' : 'Không có dữ liệu tồn kho'}
                        </p>
                      </td>
                    </tr>
                  ) : (
                    items.map((item, idx) => {
                      const daysLeft = item.days_to_expiry ?? item.days_left
                      const badge = daysBadge(daysLeft)
                      const prod = item.product || {}
                      const store = item.store || {}
                      return (
                        <tr key={item.inventory_id || idx} className="transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-800/40">
                          <td className="px-4 py-3.5">
                            <p className="font-medium text-slate-900 dark:text-white">{prod.product_name || `SP #${item.product_id}`}</p>
                            <p className="mt-0.5 font-mono text-xs text-slate-400 dark:text-slate-500">{prod.product_code || ''}</p>
                          </td>
                          <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">{store.store_name || `CH #${item.store_id}`}</td>
                          <td className="px-4 py-3.5 font-mono text-xs text-slate-500 dark:text-slate-400">{item.batch_code || '—'}</td>
                          <td className="px-4 py-3.5 text-right tabular-nums font-medium text-slate-800 dark:text-slate-100">{formatNumber(item.quantity)}</td>
                          <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">{formatDate(item.received_date)}</td>
                          <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">{formatDate(item.expiry_date)}</td>
                          <td className="px-4 py-3.5"><span className={['badge', badge.cls].join(' ')}>{badge.text}</span></td>
                          {isAdmin && (
                            <td className="px-4 py-3.5">
                              <div className="flex items-center justify-end gap-1">
                                <button
                                  type="button"
                                  onClick={() => openEdit(item)}
                                  className="rounded-lg p-2 text-slate-500 transition-colors hover:bg-sky-50 hover:text-sky-600 dark:text-slate-400 dark:hover:bg-sky-950/50 dark:hover:text-sky-400"
                                  aria-label={`Sửa lô hàng ${item.batch_code || item.inventory_id}`}
                                  title="Sửa lô hàng"
                                >
                                  <Icon name="pencil" className="h-4 w-4" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setDeleteTarget(item)}
                                  className="rounded-lg p-2 text-slate-500 transition-colors hover:bg-red-50 hover:text-red-600 dark:text-slate-400 dark:hover:bg-red-950/50 dark:hover:text-red-400"
                                  aria-label={`Xoá lô hàng ${item.batch_code || item.inventory_id}`}
                                  title="Xoá lô hàng"
                                >
                                  <Icon name="trash" className="h-4 w-4" />
                                </button>
                              </div>
                            </td>
                          )}
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>
            {tab === 'all' && data.pages > 0 && (
              <div className="flex flex-col items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 dark:border-slate-800 sm:flex-row">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Hiển thị {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, data.total)} trong {formatNumber(data.total)} lô hàng
                </p>
                <div className="flex items-center gap-2">
                  <button type="button" onClick={() => goToPage(page - 1)} disabled={loading || page <= 1} className="btn-secondary px-3 py-2"><Icon name="chevronLeft" className="h-4 w-4" /></button>
                  <span className="min-w-[72px] text-center text-sm font-medium text-slate-600 dark:text-slate-300">{page} / {data.pages}</span>
                  <button type="button" onClick={() => goToPage(page + 1)} disabled={loading || page >= data.pages} className="btn-secondary px-3 py-2"><Icon name="chevronRight" className="h-4 w-4" /></button>
                </div>
              </div>
            )}
            {tab === 'expiring' && (
              <div className="border-t border-slate-200 px-4 py-2 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
                Tổng: {formatNumber(totalCount)} lô hàng
              </div>
            )}
          </>
        )}
      </div>
      {!isAdmin && (
        <p className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500">
          <Icon name="shield" className="h-4 w-4" />
          Tài khoản nhân viên có thể xem tồn kho. Chức năng thêm/sửa/xoá chỉ dành cho owner/manager.
        </p>
      )}

      <Modal
        open={formOpen}
        title={editing ? 'Sửa lô hàng' : 'Thêm lô hàng'}
        description={
          editing
            ? 'Cửa hàng và sản phẩm của lô hàng không thể thay đổi.'
            : 'Chọn cửa hàng, sản phẩm và nhập thông tin lô hàng. Các trường có dấu * là bắt buộc.'
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
            <button type="submit" form="inventory-form" disabled={saving} className="btn-primary">
              {saving ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                  Đang lưu…
                </>
              ) : (
                <>
                  <Icon name="check" className="h-4 w-4" />
                  {editing ? 'Lưu thay đổi' : 'Thêm lô hàng'}
                </>
              )}
            </button>
          </>
        }
      >
        <form id="inventory-form" onSubmit={handleSubmit} className="space-y-4">
          {formError && (
            <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300">
              <Icon name="warning" className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Cửa hàng" htmlFor="store_id" required>
              <select
                id="store_id"
                value={form.store_id}
                onChange={(event) => setField('store_id', event.target.value)}
                className="input"
                disabled={Boolean(editing)}
                required
              >
                <option value="">— Chọn cửa hàng —</option>
                {stores.map((store) => (
                  <option key={store.store_id} value={store.store_id}>
                    {store.store_name}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Sản phẩm" htmlFor="product_id" required>
              <select
                id="product_id"
                value={form.product_id}
                onChange={(event) => setField('product_id', event.target.value)}
                className="input"
                disabled={Boolean(editing)}
                required
              >
                <option value="">— Chọn sản phẩm —</option>
                {products.map((product) => (
                  <option key={product.product_id} value={product.product_id}>
                    {product.product_name} ({product.product_code})
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Số lượng" htmlFor="quantity" required>
              <input
                id="quantity"
                type="number"
                min="0"
                step="1"
                value={form.quantity}
                onChange={(event) => setField('quantity', event.target.value)}
                className="input"
                required
              />
            </Field>

            <Field label="Mã lô" htmlFor="batch_code">
              <input
                id="batch_code"
                value={form.batch_code}
                onChange={(event) => setField('batch_code', event.target.value)}
                className="input"
                maxLength={50}
                placeholder="VD: LOT-2026-01"
              />
            </Field>

            <Field label="Ngày nhập" htmlFor="received_date">
              <input
                id="received_date"
                type="date"
                value={form.received_date}
                onChange={(event) => setField('received_date', event.target.value)}
                className="input"
              />
            </Field>

            <Field label="Hạn sử dụng" htmlFor="expiry_date" hint="Bắt buộc với hàng dễ hỏng.">
              <input
                id="expiry_date"
                type="date"
                value={form.expiry_date}
                onChange={(event) => setField('expiry_date', event.target.value)}
                className="input"
              />
            </Field>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Xoá lô hàng"
        message={
          deleteTarget
            ? `Bạn có chắc muốn xoá lô hàng ${deleteTarget.batch_code ? `"${deleteTarget.batch_code}" ` : ''}của ${labelForRow(deleteTarget)}? Hành động này không thể hoàn tác.`
            : ''
        }
        busy={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  )
}
