import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import Icon from '../components/common/Icon.jsx'
import ReportTabs from '../components/reports/ReportTabs.jsx'
import api from '../services/api.js'
import {
  formatCompactCurrency,
  formatCurrency,
  formatNumber,
  getErrorMessage,
} from '../utils/format.js'

/* Colour only helps scanning the list; it does not encode anything. */
const DOT_COLORS = [
  'bg-brand-500',
  'bg-emerald-500',
  'bg-amber-500',
  'bg-rose-500',
  'bg-violet-500',
  'bg-sky-500',
  'bg-orange-500',
  'bg-teal-500',
]

const SORTS = [
  { value: 'quantity', label: 'Số lượng bán' },
  { value: 'revenue', label: 'Doanh thu' },
  { value: 'name', label: 'Tên A → Z' },
]

const LIMITS = [
  { value: '10', label: '10' },
  { value: '20', label: '20' },
  { value: '50', label: '50' },
  { value: 'all', label: 'Tất cả' },
]

const WEEKDAYS = [
  'Chủ Nhật',
  'Thứ Hai',
  'Thứ Ba',
  'Thứ Tư',
  'Thứ Năm',
  'Thứ Sáu',
  'Thứ Bảy',
]

const pad = (value) => String(value).padStart(2, '0')

/* Parse as a local date: `new Date('2026-11-16')` is UTC and would show the
   15th in some time zones, which is exactly the kind of off-by-one that makes
   a date picker look broken. */
