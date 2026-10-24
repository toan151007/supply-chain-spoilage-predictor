import { useEffect, useState } from 'react'

import Icon from '../components/common/Icon.jsx'
import Spinner from '../components/common/Spinner.jsx'
import { useAuth } from '../contexts/AuthContext.jsx'
import api from '../services/api.js'
import { formatCurrency, formatDate, formatNumber, getErrorMessage } from '../utils/format.js'

const PAGE_SIZE = 20

const STATUS_MAP = {
  pending: { label: 'Chờ xử lý', cls: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300' },
  completed: { label: 'Hoàn thành', cls: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' },
  cancelled: { label: 'Đã huỷ', cls: 'bg-red-50 text-red-700 dark:bg-red-900/40 dark:text-red-300' },
}

const TYPE_MAP = {
  sale: { label: 'Bán hàng', cls: 'bg-sky-50 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300' },
  purchase: { label: 'Nhập hàng', cls: 'bg-amber-50 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' },
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

function DetailModal({ order, onClose }) {
  if (!order) return null
  const items = order.items || []
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center">
      <div className="absolute inset-0 bg-slate-950/60" onClick={onClose} />
      <div className="relative w-full max-w-3xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4 dark:border-slate-800">
          <div>
            <p className="text-lg font-semibold text-slate-900 dark:text-white">Chi tiết đơn hàng {order.order_code}</p>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {TYPE_MAP[order.order_type]?.label} · {STATUS_MAP[order.status]?.label} · {formatDate(order.order_date)}
            </p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800">
            <Icon name="close" />
          </button>
        </div>
        <div className="max-h-[70vh] overflow-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-400">
                <th className="px-5 py-2.5 font-semibold">Sản phẩm</th>
                <th className="px-5 py-2.5 text-right font-semibold">Số lượng</th>
                <th className="px-5 py-2.5 text-right font-semibold">Đơn giá</th>
                <th className="px-5 py-2.5 text-right font-semibold">Giảm giá</th>
                <th className="px-5 py-2.5 text-right font-semibold">Thành tiền</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {items.map((line) => (
                <tr key={line.order_item_id}>
                  <td className="px-5 py-3">
                    <p className="font-medium text-slate-900 dark:text-white">{line.product?.product_name || `SP #${line.product_id}`}</p>
                    <p className="font-mono text-xs text-slate-400 dark:text-slate-500">{line.product?.product_code || ''}</p>
                  </td>
                  <td className="px-5 py-3 text-right tabular-nums text-slate-700 dark:text-slate-200">{formatNumber(line.quantity)}</td>
                  <td className="px-5 py-3 text-right tabular-nums text-slate-600 dark:text-slate-300">{formatCurrency(line.unit_price)}</td>
                  <td className="px-5 py-3 text-right tabular-nums text-slate-500 dark:text-slate-400">{line.discount_percent}%</td>
                  <td className="px-5 py-3 text-right tabular-nums font-medium text-slate-900 dark:text-white">{formatCurrency(line.line_total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 px-5 py-3 dark:border-slate-800">
          <p className="text-sm text-slate-500 dark:text-slate-400">Số dòng: {items.length}</p>
          <div className="text-right">
            <p className="text-sm text-slate-500 dark:text-slate-400">Tổng tiền</p>
            <p className="text-lg font-bold text-slate-900 dark:text-white">{formatCurrency(order.total_amount)}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function OrdersPage() {
  const { isAdmin } = useAuth()
  const [page, setPage] = useState(1)
  const [type, setType] = useState('')
  const [status, setStatus] = useState('')
  const [reloadKey, setReloadKey] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [data, setData] = useState({ items: [], total: 0, pages: 0 })
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    setPage(1)
  }, [type, status])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    api
      .get('/orders', {
        params: {
          page,
          page_size: PAGE_SIZE,
          order_type: type || undefined,
          status: status || undefined,
        },
      })
      .then((res) => {
        if (!cancelled) setData(res.data)
      })
      .catch((err) => {
        if (!cancelled) setError(getErrorMessage(err, 'Không tải được danh sách đơn hàng.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [page, type, status, reloadKey])

  const openDetail = async (orderId) => {
    setDetailLoading(true)
    try {
      const res = await api.get(`/orders/${orderId}`)
      setDetail(res.data)
    } catch (err) {
      setError(getErrorMessage(err, 'Không tải được chi tiết đơn hàng.'))
    } finally {
      setDetailLoading(false)
    }
  }

  const goToPage = (next) => {
    if (next < 1 || next > data.pages || next === page) return
    setPage(next)
  }

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-2xl">Đơn hàng</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Theo dõi đơn bán và đơn nhập trên toàn chuỗi cửa hàng.</p>
        </div>
        {(isAdmin) && (
          <button type="button" onClick={() => setError('Tạo đơn mới sẽ được nối với API ở bước tiếp theo.')} className="btn-primary w-fit">
            <Icon name="plus" className="h-4 w-4" />
            Tạo đơn mới
          </button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <select value={type} onChange={(e) => setType(e.target.value)} className="input w-auto min-w-[140px]">
          <option value="">Tất cả loại</option>
          <option value="sale">Bán hàng</option>
          <option value="purchase">Nhập hàng</option>
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)} className="input w-auto min-w-[140px]">
          <option value="">Tất cả trạng thái</option>
          <option value="pending">Chờ xử lý</option>
          <option value="completed">Hoàn thành</option>
          <option value="cancelled">Đã huỷ</option>
        </select>
        <button type="button" onClick={() => setReloadKey((k) => k + 1)} className="btn-secondary px-3">
          <Icon name="refresh" className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="card overflow-hidden">
        {error ? (
          <div className="flex flex-col items-center gap-3 px-6 py-16 text-center">
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-red-50 text-red-600 dark:bg-red-950/50 dark:text-red-400">
              <Icon name="warning" className="h-6 w-6" />
            </span>
            <div>
              <p className="font-semibold text-slate-900 dark:text-white">Thông báo</p>
              <p className="mt-1 max-w-md text-sm text-slate-500 dark:text-slate-400">{error}</p>
            </div>
            <button type="button" onClick={() => setError('')} className="btn-secondary mt-1">Đóng</button>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[880px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/70 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-400">
                    <th className="px-4 py-3 font-semibold">Mã đơn</th>
                    <th className="px-4 py-3 font-semibold">Loại</th>
                    <th className="px-4 py-3 font-semibold">Ngày đặt</th>
                    <th className="px-4 py-3 font-semibold">Trạng thái</th>
                    <th className="px-4 py-3 text-right font-semibold">Số dòng</th>
                    <th className="px-4 py-3 text-right font-semibold">Tổng tiền</th>
                    <th className="px-4 py-3 text-right font-semibold">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {loading ? (
                    <TableSkeleton cols={7} />
                  ) : data.items.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-6 py-16 text-center">
                        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
                          <Icon name="orders" className="h-6 w-6" />
                        </span>
                        <p className="mt-3 font-semibold text-slate-700 dark:text-slate-200">Không có đơn hàng</p>
                      </td>
                    </tr>
                  ) : (
                    data.items.map((order) => (
                      <tr key={order.order_id} className="transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-800/40">
                        <td className="px-4 py-3.5">
                          <p className="font-medium text-slate-900 dark:text-white">{order.order_code}</p>
                          <p className="text-xs text-slate-400 dark:text-slate-500"># {order.order_id}</p>
                        </td>
                        <td className="px-4 py-3.5"><span className={['badge', TYPE_MAP[order.order_type]?.cls || 'bg-slate-100 text-slate-600'].join(' ')}>{TYPE_MAP[order.order_type]?.label || order.order_type}</span></td>
                        <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">{formatDate(order.order_date)}</td>
                        <td className="px-4 py-3.5"><span className={['badge', STATUS_MAP[order.status]?.cls || 'bg-slate-100 text-slate-600'].join(' ')}>{STATUS_MAP[order.status]?.label || order.status}</span></td>
                        <td className="px-4 py-3.5 text-right tabular-nums text-slate-600 dark:text-slate-300">{formatNumber(order.line_count || 0)}</td>
                        <td className="px-4 py-3.5 text-right tabular-nums font-medium text-slate-900 dark:text-white">{formatCurrency(order.total_amount)}</td>
                        <td className="px-4 py-3.5 text-right">
                          <button type="button" onClick={() => openDetail(order.order_id)} disabled={detailLoading} className="btn-secondary px-3 py-1.5">
                            <Icon name="search" className="h-4 w-4" />
                            Xem chi tiết
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            {data.pages > 0 && (
              <div className="flex flex-col items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 dark:border-slate-800 sm:flex-row">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Hiển thị {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, data.total)} trong {formatNumber(data.total)} đơn hàng
                </p>
                <div className="flex items-center gap-2">
                  <button type="button" onClick={() => goToPage(page - 1)} disabled={loading || page <= 1} className="btn-secondary px-3 py-2"><Icon name="chevronLeft" className="h-4 w-4" /></button>
                  <span className="min-w-[72px] text-center text-sm font-medium text-slate-600 dark:text-slate-300">{page} / {data.pages}</span>
                  <button type="button" onClick={() => goToPage(page + 1)} disabled={loading || page >= data.pages} className="btn-secondary px-3 py-2"><Icon name="chevronRight" className="h-4 w-4" /></button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
      <DetailModal order={detail} onClose={() => setDetail(null)} />
      {!isAdmin && (
        <p className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500">
          <Icon name="shield" className="h-4 w-4" />
          Nút tạo đơn mới chỉ dành cho owner/manager.
        </p>
      )}
    </div>
  )
}
