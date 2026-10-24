import { useEffect, useRef, useState } from 'react'

import { useAuth } from '../../contexts/AuthContext.jsx'

export default function RealtimeAlerts() {
  const { isAuthenticated } = useAuth()
  const [toasts, setToasts] = useState([])
  const wsRef = useRef(null)

  useEffect(() => {
    if (!isAuthenticated) return undefined

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.hostname
    const url = `${protocol}//${host}:8000/ws/alerts`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'alert_updated' || data.type === 'alert_deleted') {
          const id = Date.now()
          setToasts((prev) => [
            ...prev.slice(-2),
            {
              id,
              type: data.type,
              message: data.message || 'Co cap nhat canh bao',
            },
          ])
          setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id))
          }, 5000)
        }
      } catch {
        // ignore malformed
      }
    }

    ws.onerror = () => {}
    ws.onclose = () => {}

    return () => {
      try {
        ws.close()
      } catch {
        // ignore
      }
    }
  }, [isAuthenticated])

  if (!isAuthenticated || toasts.length === 0) return null

  return (
    <div className="fixed bottom-24 left-4 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className="flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800 shadow-lg dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-200"
        >
          <span className="h-2 w-2 rounded-full bg-amber-500" />
          {toast.message}
        </div>
      ))}
    </div>
  )
}
