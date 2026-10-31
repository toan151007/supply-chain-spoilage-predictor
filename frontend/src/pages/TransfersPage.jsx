import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import Field from '../components/common/Field.jsx'
import Icon from '../components/common/Icon.jsx'
import Modal from '../components/common/Modal.jsx'
import Toast from '../components/common/Toast.jsx'
import { useAuth } from '../contexts/AuthContext.jsx'
import api from '../services/api.js'
import { formatDate, formatNumber, getErrorMessage } from '../utils/format.js'

const PAGE_SIZE = 10

/**
 * Năm bước của quy trình, đúng thứ tự backend trả về. `rejected` và
 * `cancelled` là trạng thái kết thúc nên không nằm trên thanh quy trình.
 */
const PIPELINE = ['proposed', 'pending', 'approved', 'in_transit', 'received']

const STATUS_META = {
  proposed: {
    label: 'Đề xuất',
    badge: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
    dot: 'bg-slate-400',
  },
  pending: {
    label: 'Chờ duyệt',
    badge: 'bg-amber-50 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
    dot: 'bg-amber-500',
  },
  approved: {
    label: 'Đã duyệt',
    badge: 'bg-sky-50 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300',
    dot: 'bg-sky-500',
  },
  in_transit: {
    label: 'Đang chuyển',
    badge: 'bg-indigo-50 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300',
    dot: 'bg-indigo-500',
  },
  received: {
    label: 'Đã nhận',
    badge: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
    dot: 'bg-emerald-500',
  },
  rejected: {
    label: 'Bị từ chối',
    badge: 'bg-red-50 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    dot: 'bg-red-500',
  },
  cancelled: {
    label: 'Đã huỷ',
    badge: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
    dot: 'bg-slate-400',
  },
}

