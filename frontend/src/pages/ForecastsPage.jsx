import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import Icon from '../components/common/Icon.jsx'
import Spinner from '../components/common/Spinner.jsx'
import SeasonalPanel from '../components/forecasts/SeasonalPanel.jsx'
import api from '../services/api.js'
import { formatDate, formatNumber, getErrorMessage } from '../utils/format.js'

const PAGE_SIZE = 20

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

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs shadow-lg dark:border-slate-700 dark:bg-slate-800">
      <p className="font-semibold text-slate-700 dark:text-slate-200">{label}</p>
      <p className="mt-0.5 text-brand-600 dark:text-brand-400">{formatNumber(payload[0].value)} đơn vị</p>
    </div>
  )
}

export default function ForecastsPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState('latest')
  const [page, setPage] = useState(1)
  const [reloadKey, setReloadKey] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [data, setData] = useState({ items: [], total: 0, pages: 0 })

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    api
      .get('/forecasts/latest', { params: { page, page_size: PAGE_SIZE } })
      .then((res) => {
        if (!cancelled) setData(res.data)
      })
      .catch((err) => {
        if (!cancelled) setError(getErrorMessage(err, 'Không tải được danh sách dự báo.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [page, reloadKey])

  const chartData = useMemo(() => {
    return (data.items || [])
      .slice(0, 10)
      .map((item) => ({
        name: item.product?.product_code || `SP${item.product_id}`,
        value: Number(item.predicted_quantity || 0),
      }))
  }, [data.items])

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
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-2xl">Dự báo nhu cầu</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {tab === 'latest'
              ? 'Dự báo mới nhất theo từng cặp sản phẩm × cửa hàng (mô hình tốt nhất mỗi cặp).'
              : 'Sản phẩm nên nhập nhiều hơn hoặc hạn chế nhập theo từng mùa, tự động làm mới mỗi 5 phút.'}
          </p>
        </div>
        {tab === 'latest' && (
          <button type="button" onClick={() => setReloadKey((k) => k + 1)} className="btn-secondary w-fit">
            <Icon name="refresh" className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Tải lại
          </button>
        )}
      </div>

      <div className="card flex flex-wrap gap-1.5 p-1.5">
        {[
          { key: 'latest', label: 'Dự báo mới nhất', icon: 'forecast' },
          { key: 'seasonal', label: 'Dự báo theo mùa', icon: 'leaf' },
        ].map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setTab(item.key)}
            className={[
              'btn flex-1 justify-center sm:flex-none',
              tab === item.key
                ? 'bg-brand-600 text-white hover:bg-brand-700'
                : 'bg-transparent text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800',
            ].join(' ')}
            aria-pressed={tab === item.key}
          >
            <Icon name={item.icon} className="h-4 w-4" />
            {item.label}
          </button>
        ))}
      </div>

      {tab === 'seasonal' ? (
        <SeasonalPanel />
      ) : (
        <>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="card p-5 xl:col-span-2">
          <div className="mb-4">
            <h2 className="font-semibold text-slate-900 dark:text-white">Top 10 dự báo gần nhất</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">Số lượng dự báo (đơn vị)</p>
          </div>
          <div className="h-64 w-full">
            {chartData.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-slate-400 dark:text-slate-500">
                {loading ? 'Đang tải biểu đồ…' : 'Chưa có dữ liệu'}
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 5, right: 8, left: -18, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.22)" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(16,185,129,0.08)' }} />
                  <Bar dataKey="value" fill="#10b981" radius={[6, 6, 0, 0]} barSize={28} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
        <div className="card p-5">
          <div className="flex items-center gap-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-300">
              <Icon name="forecast" className="h-4 w-4" />
            </span>
            <div>
              <h2 className="font-semibold text-slate-900 dark:text-white">Thông tin mô hình</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">Kết quả huấn luyện trên 100 cặp</p>
            </div>
          </div>
          <div className="mt-4 space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-slate-500 dark:text-slate-400">Mô hình chính</span>
              <span className="font-semibold text-slate-800 dark:text-slate-100">Prophet</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500 dark:text-slate-400">RMSE (test nội bộ)</span>
              <span className="font-semibold text-slate-800 dark:text-slate-100">9,97</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500 dark:text-slate-400">MAE / MAPE</span>
              <span className="font-semibold text-slate-800 dark:text-slate-100">7,94 / 10,43%</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500 dark:text-slate-400">Thắng / 100 cặp</span>
              <span className="font-semibold text-emerald-600 dark:text-emerald-400">97 / 100</span>
            </div>
          </div>
          <p className="mt-4 text-xs text-slate-400 dark:text-slate-500">
            Giá trị `predicted_quantity` là dự báo cho ngày gần nhất; `recommended_import_qty` đã bị giới hạn bởi `max_stock`.
          </p>
        </div>
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
              <table className="w-full min-w-[980px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/70 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-400">
                    <th className="px-4 py-3 font-semibold">Sản phẩm</th>
                    <th className="px-4 py-3 font-semibold">Cửa hàng</th>
                    <th className="px-4 py-3 font-semibold">Mô hình</th>
                    <th className="px-4 py-3 font-semibold">Ngày dự báo</th>
                    <th className="px-4 py-3 text-right font-semibold">Dự báo (đơn vị)</th>
                    <th className="px-4 py-3 text-right font-semibold">Đề xuất nhập</th>
                    <th className="px-4 py-3 text-right font-semibold">Khoảng tin cậy</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {loading ? (
                    <TableSkeleton cols={7} />
                  ) : data.items.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-6 py-16 text-center">
                        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
                          <Icon name="forecast" className="h-6 w-6" />
                        </span>
                        <p className="mt-3 font-semibold text-slate-700 dark:text-slate-200">Chưa có dữ liệu dự báo</p>
                      </td>
                    </tr>
                  ) : (
                    data.items.map((item) => (
                      <tr key={`${item.store_id}-${item.product_id}`} className="transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-800/40">
                        <td className="px-4 py-3.5">
                          <p className="font-medium text-slate-900 dark:text-white">{item.product?.product_name || `SP #${item.product_id}`}</p>
                          <p className="font-mono text-xs text-slate-400 dark:text-slate-500">{item.product?.product_code || ''}</p>
                        </td>
                        <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">{item.store?.store_name || `CH #${item.store_id}`}</td>
                        <td className="px-4 py-3.5">
                          <span className="badge bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">{item.model_name}</span>
                        </td>
                        <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">{formatDate(item.forecast_date)}</td>
                        <td className="px-4 py-3.5 text-right tabular-nums font-medium text-slate-900 dark:text-white">{formatNumber(item.predicted_quantity)}</td>
                        <td className="px-4 py-3.5 text-right tabular-nums text-slate-600 dark:text-slate-300">{item.recommended_import_qty == null ? '—' : formatNumber(item.recommended_import_qty)}</td>
                        <td className="px-4 py-3.5 text-right tabular-nums text-slate-500 dark:text-slate-400">
                          {item.lower_bound == null || item.upper_bound == null ? '—' : `${formatNumber(item.lower_bound)} – ${formatNumber(item.upper_bound)}`}
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
                  Trang {page} / {data.pages} · Tổng {data.total} cặp (sản phẩm × cửa hàng)
                </p>
                <div className="flex items-center gap-2">
                  <button type="button" onClick={() => goToPage(page - 1)} disabled={loading || page <= 1} className="btn-secondary px-3 py-2">
                    <Icon name="chevronLeft" className="h-4 w-4" />
                  </button>
                  <button type="button" onClick={() => goToPage(page + 1)} disabled={loading || page >= data.pages} className="btn-secondary px-3 py-2">
                    <Icon name="chevronRight" className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
        </>
      )}
    </div>
  )
}
