import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import Icon from '../components/common/Icon.jsx'
import Spinner from '../components/common/Spinner.jsx'
import { useAuth } from '../contexts/AuthContext.jsx'
import api from '../services/api.js'
import { formatDate, formatNumber, getErrorMessage } from '../utils/format.js'

const PAGE_SIZE = 20

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

  const items = tab === 'expiring' ? expiring.items : data.items
  const totalCount = tab === 'expiring' ? expiring.total : data.total

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
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-2xl">Kho hàng</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Quản lý lô hàng tồn kho theo cửa hàng và ngày hết hạn.</p>
        </div>
        {isAdmin && (
          <button type="button" onClick={() => setReloadKey((k) => k + 1)} className="btn-secondary w-fit">
            <Icon name="refresh" className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Tải lại
          </button>
        )}
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
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {loading ? (
                    <TableSkeleton cols={7} />
                  ) : items.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-6 py-16 text-center">
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
    </div>
  )
}
