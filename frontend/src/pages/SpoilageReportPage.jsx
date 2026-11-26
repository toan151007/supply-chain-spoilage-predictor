import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import Icon from '../components/common/Icon.jsx'
import Toast from '../components/common/Toast.jsx'
import ReportTabs from '../components/reports/ReportTabs.jsx'
import api from '../services/api.js'
import {
  formatCompactCurrency,
  formatDate,
  formatDateTime,
  formatNumber,
  getErrorMessage,
} from '../utils/format.js'

const PERIODS = [
  { value: 0, label: 'Hôm nay' },
  { value: 7, label: '7 ngày' },
  { value: 30, label: '30 ngày' },
]

const pad2 = (value) => String(value).padStart(2, '0')

/* Prefer the filename the API chose; fall back to the same convention when a
   proxy strips Content-Disposition. */
function exportFileName(response, format) {
  const disposition =
    response?.headers?.['content-disposition'] ||
    response?.headers?.['Content-Disposition'] ||
    ''
  const match = /filename="?([^";]+)"?/i.exec(disposition)
  if (match) return match[1]

  const now = new Date()
  const stamp = `${now.getFullYear()}${pad2(now.getMonth() + 1)}${pad2(
    now.getDate(),
  )}_${pad2(now.getHours())}${pad2(now.getMinutes())}`
  return `Bao_Cao_Hao_Hut_${stamp}.${format}`
}

/* With responseType:'blob' an error body is still a Blob, so getErrorMessage
   cannot see the JSON detail without reading it first. */
async function readBlobError(error) {
  const data = error?.response?.data
  if (!data || typeof data.text !== 'function') return ''
  try {
    const text = await data.text()
    if (!text) return ''
    try {
      const parsed = JSON.parse(text)
      if (parsed?.detail) {
        return typeof parsed.detail === 'string'
          ? parsed.detail
          : JSON.stringify(parsed.detail)
      }
    } catch {
      /* Body is plain text, use it as-is. */
    }
    return text
  } catch {
    return ''
  }
}

const RISK_META = {
  high: {
    label: 'Nguy cơ cao',
    badge: 'bg-red-50 text-red-700 dark:bg-red-950/50 dark:text-red-300',
    dot: 'bg-red-500',
    text: 'text-red-600 dark:text-red-400',
  },
  warning: {
    label: 'Cảnh báo',
    badge: 'bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300',
    dot: 'bg-amber-500',
    text: 'text-amber-600 dark:text-amber-400',
  },
  safe: {
    label: 'An toàn',
    badge: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300',
    dot: 'bg-emerald-500',
    text: 'text-emerald-600 dark:text-emerald-400',
  },
}

const ACTION_META = {
  promotion: { label: 'Khuyến mãi', icon: 'sparkles' },
  transfer: { label: 'Điều chuyển', icon: 'transfer' },
  inventory_check: { label: 'Kiểm kê', icon: 'inventory' },
}

const DEMAND_SOURCE_LABEL = {
  forecast: 'Dự báo Prophet',
  sales: 'Bán thực tế 30 ngày',
  none: 'Chưa có dữ liệu bán',
}

const PAGE_SIZE = 15

function daysLeftLabel(days) {
  if (days < 0) return `Hết hạn ${Math.abs(days)} ngày`
  if (days === 0) return 'Hết hạn hôm nay'
  return `Còn ${days} ngày`
}

function RiskBadge({ level, score }) {
  const meta = RISK_META[level] ?? RISK_META.safe
  return (
    <span
      title={meta.label}
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold tabular-nums ${meta.badge}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} aria-hidden="true" />
      {formatNumber(score)}
    </span>
  )
}

