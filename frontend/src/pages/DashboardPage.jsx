import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import Icon from '../components/common/Icon.jsx'
import { useAuth } from '../contexts/AuthContext.jsx'
import { formatCompactCurrency } from '../utils/format.js'

/* ------------------------------------------------------------------ */
/* Static mockup data. The dashboard is wired to the real API in a     */
/* later step; the numbers below only exist to shape the interface.    */
/* ------------------------------------------------------------------ */

const REVENUE_BY_MONTH = [
  { month: 'T1', revenue: 820 },
  { month: 'T2', revenue: 905 },
  { month: 'T3', revenue: 1010 },
  { month: 'T4', revenue: 980 },
  { month: 'T5', revenue: 1075 },
  { month: 'T6', revenue: 1160 },
  { month: 'T7', revenue: 1240 },
  { month: 'T8', revenue: 1195 },
  { month: 'T9', revenue: 1280 },
  { month: 'T10', revenue: 1345 },
  { month: 'T11', revenue: 1410 },
  { month: 'T12', revenue: 1520 },
]

const TOP_PRODUCTS = [
  { name: 'Cà phê sữa', revenue: 148 },
  { name: 'Kẹo mút', revenue: 132 },
  { name: 'Sữa chua', revenue: 118 },
  { name: 'Nước suối', revenue: 104 },
  { name: 'Khăn ướt', revenue: 96 },
]

const KPIS = [
  {
    label: 'Doanh thu 30 ngày',
    value: '1,42 tỷ đ',
    change: '+12,4%',
    positive: true,
    hint: 'so với 30 ngày trước',
    icon: 'reports',
    tone: 'brand',
  },
  {
    label: 'Giá trị tồn kho',
    value: '842 triệu đ',
    change: '+3,1%',
    positive: true,
    hint: '1.330 lô hàng đang theo dõi',
    icon: 'inventory',
    tone: 'sky',
  },
  {
    label: 'Lô sắp hết hạn',
    value: '37 lô',
    change: '−8 lô',
    positive: true,
    hint: 'trong vòng 7 ngày tới',
    icon: 'clock',
    tone: 'amber',
  },
  {
    label: 'Tỷ lệ lãng phí',
    value: '2,8%',
    change: '−0,6 điểm %',
    positive: true,
    hint: 'mục tiêu dưới 3,0%',
    icon: 'leaf',
    tone: 'rose',
  },
]

const ALERTS = [
  {
    id: 1,
    level: 'high',
    title: '18 lô sữa chua còn dưới 3 ngày',
    time: '12 phút trước',
    store: 'Cửa hàng Quận 1',
  },
  {
    id: 2,
    level: 'medium',
    title: 'Nước suối 330ml dưới điểm đặt hàng',
    time: '1 giờ trước',
    store: 'Cửa hàng Thủ Đức',
  },
  {
    id: 3,
    level: 'low',
    title: 'Dự báo tuần tới tăng 9% so với tuần này',
    time: '3 giờ trước',
    store: 'Toàn hệ thống',
  },
]

const EXPIRING_BATCHES = [
  { product: 'Sữa chua 500g', batch: 'SC-2401', store: 'Quận 1', days: 2, quantity: 180 },
  { product: 'Thịt bò', batch: 'TB-1187', store: 'Quận 3', days: 3, quantity: 64 },
  { product: 'Kem đánh răng', batch: 'KR-0922', store: 'Thủ Đức', days: 5, quantity: 210 },
  { product: 'Cà phê sữa', batch: 'CF-3310', store: 'Bình Thạnh', days: 6, quantity: 96 },
]

const TONES = {
  brand: {
    icon: 'bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-300',
    bar: 'bg-brand-500',
  },
  sky: {
    icon: 'bg-sky-100 text-sky-700 dark:bg-sky-900/50 dark:text-sky-300',
    bar: 'bg-sky-500',
  },
  amber: {
    icon: 'bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300',
    bar: 'bg-amber-500',
  },
  rose: {
    icon: 'bg-rose-100 text-rose-700 dark:bg-rose-900/50 dark:text-rose-300',
    bar: 'bg-rose-500',
  },
}

