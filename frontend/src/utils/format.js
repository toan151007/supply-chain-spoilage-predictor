/** Shared formatting helpers. */

const currencyFormatter = new Intl.NumberFormat('vi-VN', {
  maximumFractionDigits: 0,
})

const compactNumberFormatter = new Intl.NumberFormat('vi-VN', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
})

/* Custom compact units: Intl `notation: 'compact'` for vi-VN returns
   "1,42 T" / "842 Tr", which is not Vietnamese prose. Spell the units out. */
const COMPACT_UNITS = [
  { threshold: 1e12, divisor: 1e12, suffix: 'nghìn tỷ' },
  { threshold: 1e9, divisor: 1e9, suffix: 'tỷ' },
  { threshold: 1e6, divisor: 1e6, suffix: 'triệu' },
  { threshold: 1e3, divisor: 1e3, suffix: 'nghìn' },
]

const numberFormatter = new Intl.NumberFormat('vi-VN', {
  maximumFractionDigits: 1,
})

/**
 * Full Vietnamese dong amount, e.g. 1420000000 -> "1.420.000.000 đ".
 * Thousands are separated with a dot, the unit stays at the end.
 */
export function formatCurrency(value) {
  const number = Number(value)
  return Number.isFinite(number) ? `${currencyFormatter.format(number)} đ` : '—'
}

/**
 * Short but accurate amount for tight spaces, e.g.
 *   1420000000 -> "1,42 tỷ đ"
 *   842000000  -> "842 triệu đ"
 * Keeps up to two decimals instead of rounding to "1,4 tỷ".
 */
export function formatCompactCurrency(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return '—'

  const absolute = Math.abs(number)
  const unit = COMPACT_UNITS.find((item) => absolute >= item.threshold)
  if (!unit) return `${compactNumberFormatter.format(number)} đ`

  const scaled = number / unit.divisor
  return `${compactNumberFormatter.format(scaled)} ${unit.suffix} đ`
}

export function formatNumber(value) {
  const number = Number(value)
  return Number.isFinite(number) ? numberFormatter.format(number) : '—'
}

export function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleDateString('vi-VN')
}

/**
 * FastAPI returns `detail` either as a string or, for validation errors,
 * as a list of `{ loc, msg }` objects. Normalise both into one sentence
 * the UI can show without leaking a raw object.
 */
export function getErrorMessage(error, fallback = 'Đã có lỗi xảy ra. Vui lòng thử lại.') {
  const detail = error?.response?.data?.detail

  if (typeof detail === 'string') return detail

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const field = Array.isArray(item?.loc) ? item.loc.at(-1) : null
        return field ? `${field}: ${item.msg}` : item?.msg
      })
      .filter(Boolean)
      .join('; ')
  }

  if (error?.code === 'ECONNABORTED') return 'Máy chủ phản hồi quá lâu. Vui lòng thử lại.'
  if (!error?.response) return 'Không kết nối được tới máy chủ. Kiểm tra backend đang chạy ở cổng 8000.'

  return fallback
}
