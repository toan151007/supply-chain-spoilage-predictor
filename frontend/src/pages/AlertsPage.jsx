import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import Icon from '../components/common/Icon.jsx'
import Spinner from '../components/common/Spinner.jsx'
import { useAuth } from '../contexts/AuthContext.jsx'
import api from '../services/api.js'
import { formatDate, getErrorMessage } from '../utils/format.js'

const SEVERITY_MAP = {
  critical: { label: 'Nghiêm trọng', cls: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300' },
  high: { label: 'Cao', cls: 'bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300' },
  medium: { label: 'Trung bình', cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300' },
  low: { label: 'Thấp', cls: 'bg-sky-100 text-sky-700 dark:bg-sky-900/50 dark:text-sky-300' },
}

const TYPE_MAP = {
  expiring_soon: 'Sắp hết hạn',
  expired: 'Đã hết hạn',
  low_stock: 'Tồn kho thấp',
  over_stock: 'Tồn kho dư',
  forecast_anomaly: 'Bất thường dự báo',
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

export default function AlertsPage() {
  const navigate = useNavigate()
  const { isAdmin } = useAuth()
  const [page, setPage] = useState(1)
  const [severity, setSeverity] = useState('')
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)
  const [loading, setLoading] = useState(true)
  const [actioning, setActioning] = useState(null)
  const [error, setError] = useState('')
  const [data, setData] = useState({ items: [], total: 0, pages: 0 })

  useEffect(() => {
    setPage(1)
  }, [severity, unreadOnly])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    api
      .get(unreadOnly ? '/alerts/unread' : '/alerts', {
        params: {
          page,
          page_size: 20,
          severity: severity || undefined,
        },
      })
      .then((res) => {
        if (!cancelled) setData(res.data)
      })
      .catch((err) => {
        if (!cancelled) setError(getErrorMessage(err, 'Không tải được danh sách cảnh báo.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [page, severity, unreadOnly, reloadKey])

  const markRead = async (alertId) => {
    setActioning(alertId)
    try {
      await api.put(`/alerts/${alertId}/read`, { is_read: true })
      setReloadKey((k) => k + 1)
    } catch (err) {
      setError(getErrorMessage(err, 'Không thể đánh dấu đã đọc.'))
    } finally {
      setActioning(null)
    }
  }

  const goToPage = (next) => {
    if (next < 1 || next > data.pages || next === page) return
    setPage(next)
  }

  return (
    <div className="space-y-5 animate-fade-in">
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
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-2xl">Cảnh báo</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Theo dõi hàng sắp hết hạn, tồn kho thấp và các cảnh báo quan trọng.</p>
        </div>
        <button type="button" onClick={() => setReloadKey((k) => k + 1)} className="btn-secondary w-fit">
          <Icon name="refresh" className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Tải lại
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <select value={severity} onChange={(e) => setSeverity(e.target.value)} className="input w-auto min-w-[140px]">
          <option value="">Tất cả mức độ</option>
          <option value="critical">Nghiêm trọng</option>
          <option value="high">Cao</option>
          <option value="medium">Trung bình</option>
          <option value="low">Thấp</option>
        </select>
        <button
          type="button"
          onClick={() => setUnreadOnly((v) => !v)}
          className={['btn-secondary px-3', unreadOnly ? 'border-brand-500 text-brand-700 dark:text-brand-300' : ''].join(' ')}
        >
          <Icon name="alerts" className="h-4 w-4" />
          {unreadOnly ? 'Hiện tất cả' : 'Chỉ chưa đọc'}
        </button>
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
            <button type="button" onClick={() => setError('')} className="btn-secondary mt-1">Đóng</button>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[880px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/70 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-400">
                    <th className="px-4 py-3 font-semibold">Cảnh báo</th>
                    <th className="px-4 py-3 font-semibold">Loại</th>
                    <th className="px-4 py-3 font-semibold">Mức độ</th>
                    <th className="px-4 py-3 font-semibold">Sản phẩm</th>
                    <th className="px-4 py-3 font-semibold">Ngày tạo</th>
                    <th className="px-4 py-3 font-semibold">Trạng thái</th>
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
                          <Icon name="alerts" className="h-6 w-6" />
                        </span>
                        <p className="mt-3 font-semibold text-slate-700 dark:text-slate-200">Không có cảnh báo</p>
                      </td>
                    </tr>
                  ) : (
                    data.items.map((alert) => (
                      <tr key={alert.alert_id} className="transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-800/40">
                        <td className="px-4 py-3.5">
                          <p className="font-medium text-slate-900 dark:text-white">{alert.title.replace('alert.title.', '').replace(/_/g, ' ')}</p>
                          <p className="mt-0.5 max-w-md truncate text-xs text-slate-500 dark:text-slate-400">{alert.message || ''}</p>
                        </td>
                        <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">{TYPE_MAP[alert.alert_type] || alert.alert_type}</td>
                        <td className="px-4 py-3.5"><span className={['badge', SEVERITY_MAP[alert.severity]?.cls || 'bg-slate-100 text-slate-600'].join(' ')}>{SEVERITY_MAP[alert.severity]?.label || alert.severity}</span></td>
                        <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">{alert.product?.product_name || (alert.product_id ? `#${alert.product_id}` : '—')}</td>
                        <td className="px-4 py-3.5 text-slate-500 dark:text-slate-400">{formatDate(alert.created_at)}</td>
                        <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">{alert.is_read ? 'Đã đọc' : 'Chưa đọc'}</td>
                        <td className="px-4 py-3.5 text-right">
                          {!alert.is_read && (isAdmin || true) && (
                            <button
                              type="button"
                              onClick={() => markRead(alert.alert_id)}
                              disabled={actioning === alert.alert_id}
                              className="btn-secondary px-3 py-1.5"
                            >
                              {actioning === alert.alert_id ? <Spinner label="" /> : <><Icon name="check" className="h-4 w-4" />Đánh dấu đã đọc</>}
                            </button>
                          )}
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
                  Trang {page} / {data.pages} · Tổng {data.total} cảnh báo
                </p>
                <div className="flex items-center gap-2">
                  <button type="button" onClick={() => goToPage(page - 1)} disabled={loading || page <= 1} className="btn-secondary px-3 py-2"><Icon name="chevronLeft" className="h-4 w-4" /></button>
                  <button type="button" onClick={() => goToPage(page + 1)} disabled={loading || page >= data.pages} className="btn-secondary px-3 py-2"><Icon name="chevronRight" className="h-4 w-4" /></button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
