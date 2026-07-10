import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

// Paths that may legitimately return 401 — do not attempt token refresh
const NO_REFRESH_PATHS = ['/auth/me', '/auth/login', '/auth/register', '/auth/refresh']

function shouldSkipRefresh(url: string | undefined): boolean {
  if (!url) return false
  return NO_REFRESH_PATHS.some((p) => url.includes(p))
}

// Token silent refresh: on 401, call /auth/refresh then retry once
let isRefreshing = false
let pendingQueue: Array<{
  resolve: (val: unknown) => void
  reject: (err: unknown) => void
}> = []

function processQueue(success: boolean, error?: unknown) {
  pendingQueue.forEach(({ resolve, reject }) => {
    if (success) resolve(undefined)
    else reject(error)
  })
  pendingQueue = []
}

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const originalRequest = error.config
    if (
      error.response?.status !== 401 ||
      originalRequest._retry ||
      shouldSkipRefresh(originalRequest.url)
    ) {
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        pendingQueue.push({ resolve, reject })
      }).then(() => api(originalRequest))
    }

    originalRequest._retry = true
    isRefreshing = true

    try {
      await api.post('/auth/refresh')
      processQueue(true)
      return api(originalRequest)
    } catch (refreshError) {
      processQueue(false, refreshError)
      // Lazy import avoids circular dependency: router → auth → api → router
      const { default: router } = await import('@/router')
      const { name } = router.currentRoute.value
      if (name !== 'login' && name !== 'register') {
        await router.push({
          name: 'login',
          query: { redirect: router.currentRoute.value.fullPath },
        })
      }
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  }
)

export default api
