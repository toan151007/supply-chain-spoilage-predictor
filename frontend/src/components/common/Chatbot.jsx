import { useEffect, useRef, useState } from 'react'

import Icon from './Icon.jsx'
import { useAuth } from '../../contexts/AuthContext.jsx'
import api from '../../services/api.js'

const QUICK_PROMPTS = [
  'Sản phẩm nào sắp hết hạn?',
  'Top 5 sản phẩm bán chạy hôm nay?',
  'Mùa đông nên nhập thêm gì?',
  'Có cảnh báo nào chưa xử lý?',
]

const TIPS = [
  {
    icon: '📝',
    text: 'Nhập câu hỏi đầy đủ, rõ ràng (Ví dụ: "Tồn kho hiện tại thế nào?" thay vì "kho").',
  },
  {
    icon: '⚠️',
    text: 'Tôi đã được huấn luyện để tự động sửa lỗi chính tả, nhưng hạn chế dùng từ viết tắt quá ngắn để tránh hiểu lầm.',
  },
  {
    icon: '💡',
    text: 'Tôi có thể tra cứu: Tồn kho, Hạn sử dụng, Top bán chạy, Dự báo nhu cầu mùa vụ, Điều chuyển hàng.',
  },
  {
    icon: '📞',
    text: 'Nếu cần hỗ trợ khẩn cấp, vui lòng liên hệ quản lý cửa hàng.',
  },
]

function QuickPrompts({ onPick }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {QUICK_PROMPTS.map((prompt) => (
        <button
          key={prompt}
          type="button"
          onClick={() => onPick(prompt)}
          className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-left text-xs text-slate-600 transition hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-brand-700 dark:hover:bg-brand-950/40 dark:hover:text-brand-300"
        >
          {prompt}
        </button>
      ))}
    </div>
  )
}

function WelcomePanel({ onDismiss }) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-gradient-to-br from-brand-50 via-white to-white p-3.5 dark:border-slate-700 dark:from-brand-950/50 dark:via-slate-900 dark:to-slate-900">
      <button
        type="button"
        onClick={onDismiss}
        className="absolute right-2 top-2 rounded-lg p-1.5 text-slate-400 transition hover:bg-white/80 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
        aria-label="Đóng lời chào"
      >
        <Icon name="close" className="h-3.5 w-3.5" />
      </button>

      <div className="flex items-start gap-2.5 pr-6">
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm shadow-brand-600/25">
          <Icon name="sparkles" className="h-4 w-4" />
        </span>
        <div className="min-w-0">
          <h2 className="text-sm font-bold leading-snug text-slate-900 dark:text-white">
            Chào mừng bạn đến với Trợ lý AI FreshChain!
          </h2>
          <p className="mt-1 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
            Tôi hỗ trợ tra cứu tồn kho, hạn sử dụng, bán chạy, mùa vụ và điều chuyển
            hàng.
          </p>
        </div>
      </div>

      <div className="mt-2.5 rounded-xl border border-slate-200/80 bg-white/80 p-3 dark:border-slate-700/80 dark:bg-slate-800/60">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Mẹo để trò chuyện hiệu quả
        </p>
        <ul className="mt-1.5 space-y-1.5">
          {TIPS.map((tip) => (
            <li key={tip.icon} className="flex gap-2 text-[11.5px] leading-relaxed text-slate-700 dark:text-slate-300">
              <span aria-hidden="true" className="shrink-0 text-[13px] leading-5">
                {tip.icon}
              </span>
              <span>{tip.text}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default function Chatbot() {
  const { isAuthenticated } = useAuth()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [welcomeDismissed, setWelcomeDismissed] = useState(false)
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, loading])

  if (!isAuthenticated) return null

  const send = async (text) => {
    const message = (text ?? input).trim()
    if (!message || loading) return
    setInput('')
    setError('')
    setMessages((prev) => [...prev, { role: 'user', content: message }])
    setLoading(true)
    try {
      const res = await api.post('/chat', { message })
      setMessages((prev) => [...prev, { role: 'assistant', content: res.data.answer }])
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'Không thể kết nối với trợ lý AI.'
      setError(typeof detail === 'string' ? detail : 'Lỗi khi gọi chatbot.')
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Xin lỗi, hiện tại tôi không thể trả lời. Vui lòng thử lại sau.',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const onSubmit = (e) => {
    e.preventDefault()
    send()
  }

  const showWelcome = messages.length === 0 && !welcomeDismissed

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-5 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-brand-600 text-white shadow-lg shadow-brand-600/30 transition hover:bg-brand-700 dark:shadow-brand-900/40"
        aria-label={open ? 'Đóng chatbot' : 'Mở chatbot'}
      >
        <Icon name={open ? 'close' : 'sparkles'} className="h-6 w-6" />
      </button>

      {open && (
        <div className="fixed bottom-24 right-4 z-50 w-[min(380px,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center gap-3 border-b border-slate-200 px-4 py-3 dark:border-slate-800">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-300">
              <Icon name="sparkles" className="h-4 w-4" />
            </span>
            <div>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">FreshChain AI Agent</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Hỏi đáp về tồn kho, đơn hàng, cảnh báo</p>
            </div>
            <button type="button" onClick={() => setOpen(false)} className="ml-auto rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800">
              <Icon name="close" />
            </button>
          </div>

          <div
            ref={scrollRef}
            className={`space-y-3 overflow-y-auto px-4 py-3 ${
              showWelcome ? 'max-h-[min(540px,70vh)]' : 'max-h-[360px]'
            }`}
          >
            {showWelcome && (
              <>
                <WelcomePanel onDismiss={() => setWelcomeDismissed(true)} />
                <div>
                  <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                    Câu hỏi gợi ý
                  </p>
                  <QuickPrompts onPick={send} />
                </div>
              </>
            )}

            {!showWelcome && messages.length === 0 && (
              <div>
                <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Câu hỏi gợi ý
                </p>
                <QuickPrompts onPick={send} />
              </div>
            )}

            {messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={[
                    'max-w-[80%] whitespace-pre-wrap rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed',
                    msg.role === 'user'
                      ? 'rounded-br-md bg-brand-600 text-white'
                      : 'rounded-bl-md bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-100',
                  ].join(' ')}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="flex items-center gap-2 rounded-2xl rounded-bl-md bg-slate-100 px-3.5 py-2.5 text-sm text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                  <Icon name="refresh" className="h-4 w-4 animate-spin" />
                  AI đang suy nghĩ...
                </div>
              </div>
            )}
            {error && <p className="text-xs text-red-500 dark:text-red-400">{error}</p>}
          </div>

          <form onSubmit={onSubmit} className="flex items-center gap-2 border-t border-slate-200 px-3 py-2 dark:border-slate-800">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Nhập câu hỏi..."
              className="flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            />
            <button type="submit" disabled={loading || !input.trim()} className="rounded-xl bg-brand-600 p-2 text-white disabled:opacity-50">
              <Icon name="chevronRight" className="h-4 w-4" />
            </button>
          </form>
        </div>
      )}
    </>
  )
}