const PRIORITY_META = {
  low: { label: 'Thấp', badge: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300' },
  normal: { label: 'Bình thường', badge: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300' },
  high: { label: 'Cao', badge: 'bg-amber-50 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' },
  urgent: { label: 'Khẩn', badge: 'bg-red-50 text-red-700 dark:bg-red-900/40 dark:text-red-300' },
}

const ACTION_LABELS = {
  submit: 'Gửi duyệt',
  approve: 'Duyệt',
  reject: 'Từ chối',
  ship: 'Xác nhận giao',
  complete: 'Xác nhận nhận',
  cancel: 'Huỷ yêu cầu',
}

const ACTION_HINTS = {
  submit: 'Yêu cầu sẽ chuyển sang trạng thái "Chờ duyệt" để quản lý xem xét.',
  approve: 'Sau khi duyệt, cửa hàng gửi có thể xác nhận giao hàng.',
  reject: 'Yêu cầu sẽ dừng lại và không thể tiếp tục xử lý.',
  ship: 'Kho gửi xác nhận đã xuất hàng; hàng đang trên đường tới cửa hàng nhận.',
  complete: 'Kho nhận xác nhận đã nhận đủ hàng. Hệ thống sẽ trừ kho gửi và cộng kho nhận trong cùng một transaction.',
  cancel: 'Yêu cầu sẽ bị huỷ và không thể khôi phục.',
}

const EMPTY_FORM = {
  from_store_id: '',
  to_store_id: '',
  product_id: '',
  quantity: '',
  expiry_date: '',
  priority: 'normal',
  reason: '',
}

function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function StatusBadge({ status }) {
  const meta = STATUS_META[status] ?? STATUS_META.proposed
  return (
    <span className={`badge ${meta.badge}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
      {meta.label}
    </span>
  )
}

/** Nhung thao tac duoc phep o tung trang thai (backend van la noi quyet dinh). */
function availableActions(transfer, isAdmin) {
  switch (transfer.status) {
    case 'proposed':
      return isAdmin ? ['approve', 'reject', 'submit', 'cancel'] : ['submit', 'cancel']
    case 'pending':
      return isAdmin ? ['approve', 'reject', 'cancel'] : ['cancel']
    case 'approved':
      return ['ship']
    case 'in_transit':
      return ['complete']
    default:
      return []
  }
}

function TableSkeleton() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, index) => (
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

export default function TransfersPage() {
  const navigate = useNavigate()
  const { isAdmin } = useAuth()

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)

  const [data, setData] = useState({ items: [], total: 0, pages: 0 })
  const [summary, setSummary] = useState({ counts: {}, total: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  const [stores, setStores] = useState([])
  const [products, setProducts] = useState([])

  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const [detail, setDetail] = useState(null)
  const [pendingAction, setPendingAction] = useState(null)
  const [actionNote, setActionNote] = useState('')
  const [actionBusy, setActionBusy] = useState(false)

  const [toast, setToast] = useState(null)

  /* Debounce o tim kiem: chi gui mot request sau khi nguoi dung ngung go. */
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

    Promise.all([
      api.get('/transfers', {
        params: {
          page,
          page_size: PAGE_SIZE,
          status: statusFilter || undefined,
          search: search || undefined,
        },
      }),
      api.get('/transfers/summary'),
    ])
      .then(([listResponse, summaryResponse]) => {
        if (cancelled) return
        setData(listResponse.data)
        setSummary(summaryResponse.data)
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(getErrorMessage(requestError, 'Không tải được danh sách điều chuyển.'))
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [page, statusFilter, search, reloadKey])

  /* Danh muc cho form tao yeu cau, chi tai mot lan. */
  useEffect(() => {
    api
      .get('/stores', { params: { page_size: 100 } })
      .then((response) => setStores(response.data.items || []))
      .catch(() => setStores([]))

    api
      .get('/products', { params: { page_size: 100, is_active: true } })
      .then((response) => setProducts(response.data.items || []))
      .catch(() => setProducts([]))
  }, [])

  const counts = summary.counts || {}
  const openCount = (counts.pending || 0) + (counts.approved || 0) + (counts.in_transit || 0)

  const productById = useMemo(() => {
    const map = new Map()
    products.forEach((item) => map.set(item.product_id, item))
    return map
  }, [products])

  const selectedProduct = form.product_id ? productById.get(Number(form.product_id)) : null

  const openCreate = () => {
    setForm(EMPTY_FORM)
    setFormError('')
    setFormOpen(true)
  }

  const submitForm = async (event) => {
    event.preventDefault()
    setFormError('')

    if (!form.from_store_id || !form.to_store_id) {
      setFormError('Vui lòng chọn cửa hàng gửi và cửa hàng nhận.')
      return
    }
    if (form.from_store_id === form.to_store_id) {
      setFormError('Cửa hàng gửi và cửa hàng nhận phải khác nhau.')
      return
    }
    if (!form.product_id) {
      setFormError('Vui lòng chọn sản phẩm cần điều chuyển.')
      return
    }
    const quantity = Number(form.quantity)
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setFormError('Số lượng phải là số lớn hơn 0.')
      return
    }

    setSaving(true)
    try {
      await api.post('/transfers', {
        from_store_id: Number(form.from_store_id),
        to_store_id: Number(form.to_store_id),
        product_id: Number(form.product_id),
        quantity,
        expiry_date: form.expiry_date || null,
        priority: form.priority,
        reason: form.reason.trim() || null,
      })
      setToast({ type: 'success', message: 'Đã tạo yêu cầu điều chuyển.' })
      setFormOpen(false)
      setForm(EMPTY_FORM)
      setReloadKey((key) => key + 1)
    } catch (requestError) {
      setFormError(getErrorMessage(requestError, 'Không tạo được yêu cầu điều chuyển.'))
    } finally {
      setSaving(false)
    }
  }

  const askAction = (transfer, action) => {
    setActionNote('')
    setPendingAction({ transfer, action })
  }

  const runAction = async () => {
    if (!pendingAction) return
    const { transfer, action } = pendingAction
    setActionBusy(true)
    try {
      const body = action === 'approve' || action === 'reject' ? { note: actionNote.trim() || null } : undefined
      await api.post(`/transfers/${transfer.transfer_id}/${action}`, body)
      setToast({
        type: 'success',
        message: `${ACTION_LABELS[action]} thành công cho ${transfer.transfer_code}.`,
      })
      setPendingAction(null)
      setActionNote('')
      setReloadKey((key) => key + 1)
    } catch (requestError) {
      setToast({
        type: 'error',
        message: getErrorMessage(requestError, 'Không thực hiện được thao tác.'),
      })
    } finally {
      setActionBusy(false)
    }
  }

  const goToPage = (next) => {
    if (next < 1 || next > data.pages || next === page) return
    setPage(next)
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
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-2xl">
            Điều chuyển hàng
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Luân chuyển hàng giữa các cửa hàng theo quy trình đề xuất → chờ duyệt → đã duyệt → đang chuyển → đã nhận.
          </p>
        </div>
        <button type="button" onClick={openCreate} className="btn-primary w-fit">
          <Icon name="plus" className="h-4 w-4" />
          Tạo yêu cầu
        </button>
      </div>

      {/* Thanh quy trinh: bam vao mot buoc de loc */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
        {PIPELINE.map((code, index) => {
          const meta = STATUS_META[code]
          const active = statusFilter === code
          return (
            <button
              key={code}
              type="button"
              onClick={() => {
                setStatusFilter(active ? '' : code)
                setPage(1)
              }}
              className={[
                'card px-4 py-3 text-left transition-colors',
                active
                  ? 'ring-2 ring-brand-500 dark:ring-brand-400'
                  : 'hover:bg-slate-50 dark:hover:bg-slate-800/60',
              ].join(' ')}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                  Bước {index + 1}
                </span>
                <span className={`h-2 w-2 rounded-full ${meta.dot}`} />
              </div>
              <p className="mt-1 text-sm font-semibold text-slate-800 dark:text-slate-100">{meta.label}</p>
              <p className="mt-0.5 text-xl font-bold text-slate-900 dark:text-white">
                {loading ? '—' : formatNumber(counts[code] || 0)}
              </p>
            </button>
          )
        })}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="card px-4 py-3">
          <p className="text-xs text-slate-500 dark:text-slate-400">Tổng yêu cầu</p>
          <p className="mt-0.5 text-xl font-bold text-slate-900 dark:text-white">
            {loading ? '—' : formatNumber(summary.total || 0)}
          </p>
        </div>
        <div className="card px-4 py-3">
          <p className="text-xs text-slate-500 dark:text-slate-400">Đang cần xử lý</p>
          <p className="mt-0.5 text-xl font-bold text-amber-600 dark:text-amber-400">
            {loading ? '—' : formatNumber(openCount)}
          </p>
        </div>
        <div className="card px-4 py-3">
          <p className="text-xs text-slate-500 dark:text-slate-400">Hàng đang trên đường</p>
          <p className="mt-0.5 text-xl font-bold text-indigo-600 dark:text-indigo-400">
            {loading ? '—' : formatNumber(summary.in_transit_quantity || 0)}
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
              placeholder="Tìm theo mã yêu cầu, sản phẩm hoặc cửa hàng…"
              className="input pl-10"
              aria-label="Tìm yêu cầu điều chuyển"
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={(event) => {
                setStatusFilter(event.target.value)
                setPage(1)
              }}
              className="input w-auto min-w-[170px]"
              aria-label="Lọc theo trạng thái"
            >
              <option value="">Tất cả trạng thái</option>
              {Object.entries(STATUS_META).map(([code, meta]) => (
                <option key={code} value={code}>
                  {meta.label}
                </option>
              ))}
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
              <table className="w-full min-w-[1080px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/70 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-400">
                    <th className="px-4 py-3 font-semibold">Mã yêu cầu</th>
                    <th className="px-4 py-3 font-semibold">Tuyến điều chuyển</th>
                    <th className="px-4 py-3 font-semibold">Sản phẩm</th>
                    <th className="px-4 py-3 text-right font-semibold">Số lượng</th>
                    <th className="px-4 py-3 font-semibold">Trạng thái</th>
                    <th className="px-4 py-3 font-semibold">Thời điểm</th>
                    <th className="px-4 py-3 text-right font-semibold">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {loading ? (
                    <TableSkeleton />
                  ) : data.items.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-6 py-16 text-center">
                        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
                          <Icon name="transfer" className="h-6 w-6" />
                        </span>
                        <p className="mt-3 font-semibold text-slate-700 dark:text-slate-200">
                          Chưa có yêu cầu điều chuyển nào
                        </p>
                        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                          Bấm “Tạo yêu cầu” để đề xuất chuyển hàng từ cửa hàng này sang cửa hàng khác.
                        </p>
                      </td>
                    </tr>
                  ) : (
                    data.items.map((item) => {
                      const priority = PRIORITY_META[item.priority] ?? PRIORITY_META.normal
                      const actions = availableActions(item, isAdmin)
                      return (
                        <tr
                          key={item.transfer_id}
                          className="transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-800/40"
                        >
                          <td className="px-4 py-3.5">
                            <button
                              type="button"
                              onClick={() => setDetail(item)}
                              className="font-mono text-xs font-semibold text-brand-600 hover:underline dark:text-brand-400"
                            >
                              {item.transfer_code}
                            </button>
                            <div className="mt-1">
                              <span className={`badge ${priority.badge}`}>{priority.label}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3.5">
                            <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
                              <span className="font-medium text-slate-800 dark:text-slate-100">
                                {item.from_store?.store_name || `CH #${item.from_store_id}`}
                              </span>
                              <Icon name="chevronRight" className="h-3.5 w-3.5 text-slate-400" />
                              <span className="font-medium text-slate-800 dark:text-slate-100">
                                {item.to_store?.store_name || `CH #${item.to_store_id}`}
                              </span>
                            </div>
                            {item.expiry_date && (
                              <p className="mt-0.5 text-xs text-slate-400 dark:text-slate-500">
                                Lô hết hạn {formatDate(item.expiry_date)}
                              </p>
                            )}
                          </td>
                          <td className="px-4 py-3.5">
                            <p className="font-medium text-slate-900 dark:text-white">
                              {item.product?.product_name || `SP #${item.product_id}`}
                            </p>
                            <p className="font-mono text-xs text-slate-400 dark:text-slate-500">
                              {item.product?.product_code || ''}
                            </p>
                          </td>
                          <td className="px-4 py-3.5 text-right tabular-nums font-semibold text-slate-900 dark:text-white">
                            {formatNumber(item.quantity)}
                          </td>
                          <td className="px-4 py-3.5">
                            <StatusBadge status={item.status} />
                          </td>
                          <td className="px-4 py-3.5 text-xs text-slate-500 dark:text-slate-400">
                            {formatDateTime(item.requested_at)}
                          </td>
                          <td className="px-4 py-3.5">
                            <div className="flex flex-wrap items-center justify-end gap-1.5">
                              {actions.length === 0 ? (
                                <button
                                  type="button"
                                  onClick={() => setDetail(item)}
                                  className="btn-secondary px-2.5 py-1.5 text-xs"
                                >
                                  Chi tiết
                                </button>
                              ) : (
                                actions.map((action) => (
                                  <button
                                    key={action}
                                    type="button"
                                    onClick={() => askAction(item, action)}
                                    className={[
                                      'btn px-2.5 py-1.5 text-xs',
                                      action === 'approve' || action === 'complete'
                                        ? 'bg-emerald-600 text-white hover:bg-emerald-700'
                                        : action === 'reject' || action === 'cancel'
                                          ? 'bg-red-600 text-white hover:bg-red-700'
                                          : 'bg-slate-600 text-white hover:bg-slate-700',
                                    ].join(' ')}
                                  >
                                    {ACTION_LABELS[action]}
                                  </button>
                                ))
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

            {data.pages > 0 && (
              <div className="flex flex-col items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 dark:border-slate-800 sm:flex-row">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Trang {page} / {data.pages} · Tổng {formatNumber(data.total)} yêu cầu
                </p>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => goToPage(page - 1)}
                    disabled={loading || page <= 1}
                    className="btn-secondary px-3 py-2"
                  >
                    <Icon name="chevronLeft" className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => goToPage(page + 1)}
                    disabled={loading || page >= data.pages}
                    className="btn-secondary px-3 py-2"
                  >
                    <Icon name="chevronRight" className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Modal tao yeu cau */}
      <Modal
        open={formOpen}
        title="Tạo yêu cầu điều chuyển"
        description="Hàng sẽ được trừ ở cửa hàng gửi và cộng ở cửa hàng nhận khi yêu cầu hoàn tất."
        onClose={saving ? undefined : () => setFormOpen(false)}
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
            <button type="submit" form="transfer-form" disabled={saving} className="btn-primary">
              {saving ? 'Đang tạo…' : 'Tạo yêu cầu'}
            </button>
          </>
        }
      >
        <form id="transfer-form" onSubmit={submitForm} className="space-y-4">
          {formError && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/50 dark:text-red-300">
              {formError}
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Cửa hàng gửi" htmlFor="from_store_id" required>
              <select
                id="from_store_id"
                value={form.from_store_id}
                onChange={(event) => setForm({ ...form, from_store_id: event.target.value })}
                className="input"
              >
                <option value="">— Chọn cửa hàng —</option>
                {stores.map((store) => (
                  <option key={store.store_id} value={store.store_id}>
                    {store.store_name}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Cửa hàng nhận" htmlFor="to_store_id" required>
              <select
                id="to_store_id"
                value={form.to_store_id}
                onChange={(event) => setForm({ ...form, to_store_id: event.target.value })}
                className="input"
              >
                <option value="">— Chọn cửa hàng —</option>
                {stores
                  .filter((store) => String(store.store_id) !== String(form.from_store_id))
                  .map((store) => (
                    <option key={store.store_id} value={store.store_id}>
                      {store.store_name}
                    </option>
                  ))}
              </select>
            </Field>

            <Field
              label="Sản phẩm"
              htmlFor="product_id"
              required
              hint={selectedProduct ? `Đơn vị tính: ${selectedProduct.unit}` : undefined}
            >
              <select
                id="product_id"
                value={form.product_id}
                onChange={(event) => setForm({ ...form, product_id: event.target.value })}
                className="input"
              >
                <option value="">— Chọn sản phẩm —</option>
                {products.map((product) => (
                  <option key={product.product_id} value={product.product_id}>
                    {product.product_name} ({product.product_code})
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Số lượng" htmlFor="quantity" required hint="Số lượng phải có sẵn tại cửa hàng gửi.">
              <input
                id="quantity"
                type="number"
                min="0.001"
                step="0.001"
                value={form.quantity}
                onChange={(event) => setForm({ ...form, quantity: event.target.value })}
                className="input"
                placeholder="Ví dụ: 50"
              />
            </Field>

            <Field
              label="Lô hết hạn (tuỳ chọn)"
              htmlFor="expiry_date"
              hint="Để trống: hệ thống tự trừ theo lô hết hạn trước (FEFO)."
            >
              <input
                id="expiry_date"
                type="date"
                value={form.expiry_date}
                onChange={(event) => setForm({ ...form, expiry_date: event.target.value })}
                className="input"
              />
            </Field>

            <Field label="Mức ưu tiên" htmlFor="priority">
              <select
                id="priority"
                value={form.priority}
                onChange={(event) => setForm({ ...form, priority: event.target.value })}
                className="input"
              >
                <option value="low">Thấp</option>
                <option value="normal">Bình thường</option>
                <option value="high">Cao</option>
                <option value="urgent">Khẩn</option>
              </select>
            </Field>
          </div>

          <Field label="Lý do" htmlFor="reason" hint="Ví dụ: cửa hàng nhận sắp thiếu hàng, hàng cận hạn cần chuyển gấp.">
            <textarea
              id="reason"
              rows={2}
              value={form.reason}
              onChange={(event) => setForm({ ...form, reason: event.target.value })}
              className="input"
              maxLength={500}
            />
          </Field>
        </form>
      </Modal>

      {/* Modal xac nhan thao tac */}
      <Modal
        open={Boolean(pendingAction)}
        title={pendingAction ? ACTION_LABELS[pendingAction.action] : ''}
        description={pendingAction ? ACTION_HINTS[pendingAction.action] : ''}
        onClose={actionBusy ? undefined : () => setPendingAction(null)}
        size="sm"
        footer={
          <>
            <button
              type="button"
              onClick={() => setPendingAction(null)}
              disabled={actionBusy}
              className="btn-secondary"
            >
              Đóng
            </button>
            <button type="button" onClick={runAction} disabled={actionBusy} className="btn-primary">
              {actionBusy ? 'Đang xử lý…' : 'Xác nhận'}
            </button>
          </>
        }
      >
        {pendingAction && (
          <div className="space-y-3">
            <div className="rounded-lg bg-slate-50 px-3 py-2.5 text-sm dark:bg-slate-800/60">
              <p className="font-mono text-xs font-semibold text-slate-500 dark:text-slate-400">
                {pendingAction.transfer.transfer_code}
              </p>
              <p className="mt-1 font-medium text-slate-800 dark:text-slate-100">
                {pendingAction.transfer.product?.product_name} · {formatNumber(pendingAction.transfer.quantity)} đơn vị
              </p>
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                {pendingAction.transfer.from_store?.store_name} → {pendingAction.transfer.to_store?.store_name}
              </p>
            </div>

            {(pendingAction.action === 'approve' || pendingAction.action === 'reject') && (
              <Field label="Ghi chú (tuỳ chọn)" htmlFor="action_note">
                <textarea
                  id="action_note"
                  rows={2}
                  value={actionNote}
                  onChange={(event) => setActionNote(event.target.value)}
                  className="input"
                  maxLength={500}
                />
              </Field>
            )}
          </div>
        )}
      </Modal>

      {/* Modal chi tiet */}
      <Modal
        open={Boolean(detail)}
        title={detail ? `Yêu cầu ${detail.transfer_code}` : ''}
        onClose={() => setDetail(null)}
        size="lg"
        footer={
          <button type="button" onClick={() => setDetail(null)} className="btn-secondary">
            Đóng
          </button>
        }
      >
        {detail && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={detail.status} />
              <span className={`badge ${(PRIORITY_META[detail.priority] ?? PRIORITY_META.normal).badge}`}>
                Ưu tiên {(PRIORITY_META[detail.priority] ?? PRIORITY_META.normal).label}
              </span>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-lg bg-slate-50 px-3 py-2.5 dark:bg-slate-800/60">
                <p className="text-xs text-slate-500 dark:text-slate-400">Cửa hàng gửi</p>
                <p className="mt-0.5 font-medium text-slate-800 dark:text-slate-100">
                  {detail.from_store?.store_name}
                </p>
              </div>
              <div className="rounded-lg bg-slate-50 px-3 py-2.5 dark:bg-slate-800/60">
                <p className="text-xs text-slate-500 dark:text-slate-400">Cửa hàng nhận</p>
                <p className="mt-0.5 font-medium text-slate-800 dark:text-slate-100">
                  {detail.to_store?.store_name}
                </p>
              </div>
              <div className="rounded-lg bg-slate-50 px-3 py-2.5 dark:bg-slate-800/60">
                <p className="text-xs text-slate-500 dark:text-slate-400">Sản phẩm</p>
                <p className="mt-0.5 font-medium text-slate-800 dark:text-slate-100">
                  {detail.product?.product_name}
                </p>
                <p className="font-mono text-xs text-slate-400 dark:text-slate-500">
                  {detail.product?.product_code}
                </p>
              </div>
              <div className="rounded-lg bg-slate-50 px-3 py-2.5 dark:bg-slate-800/60">
                <p className="text-xs text-slate-500 dark:text-slate-400">Số lượng</p>
                <p className="mt-0.5 font-semibold text-slate-900 dark:text-white">
                  {formatNumber(detail.quantity)}
                </p>
              </div>
            </div>

            {detail.reason && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Lý do
                </p>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{detail.reason}</p>
              </div>
            )}

            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Tiến trình
              </p>
              <ol className="mt-2 space-y-2 text-sm">
                <li className="flex items-start gap-2">
                  <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-slate-400" />
                  <span className="text-slate-600 dark:text-slate-300">
                    <strong className="font-medium text-slate-800 dark:text-slate-100">Đề xuất</strong> ·{' '}
                    {formatDateTime(detail.requested_at)}
                    {detail.requested_by_name ? ` · ${detail.requested_by_name}` : ''}
                  </span>
                </li>
                {detail.approved_at && (
                  <li className="flex items-start gap-2">
                    <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-sky-500" />
                    <span className="text-slate-600 dark:text-slate-300">
                      <strong className="font-medium text-slate-800 dark:text-slate-100">Đã duyệt</strong> ·{' '}
                      {formatDateTime(detail.approved_at)}
                      {detail.approved_by_name ? ` · ${detail.approved_by_name}` : ''}
                    </span>
                  </li>
                )}
                {detail.rejected_at && (
                  <li className="flex items-start gap-2">
                    <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-red-500" />
                    <span className="text-slate-600 dark:text-slate-300">
                      <strong className="font-medium text-slate-800 dark:text-slate-100">Từ chối</strong> ·{' '}
                      {formatDateTime(detail.rejected_at)}
                      {detail.rejected_by_name ? ` · ${detail.rejected_by_name}` : ''}
                    </span>
                  </li>
                )}
                {detail.shipped_at && (
                  <li className="flex items-start gap-2">
                    <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-indigo-500" />
                    <span className="text-slate-600 dark:text-slate-300">
                      <strong className="font-medium text-slate-800 dark:text-slate-100">Đang chuyển</strong> ·{' '}
                      {formatDateTime(detail.shipped_at)}
                      {detail.shipped_by_name ? ` · ${detail.shipped_by_name}` : ''}
                    </span>
                  </li>
                )}
                {detail.completed_at && (
                  <li className="flex items-start gap-2">
                    <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-emerald-500" />
                    <span className="text-slate-600 dark:text-slate-300">
                      <strong className="font-medium text-slate-800 dark:text-slate-100">Đã nhận</strong> ·{' '}
                      {formatDateTime(detail.completed_at)}
                      {detail.received_by_name ? ` · ${detail.received_by_name}` : ''}
                    </span>
                  </li>
                )}
              </ol>
            </div>

            {detail.note && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Ghi chú
                </p>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{detail.note}</p>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