function parseISO(value) {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function toISO(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function addDays(value, delta) {
  const date = parseISO(value)
  date.setDate(date.getDate() + delta)
  return toISO(date)
}

function dateLabel(value) {
  if (!value) return 'Đang tải…'
  const date = parseISO(value)
  return `${WEEKDAYS[date.getDay()]}, ${pad(date.getDate())}/${pad(
    date.getMonth() + 1,
  )}/${date.getFullYear()}`
}

/* Vietnamese search should match both "Sữa" and "sua". */
function normalizeText(value) {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .toLowerCase()
}

function SkeletonRows() {
  return (
    <ul className="divide-y divide-slate-100 dark:divide-slate-800">
      {Array.from({ length: 8 }, (_, index) => (
        <li key={index} className="flex items-center gap-3 px-4 py-3.5 sm:px-5">
          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
          <div className="min-w-0 flex-1 space-y-2">
            <div className="h-3.5 w-1/2 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
            <div className="h-2.5 w-1/3 animate-pulse rounded bg-slate-100 dark:bg-slate-800" />
          </div>
          <div className="h-3.5 w-20 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
          <div className="h-8 w-14 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />
        </li>
      ))}
    </ul>
  )
}

export default function TopSellingPage() {
  const navigate = useNavigate()
  const dateInputRef = useRef(null)

  const [rows, setRows] = useState([])
  const [date, setDate] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  const [searchOpen, setSearchOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [filterOpen, setFilterOpen] = useState(false)
  const [sortBy, setSortBy] = useState('quantity')
  const [limit, setLimit] = useState('all')

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')

    api
      .get('/reports/top-selling', { params: date ? { date } : {} })
      .then(({ data }) => {
        if (!active) return
        const list = Array.isArray(data) ? data : []
        setRows(list)
        /* First visit: the API answers with the latest day that has sales,
           and the returned rows carry that date. */
        if (!date && list.length) setDate(list[0].sale_date)
      })
      .catch((requestError) => {
        if (!active) return
        setRows([])
        setError(
          getErrorMessage(
            requestError,
            'Không tải được danh sách mặt hàng bán chạy. Vui lòng thử lại.',
          ),
        )
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [date, reloadKey])

  const totals = useMemo(
    () =>
      rows.reduce(
        (acc, row) => ({
          products: acc.products + 1,
          quantity: acc.quantity + Number(row.total_quantity || 0),
          revenue: acc.revenue + Number(row.total_revenue || 0),
        }),
        { products: 0, quantity: 0, revenue: 0 },
      ),
    [rows],
  )

  const visibleRows = useMemo(() => {
    const keyword = normalizeText(search.trim())
    let list = keyword
      ? rows.filter(
          (row) =>
            normalizeText(row.product_name).includes(keyword) ||
            normalizeText(row.category_name).includes(keyword) ||
            normalizeText(row.product_code).includes(keyword),
        )
      : [...rows]

    if (sortBy === 'revenue') {
      list.sort((a, b) => b.total_revenue - a.total_revenue)
    } else if (sortBy === 'name') {
      list.sort((a, b) => a.product_name.localeCompare(b.product_name, 'vi'))
    } else {
      list.sort((a, b) => b.total_quantity - a.total_quantity)
    }

    return limit === 'all' ? list : list.slice(0, Number(limit))
  }, [rows, search, sortBy, limit])

  const openDatePicker = () => {
    const input = dateInputRef.current
    if (!input) return
    try {
      input.showPicker()
    } catch {
      input.focus()
    }
  }

  const nextDay = date ? addDays(date, 1) : null
  const previousDay = date ? addDays(date, -1) : null

  return (
    <div className="mx-auto w-full max-w-3xl space-y-4 animate-fade-in">
      <ReportTabs />

      <div className="card overflow-hidden">
        <div className="flex items-center gap-1.5 px-3 py-3 sm:px-5">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="rounded-xl p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white"
            aria-label="Quay lại"
          >
            <Icon name="chevronLeft" className="h-5 w-5" />
          </button>

          <div className="min-w-0 flex-1">
            <h1 className="truncate text-lg font-bold tracking-tight text-slate-900 dark:text-white sm:text-xl">
              Mặt hàng bán chạy
            </h1>
            <p className="truncate text-xs text-slate-500 dark:text-slate-400">
              Số lượng bán ra và doanh thu theo từng ngày
            </p>
          </div>

          <button
            type="button"
            onClick={() => setSearchOpen((open) => !open)}
            className={`rounded-xl p-2 transition-colors ${
              searchOpen
                ? 'bg-brand-50 text-brand-700 dark:bg-brand-950/50 dark:text-brand-300'
                : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white'
            }`}
            aria-label="Tìm kiếm sản phẩm"
            aria-pressed={searchOpen}
          >
            <Icon name="search" className="h-5 w-5" />
          </button>
          <button
            type="button"
            onClick={() => setFilterOpen((open) => !open)}
            className={`rounded-xl p-2 transition-colors ${
              filterOpen
                ? 'bg-brand-50 text-brand-700 dark:bg-brand-950/50 dark:text-brand-300'
                : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white'
            }`}
            aria-label="Bộ lọc danh sách"
            aria-pressed={filterOpen}
          >
            <Icon name="filter" className="h-5 w-5" />
          </button>
        </div>

        {searchOpen && (
          <div className="border-t border-slate-100 px-3 py-3 dark:border-slate-800 sm:px-5">
            <div className="relative">
              <Icon
                name="search"
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
              />
              <input
                autoFocus
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Tìm theo tên, mã hoặc nhóm hàng…"
                className="input w-full pl-9 pr-9"
                aria-label="Tìm kiếm sản phẩm"
              />
              {search && (
                <button
                  type="button"
                  onClick={() => setSearch('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                  aria-label="Xoá từ khoá"
                >
                  <Icon name="close" className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>
        )}

        {filterOpen && (
          <div className="space-y-3 border-t border-slate-100 px-3 py-3.5 dark:border-slate-800 sm:px-5">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">
                Sắp xếp theo
              </p>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {SORTS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setSortBy(option.value)}
                    className={`rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                      sortBy === option.value
                        ? 'bg-brand-600 text-white'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
                    }`}
                    aria-pressed={sortBy === option.value}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">
                Hiển thị
              </p>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {LIMITS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setLimit(option.value)}
                    className={`min-w-[52px] rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                      limit === option.value
                        ? 'bg-brand-600 text-white'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
                    }`}
                    aria-pressed={limit === option.value}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="card p-3 sm:p-5">
        <div className="flex items-center justify-between gap-2">
          <button
            type="button"
            onClick={() => previousDay && setDate(previousDay)}
            disabled={!previousDay}
            className="rounded-xl p-2.5 text-slate-600 transition-colors hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 dark:text-slate-300 dark:hover:bg-slate-800"
            aria-label="Ngày trước"
          >
            <Icon name="chevronLeft" className="h-5 w-5" />
          </button>

          <button
            type="button"
            onClick={openDatePicker}
            className="relative flex min-w-0 flex-1 flex-col items-center rounded-xl px-2 py-1 text-center transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/60"
            aria-label="Chọn ngày xem"
          >
            <span className="flex items-center gap-1 text-[11px] font-medium uppercase tracking-wide text-slate-400 dark:text-slate-500">
              <Icon name="calendar" className="h-3.5 w-3.5" />
              Ngày xem
            </span>
            <span className="mt-0.5 truncate text-base font-bold text-slate-900 dark:text-white sm:text-lg">
              {dateLabel(date)}
            </span>
          </button>

          <button
            type="button"
            onClick={() => nextDay && setDate(nextDay)}
            disabled={!nextDay}
            className="rounded-xl p-2.5 text-slate-600 transition-colors hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 dark:text-slate-300 dark:hover:bg-slate-800"
            aria-label="Ngày sau"
          >
            <Icon name="chevronRight" className="h-5 w-5" />
          </button>

          <input
            ref={dateInputRef}
            type="date"
            value={date ?? ''}
            onChange={(event) => event.target.value && setDate(event.target.value)}
            className="pointer-events-none absolute h-0 w-0 opacity-0"
            tabIndex={-1}
            aria-hidden="true"
          />
        </div>

        <div className="mt-3 grid grid-cols-3 gap-2 border-t border-slate-100 pt-3 dark:border-slate-800">
          <div className="text-center">
            <p className="text-base font-bold tabular-nums text-slate-900 dark:text-white sm:text-lg">
              {formatNumber(totals.products)}
            </p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">Sản phẩm</p>
          </div>
          <div className="border-x border-slate-100 text-center dark:border-slate-800">
            <p className="text-base font-bold tabular-nums text-slate-900 dark:text-white sm:text-lg">
              {formatNumber(totals.quantity)}
            </p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">Bán ra</p>
          </div>
          <div className="text-center">
            <p className="text-base font-bold tabular-nums text-slate-900 dark:text-white sm:text-lg">
              {formatCompactCurrency(totals.revenue)}
            </p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">Doanh thu</p>
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="flex items-center justify-between gap-2 border-b border-slate-100 px-4 py-3 dark:border-slate-800 sm:px-5">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-white">
            Danh sách sản phẩm
          </h2>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {visibleRows.length}/{rows.length} ·{' '}
            {sortBy === 'revenue'
              ? 'doanh thu giảm dần'
              : sortBy === 'name'
                ? 'tên A → Z'
                : 'số lượng bán giảm dần'}
          </span>
        </div>

        {error ? (
          <div className="px-5 py-10 text-center">
            <Icon name="warning" className="mx-auto h-8 w-8 text-red-500" />
            <p className="mt-2 text-sm font-medium text-slate-900 dark:text-white">
              {error}
            </p>
            <button
              type="button"
              onClick={() => setReloadKey((key) => key + 1)}
              className="btn-secondary mt-4"
            >
              <Icon name="refresh" className="h-4 w-4" />
              Thử lại
            </button>
          </div>
        ) : loading && !rows.length ? (
          <SkeletonRows />
        ) : !rows.length ? (
          <div className="px-5 py-10 text-center">
            <Icon name="calendar" className="mx-auto h-8 w-8 text-slate-300 dark:text-slate-600" />
            <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-white">
              Không có dữ liệu bán hàng cho ngày này
            </p>
            <p className="mx-auto mt-1 max-w-sm text-sm text-slate-500 dark:text-slate-400">
              Thử lùi sang ngày khác hoặc quay về ngày gần nhất có dữ liệu bán hàng.
            </p>
            <button
              type="button"
              onClick={() => setDate(null)}
              className="btn-secondary mt-4"
            >
              <Icon name="refresh" className="h-4 w-4" />
              Về ngày có dữ liệu gần nhất
            </button>
          </div>
        ) : !visibleRows.length ? (
          <div className="px-5 py-10 text-center">
            <Icon name="search" className="mx-auto h-8 w-8 text-slate-300 dark:text-slate-600" />
            <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-white">
              Không tìm thấy sản phẩm phù hợp
            </p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Xoá từ khoá hoặc thử tên khác.
            </p>
          </div>
        ) : (
          <ul
            className={`divide-y divide-slate-100 transition-opacity dark:divide-slate-800 ${
              loading ? 'opacity-60' : ''
            }`}
          >
            {visibleRows.map((row, index) => (
              <li
                key={row.product_id}
                className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/50 sm:px-5"
              >
                <span
                  className={`h-2.5 w-2.5 shrink-0 rounded-full ${
                    DOT_COLORS[index % DOT_COLORS.length]
                  }`}
                  aria-hidden="true"
                />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-slate-900 dark:text-white">
                    {row.product_name}
                  </p>
                  <p className="mt-0.5 truncate text-xs text-slate-500 dark:text-slate-400">
                    {row.category_name || 'Chưa phân nhóm'}
                    {row.product_code ? ` · ${row.product_code}` : ''}
                  </p>
                </div>
                <div className="shrink-0 text-right">
                  <p className="whitespace-nowrap text-sm font-semibold tabular-nums text-slate-900 dark:text-white">
                    {formatCurrency(row.total_revenue)}
                  </p>
                  <p className="text-[11px] text-slate-400 dark:text-slate-500">Doanh thu</p>
                </div>
                <div className="w-16 shrink-0 rounded-xl bg-brand-50 px-2 py-1.5 text-center dark:bg-brand-950/40">
                  <p className="text-sm font-bold tabular-nums text-brand-700 dark:text-brand-300">
                    {formatNumber(row.total_quantity)}
                  </p>
                  <p className="text-[10px] font-medium uppercase tracking-wide text-brand-500/80 dark:text-brand-400/80">
                    SL
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
