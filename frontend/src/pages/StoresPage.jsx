import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import Icon from '../components/common/Icon.jsx'
import Spinner from '../components/common/Spinner.jsx'
import { useAuth } from '../contexts/AuthContext.jsx'
import api from '../services/api.js'
import { formatDate, getErrorMessage } from '../utils/format.js'

const TYPE_MAP = {
  convenience_store: 'Cửa hàng tiện lợi',
  restaurant: 'Nhà hàng',
  warehouse: 'Kho',
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

export default function StoresPage() {
  const navigate = useNavigate()
  const { isAdmin } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [items, setItems] = useState([])
  const [reloadKey, setReloadKey] = useState(0)

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
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-2xl">Cửa hàng</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Danh sách cửa hàng, nhà hàng và kho trong chuỗi.</p>
        </div>
        <div className="flex items-center gap-2">
          {isAdmin && (
            <button type="button" onClick={() => setError('Thêm cửa hàng sẽ được nối với API ở bước tiếp theo.')} className="btn-primary w-fit">
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
        {error && !error.includes('sẽ được nối') ? (
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
            {error.includes('sẽ được nối') && (
              <div className="m-4 flex items-start gap-2 rounded-xl border border-sky-200 bg-sky-50 px-3.5 py-2.5 text-sm text-sky-700 dark:border-sky-900/60 dark:bg-sky-950/40 dark:text-sky-300">
                <Icon name="info" className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
                <button type="button" onClick={() => setError('')} className="ml-auto text-xs font-semibold">Đóng</button>
              </div>
            )}
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
                              <button type="button" onClick={() => setError('Sửa cửa hàng sẽ được nối với API ở bước tiếp theo.')} className="rounded-lg p-2 text-slate-500 hover:bg-sky-50 hover:text-sky-600 dark:text-slate-400 dark:hover:bg-sky-950/50 dark:hover:text-sky-400"><Icon name="pencil" className="h-4 w-4" /></button>
                              <button type="button" onClick={() => setError('Xoá cửa hàng sẽ được nối với API ở bước tiếp theo.')} className="rounded-lg p-2 text-slate-500 hover:bg-red-50 hover:text-red-600 dark:text-slate-400 dark:hover:bg-red-950/50 dark:hover:text-red-400"><Icon name="trash" className="h-4 w-4" /></button>
                            </div>
                          </td>
                        )}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
      {!isAdmin && (
        <p className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500">
          <Icon name="shield" className="h-4 w-4" />
          Chỉ owner/manager mới có quyền thêm/sửa/xoá cửa hàng.
        </p>
      )}
    </div>
  )
}
