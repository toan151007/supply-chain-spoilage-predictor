import { useEffect, useRef, useState } from 'react'

import Icon from './Icon.jsx'
import { useAuth } from '../../contexts/AuthContext.jsx'
import api from '../../services/api.js'

const QUICK_QUESTIONS = [
  'Hang nao sap het han trong 7 ngay toi?',
  'Co nhung canh bao nao chua xu ly?',
  'Top 5 san pham co doanh so cao nhat?',
  'Cua hang nao co ton kho thap nhat?',
]

export default function Chatbot() {
  const { isAuthenticated } = useAuth()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Xin chao! Toi la tro ly AI cua FreshChain. Ban can toi giup gi ve ton kho, don hang, canh bao hay du bao nhu cau?',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
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
      const detail = err?.response?.data?.detail || err?.message || 'Khong the ket noi voi tro ly AI.'
      setError(typeof detail === 'string' ? detail : 'Loi khi goi chatbot.')
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Xin loi, hien tai khong the tra loi. Vui long thu lai sau.',
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

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-5 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-brand-600 text-white shadow-lg shadow-brand-600/30 transition hover:bg-brand-700 dark:shadow-brand-900/40"
        aria-label={open ? 'Dong chatbot' : 'Mo chatbot'}
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
              <p className="text-xs text-slate-500 dark:text-slate-400">Hoi dap ve ton kho, don hang, canh bao</p>
            </div>
            <button type="button" onClick={() => setOpen(false)} className="ml-auto rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800">
              <Icon name="close" />
            </button>
          </div>

          <div ref={scrollRef} className="max-h-[360px] space-y-3 overflow-y-auto px-4 py-3">
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
                  AI dang suy nghi...
                </div>
              </div>
            )}
            {messages.length === 1 && !loading && (
              <div className="flex flex-wrap gap-1.5">
                {QUICK_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => send(q)}
                    className="rounded-full border border-slate-200 px-2.5 py-1 text-xs text-slate-600 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                  >
                    {q}
                  </button>
                ))}
              </div>
            )}
            {error && <p className="text-xs text-red-500 dark:text-red-400">{error}</p>}
          </div>

          <form onSubmit={onSubmit} className="flex items-center gap-2 border-t border-slate-200 px-3 py-2 dark:border-slate-800">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Nhap cau hoi..."
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