function KpiCard({ icon, tone, label, value, hint }) {
  return (
    <div className="card p-5">
      <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${tone}`}>
        <Icon name={icon} className="h-5 w-5" />
      </div>
      <p className="mt-4 whitespace-nowrap text-2xl font-bold tracking-tight tabular-nums text-slate-900 dark:text-white">
        {value}
      </p>
      <p className="mt-1 text-sm font-medium text-slate-600 dark:text-slate-300">{label}</p>
      <p className="mt-0.5 text-xs text-slate-400 dark:text-slate-500">{hint}</p>
    </div>
  )
}

function TableSkeleton() {
  return (
    <>
      {Array.from({ length: 6 }).map((_, row) => (
        <tr key={row} className="animate-pulse">
          {Array.from({ length: 8 }).map((__, col) => (
            <td key={col} className="px-4 py-4">
              <div className="h-3 rounded bg-slate-100 dark:bg-slate-800" />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}

function AdviceSkeleton() {
  return (
    <div className="space-y-2.5 animate-pulse">
      {[100, 92, 84, 96, 70].map((width, index) => (
        <div
          key={index}
          className="h-3 rounded bg-slate-100 dark:bg-slate-800"
          style={{ width: `${width}%` }}
        />
      ))}
    </div>
  )
}

export default function SpoilageReportPage() {
  const navigate = useNavigate()

  const [period, setPeriod] = useState(30)
  const [categoryId, setCategoryId] = useState('')
  const [storeId, setStoreId] = useState('')
  const [riskLevel, setRiskLevel] = useState('')

  const [categories, setCategories] = useState([])
  const [stores, setStores] = useState([])

  const [summary, setSummary] = useState(null)
  const [rows, setRows] = useState([])
  const [advice, setAdvice] = useState(null)
  const [adviceError, setAdviceError] = useState('')

  const [loading, setLoading] = useState(true)
  const [adviceLoading, setAdviceLoading] = useState(true)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)
  const [exporting, setExporting] = useState(null)
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState(null)
  const [actionNotice, setActionNotice] = useState('')
  const [toast, setToast] = useState(null)

  /* Category and store lists are reference data; load them once. */
  useEffect(() => {
    let cancelled = false
    Promise.all([
      api.get('/categories', { params: { page_size: 100 } }),
      api.get('/stores', { params: { page_size: 100 } }),
    ])
      .then(([categoryResponse, storeResponse]) => {
        if (cancelled) return
        setCategories(categoryResponse.data.items || [])
        setStores(storeResponse.data.items || [])
      })
      .catch(() => {
        /* Filters still work without the option lists. */
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    setPage(1)
  }, [period, categoryId, storeId, riskLevel])

  const scopeParams = useMemo(
    () => ({
      days: period,
      category_id: categoryId || undefined,
      store_id: storeId || undefined,
    }),
    [period, categoryId, storeId],
  )

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')

    Promise.all([
      api.get('/reports/spoilage/summary', { params: scopeParams }),
      api.get('/reports/spoilage', {
        params: { ...scopeParams, risk_level: riskLevel || undefined, limit: 500 },
      }),
    ])
      .then(([summaryResponse, rowsResponse]) => {
        if (cancelled) return
        setSummary(summaryResponse.data)
        setRows(rowsResponse.data || [])
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(getErrorMessage(requestError, 'Không tải được báo cáo rủi ro hao hụt.'))
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [scopeParams, riskLevel, reloadKey])

  /* Gemini can take a few seconds; keep it out of the main loading state. */
  useEffect(() => {
    let cancelled = false
    setAdviceLoading(true)
    setAdviceError('')

    api
      .get('/reports/spoilage/advice', { params: scopeParams })
      .then((response) => {
        if (!cancelled) setAdvice(response.data)
      })
      .catch((requestError) => {
        if (!cancelled) {
          setAdvice(null)
          setAdviceError(
            getErrorMessage(requestError, 'Không tải được phần tóm tắt và khuyến nghị.'),
          )
        }
      })
      .finally(() => {
        if (!cancelled) setAdviceLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [scopeParams, reloadKey])

  useEffect(() => {
    if (!selected) return undefined
    const handleKey = (event) => {
      if (event.key === 'Escape') setSelected(null)
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [selected])

  const kpi = summary?.kpi ?? {
    total_stock_qty: 0,
    total_stock_value: 0,
    at_risk_qty: 0,
    at_risk_value: 0,
    spoilage_rate: 0,
    lots_in_window: 0,
    lots_to_handle: 0,
    expired_lots: 0,
    high_risk_lots: 0,
    window_days: period,
  }

  const categoryData = useMemo(
    () =>
      (summary?.categories || []).map((item) => ({
        name: item.category_name || 'Khác',
        safe: item.safe_count,
        warning: item.warning_count,
        high: item.high_count,
      })),
    [summary],
  )

  const trendData = useMemo(
    () =>
      (summary?.trend || []).map((item) => ({
        label: formatDate(item.trend_date),
        loss: Math.round((item.loss_value / 1_000_000) * 100) / 100,
        handled: item.handled_rate,
      })),
    [summary],
  )

  const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const pageRows = rows.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  const handleExport = async (format) => {
    setExporting(format)
    try {
      const response = await api.get('/reports/spoilage/export', {
        params: { ...scopeParams, risk_level: riskLevel || undefined, format },
        responseType: 'blob',
      })
      const fileName = exportFileName(response, format)
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', fileName)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)

      const headerTotal = Number(response.headers?.['x-total-rows'])
      const rowCount =
        Number.isFinite(headerTotal) && headerTotal > 0
          ? headerTotal
          : rows.length
      setToast({
        type: 'success',
        message: `Đã tải báo cáo ${format.toUpperCase()} với ${formatNumber(
          rowCount,
        )} lô hàng.`,
      })
    } catch (requestError) {
      const detail = await readBlobError(requestError)
      const status = requestError?.response?.status
      /* The permission dependency answers in English, so a 403 always shows
         the Vietnamese message instead of the raw API detail. */
      const message =
        status === 403
          ? 'Bạn không có quyền xuất báo cáo. Vui lòng liên hệ quản trị viên.'
          : detail ||
            getErrorMessage(
              requestError,
              'Không xuất được báo cáo. Vui lòng thử lại.',
            )
      setToast({ type: 'error', message })
    } finally {
      setExporting(null)
    }
  }

  const openDrawer = (row) => {
    setSelected(row)
    setActionNotice('')
  }

  const handlePromotion = () => {
    if (!selected) return
    const discount =
      selected.days_left <= 2 ? 50 : selected.days_left <= 7 ? 30 : 15
    const batch = selected.batch_code || `#${selected.inventory_id}`
    setActionNotice(
      `Kế hoạch khuyến mãi: giảm ${discount}% cho lô ${batch} (${formatNumber(
        selected.quantity,
      )} ${selected.unit || 'sản phẩm'}) để bán hết trước hạn.`,
    )
    setToast({
      type: 'success',
      message: `Đã tạo kế hoạch khuyến mãi ${discount}% cho lô ${batch}.`,
    })
  }

  return (
    <div className="space-y-5 animate-fade-in">
      <Toast
        type={toast?.type}
        message={toast?.message}
        onClose={() => setToast(null)}
      />

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

      <ReportTabs />

      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-2xl">
            Báo cáo Hàng hóa &amp; Rủi ro Hao hụt
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Đối chiếu hạn sử dụng, tồn kho thật và tốc độ bán dự kiến để biết lô nào
            sắp hỏng và thiệt hại ước tính.
          </p>
        </div>
        {summary?.generated_at && (
          <p className="flex items-center gap-1.5 text-xs text-slate-400 dark:text-slate-500">
            <Icon name="clock" className="h-3.5 w-3.5" />
            Cập nhật {formatDateTime(summary.generated_at)}
          </p>
        )}
      </div>

      {/* Filters + actions */}
      <div className="card p-4">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            {PERIODS.map((item) => {
              const active = period === item.value
              return (
                <button
                  key={item.value}
                  type="button"
                  onClick={() => setPeriod(item.value)}
                  aria-pressed={active}
                  className={[
                    'rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors',
                    active
                      ? 'bg-brand-600 text-white shadow-sm'
                      : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700',
                  ].join(' ')}
                >
                  {item.label}
                </button>
              )
            })}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={categoryId}
              onChange={(event) => setCategoryId(event.target.value)}
              className="input w-auto min-w-[150px]"
              aria-label="Lọc theo danh mục"
            >
              <option value="">Tất cả danh mục</option>
              {categories.map((category) => (
                <option key={category.category_id} value={category.category_id}>
                  {category.category_name}
                </option>
              ))}
            </select>

            <select
              value={storeId}
              onChange={(event) => setStoreId(event.target.value)}
              className="input w-auto min-w-[170px]"
              aria-label="Lọc theo chi nhánh"
            >
              <option value="">Tất cả chi nhánh</option>
              {stores.map((store) => (
                <option key={store.store_id} value={store.store_id}>
                  {store.store_name}
                </option>
              ))}
            </select>

            <select
              value={riskLevel}
              onChange={(event) => setRiskLevel(event.target.value)}
              className="input w-auto min-w-[150px]"
              aria-label="Lọc theo mức độ rủi ro"
            >
              <option value="">Tất cả rủi ro</option>
              <option value="high">Nguy cơ cao</option>
              <option value="warning">Cảnh báo</option>
              <option value="safe">An toàn</option>
            </select>

            <button
              type="button"
              onClick={() => setReloadKey((key) => key + 1)}
              className="btn-secondary px-3"
              aria-label="Làm mới báo cáo"
            >
              <Icon name="refresh" className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Làm mới</span>
            </button>

            <button
              type="button"
              onClick={() => handleExport('xlsx')}
              disabled={exporting !== null || rows.length === 0}
              className="btn-secondary px-3"
            >
              <Icon name="arrowDown" className="h-4 w-4" />
              {exporting === 'xlsx' ? 'Đang xuất…' : 'Xuất Excel'}
            </button>

            <button
              type="button"
              onClick={() => handleExport('pdf')}
              disabled={exporting !== null || rows.length === 0}
              className="btn-secondary px-3"
            >
              <Icon name="reports" className="h-4 w-4" />
              {exporting === 'pdf' ? 'Đang xuất…' : 'Xuất PDF'}
            </button>
          </div>
        </div>
      </div>

      {error ? (
        <div className="card flex flex-col items-center gap-3 px-6 py-16 text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-red-50 text-red-600 dark:bg-red-950/50 dark:text-red-400">
            <Icon name="warning" className="h-6 w-6" />
          </span>
          <div>
            <p className="font-semibold text-slate-900 dark:text-white">Không tải được dữ liệu</p>
            <p className="mt-1 max-w-md text-sm text-slate-500 dark:text-slate-400">{error}</p>
          </div>
          <button
            type="button"
            onClick={() => setReloadKey((key) => key + 1)}
            className="btn-secondary mt-1"
          >
            <Icon name="refresh" className="h-4 w-4" />
            Thử lại
          </button>
        </div>
      ) : (
        <>
          {/* KPI cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard
              icon="inventory"
              tone="bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-300"
              label="Tổng tồn kho"
              value={`${formatNumber(kpi.total_stock_qty)} đơn vị`}
              hint={`Trị giá ${formatCompactCurrency(kpi.total_stock_value)}`}
            />
            <KpiCard
              icon="warning"
              tone="bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-300"
              label="Giá trị nguy cơ hao hụt"
              value={formatCompactCurrency(kpi.at_risk_value)}
              hint={`${formatNumber(kpi.at_risk_qty)} đơn vị có thể không bán được`}
            />
            <KpiCard
              icon="chart"
              tone="bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300"
              label="Tỷ lệ hao hụt"
              value={`${formatNumber(kpi.spoilage_rate)}%`}
              hint={`Trong ${formatNumber(kpi.lots_in_window)} lô thuộc khung ${kpi.window_days} ngày`}
            />
            <KpiCard
              icon="clock"
              tone="bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
              label="Số lô cần xử lý"
              value={`${formatNumber(kpi.lots_to_handle)} lô`}
              hint={`${formatNumber(kpi.expired_lots)} lô đã hết hạn · ${formatNumber(kpi.high_risk_lots)} lô nguy cơ cao`}
            />
          </div>

          {/* Charts + AI panel */}
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <div className="card p-5 xl:col-span-2">
              <div className="mb-4">
                <h2 className="font-semibold text-slate-900 dark:text-white">
                  Phân loại rủi ro theo danh mục
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Số lô an toàn / cảnh báo / nguy cơ cao trong khung {kpi.window_days} ngày
                </p>
              </div>
              <div className="h-72 w-full">
                {loading && categoryData.length === 0 ? (
                  <div className="h-full animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />
                ) : categoryData.length === 0 ? (
                  <div className="flex h-full items-center justify-center text-sm text-slate-400 dark:text-slate-500">
                    Không có lô hàng trong khung thời gian này.
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={categoryData} margin={{ top: 5, right: 8, left: -18, bottom: 0 }}>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="rgba(148,163,184,0.22)"
                        vertical={false}
                      />
                      <XAxis
                        dataKey="name"
                        tick={{ fontSize: 11, fill: '#94a3b8' }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        allowDecimals={false}
                        tick={{ fontSize: 11, fill: '#94a3b8' }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip
                        cursor={{ fill: 'rgba(148,163,184,0.12)' }}
                        formatter={(value, name) => [
                          `${formatNumber(value)} lô`,
                          name,
                        ]}
                      />
                      <Legend wrapperStyle={{ fontSize: 12 }} />
                      <Bar dataKey="safe" name="An toàn" stackId="risk" fill="#10b981" radius={[0, 0, 0, 0]} />
                      <Bar dataKey="warning" name="Cảnh báo" stackId="risk" fill="#f59e0b" />
                      <Bar dataKey="high" name="Nguy cơ cao" stackId="risk" fill="#ef4444" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>

            <div className="card flex flex-col p-5">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-start gap-2.5">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-300">
                    <Icon name="sparkles" className="h-4 w-4" />
                  </span>
                  <div>
                    <h2 className="font-semibold text-slate-900 dark:text-white">
                      Tóm tắt &amp; Khuyến nghị thông minh
                    </h2>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Phân tích từ tồn kho, hạn dùng và tốc độ bán
                    </p>
                  </div>
                </div>
                <span className="badge bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {advice?.model && advice.model !== 'fallback' ? 'Gemini' : 'Quy tắc'}
                </span>
              </div>

              <div className="mt-4 flex-1 overflow-y-auto">
                {adviceLoading ? (
                  <AdviceSkeleton />
                ) : adviceError ? (
                  <p className="text-sm text-slate-500 dark:text-slate-400">{adviceError}</p>
                ) : (
                  <p className="whitespace-pre-line text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                    {advice?.answer || 'Chưa có khuyến nghị cho bộ lọc hiện tại.'}
                  </p>
                )}
              </div>

              <p className="mt-3 border-t border-slate-100 pt-3 text-[11px] text-slate-400 dark:border-slate-800 dark:text-slate-500">
                Tốc độ bán ưu tiên dự báo Prophet; sản phẩm chưa có dự báo dùng
                tốc độ bán thực tế 30 ngày.
              </p>
            </div>
          </div>

          <div className="card p-5">
            <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
              <div>
                <h2 className="font-semibold text-slate-900 dark:text-white">
                  Xu hướng hao hụt &amp; tỷ lệ xử lý thành công
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Theo ngày hết hạn · giá trị thất thoát (triệu đ) và tỷ lệ hàng bán được (%)
                </p>
              </div>
            </div>
            <div className="h-72 w-full">
              {loading && trendData.length === 0 ? (
                <div className="h-full animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />
              ) : trendData.length === 0 ? (
                <div className="flex h-full items-center justify-center text-sm text-slate-400 dark:text-slate-500">
                  Không có dữ liệu xu hướng trong khung thời gian này.
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendData} margin={{ top: 5, right: 8, left: -18, bottom: 0 }}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(148,163,184,0.22)"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="label"
                      tick={{ fontSize: 11, fill: '#94a3b8' }}
                      axisLine={false}
                      tickLine={false}
                      minTickGap={18}
                    />
                    <YAxis
                      yAxisId="left"
                      tick={{ fontSize: 11, fill: '#94a3b8' }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      domain={[0, 100]}
                      tick={{ fontSize: 11, fill: '#94a3b8' }}
                      axisLine={false}
                      tickLine={false}
                      unit="%"
                    />
                    <Tooltip
                      formatter={(value, name) =>
                        name === 'Tỷ lệ xử lý'
                          ? [`${formatNumber(value)}%`, name]
                          : [`${formatNumber(value)} triệu đ`, name]
                      }
                    />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Line
                      yAxisId="left"
                      type="monotone"
                      dataKey="loss"
                      name="Giá trị thất thoát"
                      stroke="#ef4444"
                      strokeWidth={2.5}
                      dot={{ r: 2.5 }}
                      activeDot={{ r: 4 }}
                    />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="handled"
                      name="Tỷ lệ xử lý"
                      stroke="#2a5aaa"
                      strokeWidth={2.5}
                      dot={{ r: 2.5 }}
                      activeDot={{ r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Detail table */}
          <div className="card overflow-hidden">
            <div className="flex flex-col gap-1 border-b border-slate-200 px-4 py-3 dark:border-slate-800 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="font-semibold text-slate-900 dark:text-white">Chi tiết lô hàng</h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {formatNumber(rows.length)} lô · xếp theo điểm rủi ro giảm dần
                </p>
              </div>
              <span className="badge bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                Khung {kpi.window_days} ngày
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[980px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/70 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-400">
                    <th className="px-4 py-3 font-semibold">Mã lô / Tên hàng</th>
                    <th className="px-4 py-3 font-semibold">Danh mục</th>
                    <th className="px-4 py-3 text-right font-semibold">Tồn kho</th>
                    <th className="px-4 py-3 font-semibold">Hạn sử dụng</th>
                    <th className="px-4 py-3 text-right font-semibold">Tốc độ bán</th>
                    <th className="px-4 py-3 font-semibold">Risk Score</th>
                    <th className="px-4 py-3 text-right font-semibold">Thất thoát</th>
                    <th className="px-4 py-3 text-right font-semibold">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {loading ? (
                    <TableSkeleton />
                  ) : rows.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-6 py-16 text-center">
                        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400">
                          <Icon name="shield" className="h-6 w-6" />
                        </span>
                        <p className="mt-3 font-semibold text-slate-700 dark:text-slate-200">
                          Không có lô hàng nào trong bộ lọc này
                        </p>
                        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                          Thử mở rộng khung thời gian hoặc bỏ bớt bộ lọc.
                        </p>
                      </td>
                    </tr>
                  ) : (
                    pageRows.map((row) => {
                      const risk = RISK_META[row.risk_level] ?? RISK_META.safe
                      return (
                        <tr
                          key={row.inventory_id}
                          className="transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-800/40"
                        >
                          <td className="px-4 py-3.5">
                            <p className="font-medium text-slate-900 dark:text-white">
                              {row.product_name}
                            </p>
                            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                              {row.batch_code || `Lô #${row.inventory_id}`} · {row.store_name}
                            </p>
                          </td>
                          <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">
                            {row.category_name || '—'}
                          </td>
                          <td className="px-4 py-3.5 text-right tabular-nums text-slate-700 dark:text-slate-200">
                            {formatNumber(row.quantity)}{' '}
                            <span className="text-xs text-slate-400 dark:text-slate-500">
                              {row.unit || ''}
                            </span>
                          </td>
                          <td className="px-4 py-3.5">
                            <p className="text-slate-700 dark:text-slate-200">
                              {formatDate(row.expiry_date)}
                            </p>
                            <p className={`mt-0.5 text-xs font-medium ${risk.text}`}>
                              {daysLeftLabel(row.days_left)}
                            </p>
                          </td>
                          <td className="px-4 py-3.5 text-right">
                            <p className="tabular-nums text-slate-700 dark:text-slate-200">
                              {formatNumber(row.daily_demand)} / ngày
                            </p>
                            <p className="mt-0.5 text-xs text-slate-400 dark:text-slate-500">
                              {DEMAND_SOURCE_LABEL[row.demand_source] || row.demand_source}
                            </p>
                          </td>
                          <td className="px-4 py-3.5">
                            <RiskBadge level={row.risk_level} score={row.risk_score} />
                            <p className={`mt-1 text-xs font-medium ${risk.text}`}>{risk.label}</p>
                          </td>
                          <td className="px-4 py-3.5 text-right tabular-nums font-medium text-slate-800 dark:text-slate-100">
                            {formatCompactCurrency(row.loss_value)}
                          </td>
                          <td className="px-4 py-3.5 text-right">
                            <button
                              type="button"
                              onClick={() => openDrawer(row)}
                              className="btn-secondary px-3 py-1.5"
                            >
                              <Icon name="pencil" className="h-3.5 w-3.5" />
                              Xử lý
                            </button>
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>

            {rows.length > 0 && (
              <div className="flex flex-col items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 dark:border-slate-800 sm:flex-row">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Trang {currentPage} / {totalPages} · {formatNumber(rows.length)} lô
                </p>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setPage((value) => Math.max(1, value - 1))}
                    disabled={loading || currentPage <= 1}
                    className="btn-secondary px-3 py-2"
                    aria-label="Trang trước"
                  >
                    <Icon name="chevronLeft" className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
                    disabled={loading || currentPage >= totalPages}
                    className="btn-secondary px-3 py-2"
                    aria-label="Trang sau"
                  >
                    <Icon name="chevronRight" className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* Detail drawer */}
      {selected && (
        <div className="fixed inset-0 z-[70] flex justify-end">
          <button
            type="button"
            aria-label="Đóng chi tiết"
            onClick={() => setSelected(null)}
            className="absolute inset-0 bg-slate-950/50 backdrop-blur-sm"
          />
          <aside
            role="dialog"
            aria-modal="true"
            aria-label="Chi tiết lô hàng"
            className="relative flex h-full w-full max-w-md flex-col overflow-y-auto bg-white shadow-2xl dark:bg-slate-900"
          >
            <div className="sticky top-0 z-10 flex items-start justify-between gap-3 border-b border-slate-200 bg-white px-5 py-4 dark:border-slate-800 dark:bg-slate-900">
              <div className="min-w-0">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-400 dark:text-slate-500">
                  {selected.batch_code || `Lô #${selected.inventory_id}`}
                </p>
                <h2 className="mt-0.5 truncate text-lg font-bold text-slate-900 dark:text-white">
                  {selected.product_name}
                </h2>
                <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">
                  {selected.store_name} · {selected.category_name || 'Chưa phân nhóm'}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelected(null)}
                className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                aria-label="Đóng"
              >
                <Icon name="close" className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 space-y-4 px-5 py-5">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
                    (RISK_META[selected.risk_level] ?? RISK_META.safe).badge
                  }`}
                >
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${
                      (RISK_META[selected.risk_level] ?? RISK_META.safe).dot
                    }`}
                  />
                  {(RISK_META[selected.risk_level] ?? RISK_META.safe).label}
                </span>
                <span className="badge bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  Điểm rủi ro {formatNumber(selected.risk_score)}
                </span>
                <span className="badge bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {daysLeftLabel(selected.days_left)}
                </span>
              </div>

              <p className="rounded-xl bg-slate-50 px-3.5 py-3 text-sm leading-relaxed text-slate-600 dark:bg-slate-800/60 dark:text-slate-300">
                {selected.reason}
              </p>

              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="rounded-xl border border-slate-200 px-3 py-2.5 dark:border-slate-800">
                  <p className="text-xs text-slate-400 dark:text-slate-500">Tồn kho</p>
                  <p className="mt-0.5 font-semibold tabular-nums text-slate-800 dark:text-slate-100">
                    {formatNumber(selected.quantity)} {selected.unit || ''}
                  </p>
                </div>
                <div className="rounded-xl border border-slate-200 px-3 py-2.5 dark:border-slate-800">
                  <p className="text-xs text-slate-400 dark:text-slate-500">Giá trị tồn</p>
                  <p className="mt-0.5 font-semibold tabular-nums text-slate-800 dark:text-slate-100">
                    {formatCompactCurrency(selected.stock_value)}
                  </p>
                </div>
                <div className="rounded-xl border border-slate-200 px-3 py-2.5 dark:border-slate-800">
                  <p className="text-xs text-slate-400 dark:text-slate-500">Hạn sử dụng</p>
                  <p className="mt-0.5 font-semibold text-slate-800 dark:text-slate-100">
                    {formatDate(selected.expiry_date)}
                  </p>
                </div>
                <div className="rounded-xl border border-slate-200 px-3 py-2.5 dark:border-slate-800">
                  <p className="text-xs text-slate-400 dark:text-slate-500">Tốc độ bán</p>
                  <p className="mt-0.5 font-semibold tabular-nums text-slate-800 dark:text-slate-100">
                    {formatNumber(selected.daily_demand)} / ngày
                  </p>
                </div>
                <div className="rounded-xl border border-slate-200 px-3 py-2.5 dark:border-slate-800">
                  <p className="text-xs text-slate-400 dark:text-slate-500">Dự kiến bán được</p>
                  <p className="mt-0.5 font-semibold tabular-nums text-slate-800 dark:text-slate-100">
                    {formatNumber(selected.sellable_qty)} {selected.unit || ''}
                  </p>
                </div>
                <div className="rounded-xl border border-slate-200 px-3 py-2.5 dark:border-slate-800">
                  <p className="text-xs text-slate-400 dark:text-slate-500">Thất thoát ước tính</p>
                  <p className="mt-0.5 font-semibold tabular-nums text-red-600 dark:text-red-400">
                    {formatCompactCurrency(selected.loss_value)}
                  </p>
                </div>
              </div>

              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-slate-400 dark:text-slate-500">
                  Nguồn tốc độ bán
                </p>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                  {DEMAND_SOURCE_LABEL[selected.demand_source] || selected.demand_source}
                  {selected.demand_source === 'sales' && (
                    <span className="text-slate-400 dark:text-slate-500">
                      {' '}
                      — sản phẩm chưa có dự báo Prophet
                    </span>
                  )}
                </p>
              </div>

              {actionNotice && (
                <div className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-2.5 text-sm text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-200">
                  <Icon name="check" className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{actionNotice}</span>
                </div>
              )}
            </div>

            <div className="sticky bottom-0 border-t border-slate-200 bg-white px-5 py-4 dark:border-slate-800 dark:bg-slate-900">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400 dark:text-slate-500">
                Thao tác xử lý
              </p>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                <button type="button" onClick={handlePromotion} className="btn-primary justify-center">
                  <Icon name="sparkles" className="h-4 w-4" />
                  Khuyến mãi
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/transfers')}
                  className="btn-secondary justify-center"
                >
                  <Icon name="transfer" className="h-4 w-4" />
                  Điều chuyển
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/inventory')}
                  className="btn-secondary justify-center"
                >
                  <Icon name="inventory" className="h-4 w-4" />
                  Kiểm kê
                </button>
              </div>
              <p className="mt-2 text-[11px] text-slate-400 dark:text-slate-500">
                Gợi ý xử lý của hệ thống:{' '}
                {(ACTION_META[selected.recommended_action] ?? ACTION_META.promotion).label}.
              </p>
            </div>
          </aside>
        </div>
      )}
    </div>
  )
}
