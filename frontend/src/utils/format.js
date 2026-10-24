/** Shared formatting helpers. */

const currencyFormatter = new Intl.NumberFormat('vi-VN', {
  style: 'currency',
  currency: 'VND',
  maximumFractionDigits: 0,
})

const compactFormatter = new Intl.NumberFormat('vi-VN', {
  notation: 'compact',
  maximumFractionDigits: 1,
})

const numberFormatter = new Intl.NumberFormat('vi-VN', {
  maximumFractionDigits: 1,
})

export function formatCurrency(value) {
  const number = Number(value)
  return Number.isFinite(number) ? currencyFormatter.format(number) : '—'
}

export function formatCompactCurrency(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return '—'
  return `${compactFormatter.format(number)} đ`
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
