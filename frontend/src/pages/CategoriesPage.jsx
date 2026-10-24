import { useEffect, useState } from 'react'

import Icon from '../components/common/Icon.jsx'
import Spinner from '../components/common/Spinner.jsx'
import { useAuth } from '../contexts/AuthContext.jsx'
import api from '../services/api.js'
import { formatDate, getErrorMessage } from '../utils/format.js'

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

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-2xl">Nhóm hàng</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Phân cấp nhóm hàng (cha / con) dùng cho sản phẩm.</p>
        </div>
        <div className="flex items-center gap-2">
          {isAdmin && (
            <button type="button" onClick={() => setError('Thêm nhóm hàng sẽ được nối với API ở bước tiếp theo.')} className="btn-primary w-fit">
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
                      <>
                        <tr key={root.category_id} className="bg-slate-50/40 dark:bg-slate-800/30">
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
                                <button type="button" onClick={() => setError('Sửa nhóm hàng sẽ được nối với API ở bước tiếp theo.')} className="rounded-lg p-2 text-slate-500 hover:bg-sky-50 hover:text-sky-600 dark:text-slate-400 dark:hover:bg-sky-950/50 dark:hover:text-sky-400"><Icon name="pencil" className="h-4 w-4" /></button>
                                <button type="button" onClick={() => setError('Xoá nhóm hàng sẽ được nối với API ở bước tiếp theo.')} className="rounded-lg p-2 text-slate-500 hover:bg-red-50 hover:text-red-600 dark:text-slate-400 dark:hover:bg-red-950/50 dark:hover:text-red-400"><Icon name="trash" className="h-4 w-4" /></button>
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
                                  <button type="button" onClick={() => setError('Sửa nhóm hàng sẽ được nối với API ở bước tiếp theo.')} className="rounded-lg p-2 text-slate-500 hover:bg-sky-50 hover:text-sky-600 dark:text-slate-400 dark:hover:bg-sky-950/50 dark:hover:text-sky-400"><Icon name="pencil" className="h-4 w-4" /></button>
                                  <button type="button" onClick={() => setError('Xoá nhóm hàng sẽ được nối với API ở bước tiếp theo.')} className="rounded-lg p-2 text-slate-500 hover:bg-red-50 hover:text-red-600 dark:text-slate-400 dark:hover:bg-red-950/50 dark:hover:text-red-400"><Icon name="trash" className="h-4 w-4" /></button>
                                </div>
                              </td>
                            )}
                          </tr>
                        ))}
                      </>
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
          Chỉ owner/manager mới có quyền thêm/sửa/xoá nhóm hàng.
        </p>
      )}
    </div>
  )
}