const ALERT_STYLES = {
  high: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300',
  medium: 'bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300',
  low: 'bg-sky-100 text-sky-700 dark:bg-sky-900/50 dark:text-sky-300',
}

const BAR_COLORS = ['#059669', '#10b981', '#34d399', '#6ee7b7', '#a7f3d0']

function ChartTooltip({ active, payload, label, unit = '' }) {
  if (!active || !payload?.length) return null

  return (
    <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs shadow-lg dark:border-slate-700 dark:bg-slate-800">
      <p className="font-semibold text-slate-700 dark:text-slate-200">{label}</p>
      <p className="mt-0.5 text-brand-600 dark:text-brand-400">
        {payload[0].value}
        {unit}
      </p>
    </div>
  )
}

function KpiCard({ kpi }) {
  const tone = TONES[kpi.tone]
  const isIncrease = kpi.change.startsWith('+')

  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-3">
        <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${tone.icon}`}>
          <Icon name={kpi.icon} className="h-5 w-5" />
        </div>
        <span
          className={[
            'badge',
            kpi.positive
              ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
              : 'bg-red-50 text-red-700 dark:bg-red-900/40 dark:text-red-300',
          ].join(' ')}
        >
          <Icon name={isIncrease ? 'arrowUp' : 'arrowDown'} className="h-3 w-3" />
          {kpi.change}
        </span>
      </div>
      <p className="mt-4 text-2xl font-bold tracking-tight text-slate-900 dark:text-white">{kpi.value}</p>
      <p className="mt-1 text-sm font-medium text-slate-600 dark:text-slate-300">{kpi.label}</p>
      <p className="mt-0.5 text-xs text-slate-400 dark:text-slate-500">{kpi.hint}</p>
    </div>
  )
}

export default function DashboardPage() {
  const { user } = useAuth()
  const displayName = user?.full_name || user?.username || 'bạn'

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page heading */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-2xl">
            Xin chào, {displayName} 👋
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Đây là tình hình chuỗi cung ứng trong 30 ngày gần nhất.
          </p>
        </div>
        <span className="badge w-fit bg-amber-50 text-amber-700 ring-1 ring-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:ring-amber-800/60">
          <Icon name="info" className="h-3.5 w-3.5" />
          Số liệu minh hoạ giao diện
        </span>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {KPIS.map((kpi) => (
          <KpiCard key={kpi.label} kpi={kpi} />
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="card p-5 xl:col-span-2">
          <div className="mb-5 flex items-start justify-between gap-3">
            <div>
              <h2 className="font-semibold text-slate-900 dark:text-white">Doanh thu theo tháng</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">Đơn vị: triệu đồng</p>
            </div>
            <span className="badge bg-emerald-50 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">
              <Icon name="arrowUp" className="h-3 w-3" />
              +18,6% so với năm trước
            </span>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={REVENUE_BY_MONTH} margin={{ top: 5, right: 8, left: -18, bottom: 0 }}>
                <defs>
                  <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10b981" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#10b981" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.22)" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTooltip unit=" triệu đ" />} cursor={{ stroke: '#10b981', strokeDasharray: '4 4' }} />
                <Area
                  type="monotone"
                  dataKey="revenue"
                  stroke="#059669"
                  strokeWidth={2.5}
                  fill="url(#revenueGradient)"
                  activeDot={{ r: 4, strokeWidth: 2, stroke: '#fff' }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card p-5">
          <div className="mb-5">
            <h2 className="font-semibold text-slate-900 dark:text-white">Top sản phẩm</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">Doanh thu tháng này · triệu đồng</p>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={TOP_PRODUCTS} layout="vertical" margin={{ top: 0, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.22)" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={82}
                  tick={{ fontSize: 11, fill: '#94a3b8' }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip content={<ChartTooltip unit=" triệu đ" />} cursor={{ fill: 'rgba(148,163,184,0.12)' }} />
                <Bar dataKey="revenue" radius={[0, 6, 6, 0]} barSize={16}>
                  {TOP_PRODUCTS.map((entry, index) => (
                    <Cell key={entry.name} fill={BAR_COLORS[index % BAR_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Bottom widgets */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="card p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold text-slate-900 dark:text-white">Cảnh báo gần đây</h2>
            <span className="badge bg-red-50 text-red-700 dark:bg-red-900/40 dark:text-red-300">3 mới</span>
          </div>
          <ul className="space-y-3">
            {ALERTS.map((alert) => (
              <li key={alert.id} className="flex gap-3 rounded-xl border border-slate-100 p-3 dark:border-slate-800">
                <span className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${ALERT_STYLES[alert.level]}`}>
                  <Icon name={alert.level === 'low' ? 'info' : 'warning'} className="h-4 w-4" />
                </span>
                <div className="min-w-0">
                  <p className="text-sm font-medium leading-snug text-slate-800 dark:text-slate-100">{alert.title}</p>
                  <p className="mt-0.5 truncate text-xs text-slate-400 dark:text-slate-500">
                    {alert.store} · {alert.time}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="card p-5 xl:col-span-2">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="font-semibold text-slate-900 dark:text-white">Lô hàng cận hạn</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">Cần ưu tiên xử lý hoặc giảm giá</p>
            </div>
            <span className="badge bg-amber-50 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
              <Icon name="clock" className="h-3.5 w-3.5" />
              Trong 7 ngày
            </span>
          </div>
          <div className="-mx-1 overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-400 dark:border-slate-800 dark:text-slate-500">
                  <th className="px-1 pb-2 font-semibold">Sản phẩm</th>
                  <th className="px-1 pb-2 font-semibold">Lô</th>
                  <th className="px-1 pb-2 font-semibold">Cửa hàng</th>
                  <th className="px-1 pb-2 text-right font-semibold">Số lượng</th>
                  <th className="px-1 pb-2 text-right font-semibold">Còn lại</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {EXPIRING_BATCHES.map((batch) => (
                  <tr key={batch.batch}>
                    <td className="px-1 py-3 font-medium text-slate-800 dark:text-slate-100">{batch.product}</td>
                    <td className="px-1 py-3 font-mono text-xs text-slate-500 dark:text-slate-400">{batch.batch}</td>
                    <td className="px-1 py-3 text-slate-500 dark:text-slate-400">{batch.store}</td>
                    <td className="px-1 py-3 text-right text-slate-700 dark:text-slate-300">{batch.quantity}</td>
                    <td className="px-1 py-3 text-right">
                      <span
                        className={[
                          'badge',
                          batch.days <= 3
                            ? 'bg-red-50 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                            : 'bg-amber-50 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
                        ].join(' ')}
                      >
                        {batch.days} ngày
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Forecast summary */}
      <div className="card overflow-hidden">
        <div className="grid gap-6 p-5 sm:grid-cols-3 sm:items-center">
          <div className="sm:col-span-2">
            <div className="flex items-center gap-2">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-300">
                <Icon name="forecast" className="h-4 w-4" />
              </span>
              <h2 className="font-semibold text-slate-900 dark:text-white">Độ chính xác dự báo 30 ngày</h2>
            </div>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              Prophet đạt RMSE 9,97 trên 100 cặp sản phẩm × cửa hàng trong tập kiểm thử nội bộ.
            </p>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
              <div className="h-full w-[90%] rounded-full bg-gradient-to-r from-brand-500 to-emerald-400" />
            </div>
            <p className="mt-1.5 text-xs text-slate-400 dark:text-slate-500">MAPE 10,43% · mục tiêu dưới 15%</p>
          </div>
          <div className="rounded-2xl bg-slate-50 p-4 text-center dark:bg-slate-800/60">
            <p className="text-3xl font-bold tracking-tight text-brand-600 dark:text-brand-400">97/100</p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">cặp sản phẩm Prophet thắng XGBoost</p>
            <p className="mt-2 text-[11px] text-slate-400 dark:text-slate-500">
              {formatCompactCurrency(1420000000)} doanh thu minh hoạ 30 ngày
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
