import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import Icon from '../components/common/Icon.jsx'
import Spinner from '../components/common/Spinner.jsx'
import { useAuth } from '../contexts/AuthContext.jsx'
import api from '../services/api.js'
import { formatCurrency, formatNumber, getErrorMessage } from '../utils/format.js'

const PAGE_SIZE = 10

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
  const [notice, setNotice] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

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

  /* Auto-dismiss the "not wired yet" notice. */
  useEffect(() => {
    if (!notice) return undefined
    const timer = setTimeout(() => setNotice(''), 4500)
    return () => clearTimeout(timer)
  }, [notice])

  const activeCount = useMemo(
    () => data.items.filter((item) => item.is_active).length,
    [data.items],
  )

  const showNotImplemented = (action) => {
    setNotice(`Chức năng "${action}" sẽ được nối với API ở bước tiếp theo.`)
  }

  const goToPage = (nextPage) => {
    if (nextPage < 1 || nextPage > data.pages || nextPage === page) return
    setPage(nextPage)
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
          <button type="button" onClick={() => showNotImplemented('Thêm sản phẩm')} className="btn-primary w-fit">
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

        {notice && (
          <div className="mt-3 flex items-start gap-2 rounded-xl border border-sky-200 bg-sky-50 px-3.5 py-2.5 text-sm text-sky-700 dark:border-sky-900/60 dark:bg-sky-950/40 dark:text-sky-300">
            <Icon name="info" className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{notice}</span>
          </div>
        )}
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
                                onClick={() => showNotImplemented('Sửa sản phẩm')}
                                className="rounded-lg p-2 text-slate-500 transition-colors hover:bg-sky-50 hover:text-sky-600 dark:text-slate-400 dark:hover:bg-sky-950/50 dark:hover:text-sky-400"
                                aria-label={`Sửa ${product.product_name}`}
                                title="Sửa sản phẩm"
                              >
                                <Icon name="pencil" className="h-4 w-4" />
                              </button>
                              <button
                                type="button"
                                onClick={() => showNotImplemented('Xoá sản phẩm')}
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
    </div>
  )
}
