import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import api, { tokenStore } from '../services/api.js'

const AuthContext = createContext(null)

const ROLE_LABELS = {
  owner: 'Chủ sở hữu',
  manager: 'Quản lý',
  staff: 'Nhân viên',
}

/** Both admin roles may write master data; `staff` may not. */
const ADMIN_ROLES = new Set(['owner', 'manager'])

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => tokenStore.getUser())
  const [initializing, setInitializing] = useState(() => Boolean(tokenStore.getAccess()))

  const clearSession = useCallback(() => {
    tokenStore.clear()
    setUser(null)
  }, [])

  /* Re-validate the stored token on boot: a role change or a deactivated
     account must take effect without waiting for the token to expire. */
  useEffect(() => {
    let cancelled = false

    if (!tokenStore.getAccess()) {
      setInitializing(false)
      return undefined
    }

    api
      .get('/auth/me')
      .then((response) => {
        if (cancelled) return
        setUser(response.data)
        tokenStore.setSession({ user: response.data })
      })
      .catch(() => {
        if (!cancelled) clearSession()
      })
      .finally(() => {
        if (!cancelled) setInitializing(false)
      })

    return () => {
      cancelled = true
    }
  }, [clearSession])

  /* The axios interceptor fires this when a refresh attempt fails. */
  useEffect(() => {
    const onExpired = () => setUser(null)
    window.addEventListener('scsp:session-expired', onExpired)
    return () => window.removeEventListener('scsp:session-expired', onExpired)
  }, [])

  const login = useCallback(async (username, password) => {
    const response = await api.post('/auth/login', { username, password })
    tokenStore.setSession(response.data)
    setUser(response.data.user)
    return response.data.user
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout')
    } catch {
      /* The local session must be dropped even if the server call fails. */
    } finally {
      clearSession()
    }
  }, [clearSession])

  const value = useMemo(() => {
    const role = user?.role ?? null
    return {
      user,
      role,
      roleLabel: role ? (ROLE_LABELS[role] ?? role) : '',
      isAuthenticated: Boolean(user),
      isAdmin: Boolean(role && ADMIN_ROLES.has(role)),
      isStaff: role === 'staff',
      initializing,
      login,
      logout,
    }
  }, [user, initializing, login, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}
