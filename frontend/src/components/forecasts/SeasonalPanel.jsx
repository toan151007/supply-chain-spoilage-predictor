import { useEffect, useMemo, useRef, useState } from 'react'

import Icon from '../common/Icon.jsx'
import api from '../../services/api.js'
import { formatNumber, getErrorMessage } from '../../utils/format.js'

/** Chu ky tu dong goi lai API du bao mua vu (yeu cau nghiep vu: 5 phut). */
const REFRESH_MS = 5 * 60 * 1000

const SEASON_TONE = {
  spring: {
    ring: 'ring-emerald-500',
    chip: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  },
  summer: {
    ring: 'ring-amber-500',
    chip: 'bg-amber-50 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  },
  autumn: {
    ring: 'ring-orange-500',
    chip: 'bg-orange-50 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
  },
  winter: {
    ring: 'ring-sky-500',
    chip: 'bg-sky-50 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300',
  },
}

function formatClock(date) {
  if (!date) return '—'
  return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function formatCountdown(seconds) {
  const safe = Math.max(0, seconds)
  const minutes = Math.floor(safe / 60)
  const rest = safe % 60
  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
}

function ProductRow({ item, tone }) {
  return (
    <li className="flex items-start justify-between gap-3 border-b border-slate-100 py-2.5 last:border-0 dark:border-slate-800">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-slate-900 dark:text-white">{item.product_name}</p>
        <p className="mt-0.5 text-xs text-slate-400 dark:text-slate-500">
          {item.category_name || 'Chưa phân nhóm'} · trung bình {formatNumber(item.avg_daily_qty)} {item.unit || 'đơn vị'}/ngày
        </p>
      </div>
      <div className="shrink-0 text-right">
        <p className={`text-sm font-semibold tabular-nums ${tone}`}>
          {Number(item.seasonal_index).toFixed(3)}
        </p>
        <p className="text-xs text-slate-400 dark:text-slate-500">
          hạng {item.rank_in_season}/{item.season_products}
        </p>
      </div>
    </li>
  )
}

/**
 * Dự báo theo mùa vụ, tự động làm mới mỗi 5 phút.
 *
 * Đồng hồ đếm ngược chạy bằng `setInterval` 1 giây, còn việc gọi API được
 * kích hoạt bằng so sánh mốc thời gian `now >= nextRefresh`. Cách này tránh
 * gọi lặp nhiều lần khi request đang chạy (mỗi giây `now` lại đổi).
 */
export default function SeasonalPanel() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  const [lastUpdated, setLastUpdated] = useState(null)
  const [nextRefresh, setNextRefresh] = useState(() => Date.now() + REFRESH_MS)
  const [now, setNow] = useState(Date.now())
  const [seasonCode, setSeasonCode] = useState('')

  const hasDataRef = useRef(false)
  const autoRefreshRef = useRef(false)

  /* Đồng hồ 1 giây chỉ để vẽ đếm ngược. */
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])

  /* Gọi API: lần đầu và mỗi khi reloadKey tăng (thủ công hoặc tự động). */
  useEffect(() => {
    let cancelled = false
    const firstLoad = !hasDataRef.current

    if (firstLoad) setLoading(true)
    else setRefreshing(true)
    setError('')

    api
      .get('/forecasts/seasonal')
      .then((response) => {
        if (cancelled) return
        hasDataRef.current = true
        setData(response.data)
        setLastUpdated(new Date())
        setSeasonCode((previous) => previous || response.data.current_season)
        setNextRefresh(Date.now() + REFRESH_MS)
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(getErrorMessage(requestError, 'Không tải được dự báo theo mùa.'))
        }
      })
      .finally(() => {
        if (cancelled) return
        autoRefreshRef.current = false
        setLoading(false)
        setRefreshing(false)
      })

    return () => {
      cancelled = true
    }
  }, [reloadKey])

  /* Hết 5 phút thì tự gọi lại, nhưng chỉ một lần cho mỗi chu kỳ. */
  useEffect(() => {
    if (now >= nextRefresh && !autoRefreshRef.current) {
      autoRefreshRef.current = true
      setReloadKey((key) => key + 1)
    }
  }, [now, nextRefresh])

  const seasons = useMemo(() => data?.seasons || [], [data])
  const selected = useMemo(
    () => seasons.find((season) => season.season_code === seasonCode) || seasons[0] || null,
    [seasons, seasonCode],
  )

  const secondsLeft = Math.max(0, Math.ceil((nextRefresh - now) / 1000))

  if (loading) {
    return (
      <div className="card p-10">
        <div className="flex items-center justify-center gap-3 text-sm text-slate-500 dark:text-slate-400">
          <Icon name="refresh" className="h-5 w-5 animate-spin" />
          <span>Đang tính chỉ số mùa vụ từ dữ liệu bán hàng lịch sử…</span>
        </div>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="card flex flex-col items-center gap-3 px-6 py-16 text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-red-50 text-red-600 dark:bg-red-950/50 dark:text-red-400">
          <Icon name="warning" className="h-6 w-6" />
        </span>
        <div>
          <p className="font-semibold text-slate-900 dark:text-white">Không tải được dự báo theo mùa</p>
          <p className="mt-1 max-w-md text-sm text-slate-500 dark:text-slate-400">{error}</p>
        </div>
        <button type="button" onClick={() => setReloadKey((key) => key + 1)} className="btn-secondary mt-1">
          <Icon name="refresh" className="h-4 w-4" />
          Thử lại
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Thông tin làm mới */}
      <div className="card flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-300">
            <Icon name="leaf" className="h-4 w-4" />
          </span>
          <div>
            <p className="text-sm font-semibold text-slate-900 dark:text-white">
              Dự báo theo mùa vụ
              {data?.data_from && data?.data_to ? ` · dữ liệu ${data.data_from} → ${data.data_to}` : ''}
            </p>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              Cập nhật lúc {formatClock(lastUpdated)} · tự động làm mới sau{' '}
              <span className="font-semibold tabular-nums text-brand-600 dark:text-brand-400">
                {formatCountdown(secondsLeft)}
              </span>
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setReloadKey((key) => key + 1)}
          disabled={refreshing}
          className="btn-secondary w-fit"
        >
          <Icon name="refresh" className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? 'Đang làm mới…' : 'Làm mới ngay'}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/50 dark:text-amber-200">
          Lần làm mới gần nhất thất bại: {error} Đang hiển thị dữ liệu của lần trước.
        </div>
      )}

      {/* Chọn mùa */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {seasons.map((season) => {
          const tone = SEASON_TONE[season.season_code] ?? SEASON_TONE.spring
          const active = selected?.season_code === season.season_code
          return (
            <button
              key={season.season_code}
              type="button"
              onClick={() => setSeasonCode(season.season_code)}
              className={[
                'card px-4 py-3 text-left transition-colors',
                active
                  ? `ring-2 ${tone.ring}`
                  : 'hover:bg-slate-50 dark:hover:bg-slate-800/60',
              ].join(' ')}
            >
              <div className="flex items-center justify-between">
                <span className={`badge ${tone.chip}`}>{season.season_name}</span>
                {season.is_current && (
                  <span className="text-[11px] font-semibold uppercase tracking-wide text-brand-600 dark:text-brand-400">
                    Hiện tại
                  </span>
                )}
              </div>
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                Tháng {season.months.join(', ')}
              </p>
              <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">
                <span className="font-semibold text-emerald-600 dark:text-emerald-400">{season.import_count}</span>{' '}
                nên nhập ·{' '}
                <span className="font-semibold text-red-600 dark:text-red-400">{season.avoid_count}</span> hạn chế
              </p>
            </button>
          )
        })}
      </div>

      {selected && (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <div className="card p-5">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300">
                <Icon name="arrowUp" className="h-4 w-4" />
              </span>
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white">
                  Nên nhập nhiều hơn vào mùa {selected.season_name.toLowerCase()}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Chỉ số mùa vụ cao nhất — nhu cầu tương đối mạnh hơn mức chung
                </p>
              </div>
            </div>
            <ul className="mt-3">
              {selected.import_items.length === 0 ? (
                <li className="py-6 text-center text-sm text-slate-400 dark:text-slate-500">
                  Chưa đủ dữ liệu để xếp hạng mùa này.
                </li>
              ) : (
                selected.import_items.map((item) => (
                  <ProductRow
                    key={item.product_id}
                    item={item}
                    tone="text-emerald-600 dark:text-emerald-400"
                  />
                ))
              )}
            </ul>
          </div>

          <div className="card p-5">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300">
                <Icon name="arrowDown" className="h-4 w-4" />
              </span>
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white">
                  Nên hạn chế nhập vào mùa {selected.season_name.toLowerCase()}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Chỉ số mùa vụ thấp nhất — dễ tồn kho và lãng phí nếu nhập nhiều
                </p>
              </div>
            </div>
            <ul className="mt-3">
              {selected.avoid_items.length === 0 ? (
                <li className="py-6 text-center text-sm text-slate-400 dark:text-slate-500">
                  Chưa đủ dữ liệu để xếp hạng mùa này.
                </li>
              ) : (
                selected.avoid_items.map((item) => (
                  <ProductRow
                    key={item.product_id}
                    item={item}
                    tone="text-red-600 dark:text-red-400"
                  />
                ))
              )}
            </ul>
          </div>
        </div>
      )}

      {data?.method && (
        <details className="card px-4 py-3 text-sm">
          <summary className="cursor-pointer font-medium text-slate-700 dark:text-slate-200">
            Cách tính chỉ số mùa vụ
          </summary>
          <p className="mt-2 leading-relaxed text-slate-600 dark:text-slate-300">{data.method}</p>
          <p className="mt-2 text-xs text-slate-400 dark:text-slate-500">
            Chỉ số 1,000 nghĩa là sản phẩm có tỷ trọng doanh số trong mùa đúng bằng mức chung của toàn hệ thống.
            Cao hơn 1,000 là mạnh hơn mức chung, thấp hơn là yếu hơn.
          </p>
        </details>
      )}
    </div>
  )
}
