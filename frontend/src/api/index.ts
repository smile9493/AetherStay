import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

// Access Token 过期时的静默刷新：刷新期间并发请求排队，成功后重放。
let isRefreshing = false
let pendingQueue: Array<(token: string | null) => void> = []

function flushQueue(token: string | null) {
  pendingQueue.forEach((cb) => cb(token))
  pendingQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined
    const status = error.response?.status
    const url = original?.url ?? ''

    const isAuthEndpoint = ['/auth/login', '/auth/register', '/auth/refresh'].some((p) => url.includes(p))

    if (status === 401 && original && !original._retry && !isAuthEndpoint) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          pendingQueue.push((token) => {
            if (token) resolve(api(original))
            else reject(error)
          })
        })
      }

      original._retry = true
      isRefreshing = true
      try {
        await api.post('/auth/refresh')
        flushQueue('ok')
        isRefreshing = false
        return api(original)
      } catch {
        flushQueue(null)
        isRefreshing = false
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    }

    return Promise.reject(error)
  },
)

export default api
