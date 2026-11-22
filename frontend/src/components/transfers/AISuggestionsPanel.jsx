import { useEffect, useState } from 'react'

import Icon from '../common/Icon.jsx'
import api from '../../services/api.js'
import { formatNumber, getErrorMessage } from '../../utils/format.js'

const PRIORITY_META = {
  low: { label: 'Thấp', badge: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300' },
  normal: { label: 'Bình thường', badge: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300' },
  high: { label: 'Cao', badge: 'bg-amber-50 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' },
  urgent: { label: 'Khẩn', badge: 'bg-red-50 text-red-700 dark:bg-red-900/40 dark:text-red-300' },
}

const TARGET_OPTIONS = [
  { value: 7, label: '7 ngày' },
  { value: 14, label: '14 ngày' },
  { value: 21, label: '21 ngày' },
  { value: 30, label: '30 ngày' },
]

function CardSkeleton() {
  return (
    <div className="card animate-pulse space-y-3 p-4">
      <div className="h-4 w-1/3 rounded bg-slate-100 dark:bg-slate-800" />
      <div className="h-3 w-2/3 rounded bg-slate-100 dark:bg-slate-800" />
      <div className="h-12 rounded bg-slate-100 dark:bg-slate-800" />
    </div>
  )
}

/**
 * Tab "Gợi ý từ AI": so sánh nhu cầu dự báo (Prophet) với tồn kho thật để
 * chỉ ra cặp cửa hàng dư → thiếu. Toàn bộ con số do
 * `sp_Transfer_SuggestAI` tính; component chỉ hiển thị và chuyển yêu cầu
 * sang form tạo yêu cầu có sẵn.
 */
export default function AISuggestionsPanel({ canManage, onCreate }) {
  const [targetDays, setTargetDays] = useState(14)
  const [suggestions, setSuggestions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')

    api
      .get('/transfers/suggestions', {
        params: { target_days: targetDays, limit: 20, model_name: 'prophet' },
      })
      .then((response) => {
        if (!cancelled) setSuggestions(response.data || [])
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(getErrorMessage(requestError, 'Không tải được gợi ý điều chuyển.'))
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [targetDays, reloadKey])

  return (
    <div className="space-y-4">
      <div className="card p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-300">
              <Icon name="sparkles" className="h-5 w-5" />
            </span>
            <div>
              <h2 className="font-semibold text-slate-900 dark:text-white">
                Gợi ý điều chuyển từ dự báo Prophet
              </h2>
              <p className="mt-0.5 max-w-3xl text-sm text-slate-500 dark:text-slate-400">
                So sánh nhu cầu dự báo với tồn kho thật của từng cặp sản phẩm × cửa hàng.
                Cửa hàng còn nhiều hơn mức phục vụ mục tiêu được xem là dư; cửa hàng thấp hơn là thiếu.
                Hệ thống ghép cặp dư → thiếu và lấy phần nhỏ hơn làm số lượng gợi ý.
              </p>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <label htmlFor="target_days" className="text-xs font-medium text-slate-500 dark:text-slate-400">
              Mức phục vụ mục tiêu
            </label>
            <select
              id="target_days"
              value={targetDays}
              onChange={(event) => setTargetDays(Number(event.target.value))}
              className="input w-auto min-w-[110px]"
            >
              {TARGET_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => setReloadKey((key) => key + 1)}
              className="btn-secondary px-3"
              aria-label="Tải lại gợi ý"
            >
              <Icon name="refresh" className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
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
            <p className="font-semibold text-slate-900 dark:text-white">Không tải được gợi ý</p>
            <p className="mt-1 max-w-md text-sm text-slate-500 dark:text-slate-400">{error}</p>
          </div>
          <button type="button" onClick={() => setReloadKey((key) => key + 1)} className="btn-secondary mt-1">
            <Icon name="refresh" className="h-4 w-4" />
            Thử lại
          </button>
        </div>
      ) : loading ? (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <CardSkeleton key={index} />
          ))}
        </div>
      ) : suggestions.length === 0 ? (
        <div className="card flex flex-col items-center gap-3 px-6 py-16 text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
            <Icon name="transfer" className="h-6 w-6" />
          </span>
          <div>
            <p className="font-semibold text-slate-700 dark:text-slate-200">Chưa có cặp nào cần điều chuyển</p>
            <p className="mt-1 max-w-md text-sm text-slate-500 dark:text-slate-400">
              Với mức phục vụ {targetDays} ngày, không có cửa hàng nào vừa dư vừa thiếu cùng một sản phẩm.
              Thử tăng mức phục vụ mục tiêu để thấy thêm gợi ý.
            </p>
          </div>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between text-sm text-slate-500 dark:text-slate-400">
            <p>
              <span className="font-semibold text-slate-800 dark:text-slate-100">{suggestions.length}</span>{' '}
              gợi ý, xếp theo khối lượng nên chuyển giảm dần.
            </p>
            <p className="hidden sm:block">
              Dự báo {suggestions[0]?.horizon_days ?? 30} ngày · mục tiêu {targetDays} ngày
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {suggestions.map((item) => {
              const priority = PRIORITY_META[item.priority] ?? PRIORITY_META.normal
              const key = `${item.product_id}-${item.from_store_id}-${item.to_store_id}`
              return (
                <div key={key} className="card flex flex-col p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-slate-900 dark:text-white">{item.product_name}</p>
                        <span className="font-mono text-xs text-slate-400 dark:text-slate-500">
                          {item.product_code}
                        </span>
                        <span className={`badge ${priority.badge}`}>{priority.label}</span>
                      </div>
                      <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-sm text-slate-600 dark:text-slate-300">
                        <span className="font-medium text-slate-800 dark:text-slate-100">
                          {item.from_store_name}
                        </span>
                        <Icon name="chevronRight" className="h-3.5 w-3.5 text-slate-400" />
                        <span className="font-medium text-slate-800 dark:text-slate-100">
                          {item.to_store_name}
                        </span>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-slate-500 dark:text-slate-400">Nên chuyển</p>
                      <p className="text-lg font-bold tabular-nums text-brand-700 dark:text-brand-300">
                        {formatNumber(item.suggested_qty)}{' '}
                        <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                          {item.unit}
                        </span>
                      </p>
                    </div>
                  </div>

                  <p className="mt-3 text-sm leading-relaxed text-slate-600 dark:text-slate-300">{item.reason}</p>

                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                    <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800/60">
                      <p className="text-slate-500 dark:text-slate-400">Kho gửi</p>
                      <p className="mt-0.5 font-semibold text-slate-800 dark:text-slate-100">
                        {formatNumber(item.from_stock)} {item.unit} · phủ {formatNumber(item.from_days_cover)} ngày
                      </p>
                    </div>
                    <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800/60">
                      <p className="text-slate-500 dark:text-slate-400">Kho nhận</p>
                      <p className="mt-0.5 font-semibold text-slate-800 dark:text-slate-100">
                        {formatNumber(item.to_stock)} {item.unit} · phủ {formatNumber(item.to_days_cover)} ngày
                      </p>
                    </div>
                  </div>

                  <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                    <p className="text-xs text-slate-400 dark:text-slate-500">
                      Mô hình {item.model_name === 'prophet' ? 'Prophet' : item.model_name} ·{' '}
                      {item.horizon_days} ngày dự báo
                    </p>
                    {canManage && (
                      <button
                        type="button"
                        onClick={() => onCreate(item)}
                        className="btn-primary px-3 py-1.5 text-xs"
                      >
                        <Icon name="plus" className="h-3.5 w-3.5" />
                        Tạo yêu cầu
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
