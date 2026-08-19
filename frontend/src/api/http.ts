import axios, { AxiosError } from 'axios'

export const TOKEN_STORAGE_KEY = 'enterprise_kb_access_token'

// 所有 API 模块共用这一实例，本地直连 FastAPI，生产环境由 Nginx 转发同源请求。
const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  timeout: 180_000,
})

http.interceptors.request.use((config) => {
  // 每次请求自动携带 JWT，页面组件不需要重复拼接 Authorization 请求头。
  const token = localStorage.getItem(TOKEN_STORAGE_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // 令牌过期、签名无效或账号被禁用时，统一清理状态并返回登录页。
      localStorage.removeItem(TOKEN_STORAGE_KEY)
      if (window.location.pathname !== '/login') {
        const redirect = encodeURIComponent(window.location.pathname + window.location.search)
        window.location.assign(`/login?redirect=${redirect}`)
      }
    }
    return Promise.reject(error)
  },
)

export function getErrorMessage(error: unknown, fallback = '请求失败，请稍后重试'): string {
  // 优先展示后端经过处理的 detail，避免把 Axios 底层异常直接暴露给用户。
  if (!axios.isAxiosError(error)) return fallback
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || String(item)).join('；')
  }
  if (error.code === 'ECONNABORTED') return '请求超时，请稍后重试'
  if (!error.response) return '无法连接后端服务，请确认 FastAPI 已启动'
  return fallback
}

export function isRequestCancelled(error: unknown): boolean {
  return axios.isCancel(error) || (axios.isAxiosError(error) && error.code === 'ERR_CANCELED')
}

export default http
