import axios from 'axios'

/* ------------------------------------------------------------------ */
/* Storage keys - one place only, so token handling stays consistent. */
/* ------------------------------------------------------------------ */

export const ACCESS_TOKEN_KEY = 'scsp_access_token'
export const REFRESH_TOKEN_KEY = 'scsp_refresh_token'
export const USER_KEY = 'scsp_user'

export const tokenStore = {
  getAccess() {
    return localStorage.getItem(ACCESS_TOKEN_KEY)
  },
  getRefresh() {
    return localStorage.getItem(REFRESH_TOKEN_KEY)
  },
  getUser() {
    try {
      const raw = localStorage.getItem(USER_KEY)
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  },
  /**
   * Persist a whole session. The login and refresh endpoints both return
   * the same shape, so both paths use this one function.
   */
  setSession({ access_token, accessToken, refresh_token, refreshToken, user }) {
    const access = access_token ?? accessToken
    const refresh = refresh_token ?? refreshToken
    if (access) localStorage.setItem(ACCESS_TOKEN_KEY, access)
    if (refresh) localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
  },
  clear() {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  },
}

/* ------------------------------------------------------------------ */
/* Axios instance                                                      */
/* ------------------------------------------------------------------ */

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = tokenStore.getAccess()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/**
 * Refresh at most once for a burst of parallel 401s. Without this every
 * failed request would rotate the refresh token and most of them would be
 * rejected as "already revoked".
 */
let refreshPromise = null

function refreshSession() {
  if (!refreshPromise) {
    const refreshToken = tokenStore.getRefresh()
    refreshPromise = axios
      .post('/api/v1/auth/refresh', { refresh_token: refreshToken })
      .then((response) => {
        tokenStore.setSession(response.data)
        return response.data
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const status = error.response?.status
    const url = original?.url ?? ''
    const isAuthEndpoint = url.includes('/auth/login') || url.includes('/auth/refresh')

    if (status === 401 && original && !original._retry && !isAuthEndpoint) {
      original._retry = true

      if (tokenStore.getRefresh()) {
        try {
          const data = await refreshSession()
          original.headers.Authorization = `Bearer ${data.access_token}`
          return api(original)
        } catch {
          /* Fall through to a full sign-out below. */
        }
      }

      tokenStore.clear()
      window.dispatchEvent(new CustomEvent('scsp:session-expired'))
    }

    return Promise.reject(error)
  },
)

export default api
