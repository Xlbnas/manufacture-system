import axios from 'axios'
import { useAuthStore } from '../stores/auth.js'
import router from '../router'

// 创建 axios 实例
const api = axios.create({
  baseURL: 'http://127.0.0.1:9876/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true // 允许携带凭证（cookie）
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore()
    // 添加访问令牌到请求头
    if (authStore.accessToken) {
      config.headers.Authorization = `Bearer ${authStore.accessToken}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response
  },
  async (error) => {
    const originalRequest = error.config
    const authStore = useAuthStore()

    // 如果是 401 错误且不是刷新令牌请求
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        // 尝试刷新令牌
        const result = await authStore.refreshToken()
        if (result.success) {
          // 刷新成功，重试原请求
          originalRequest.headers.Authorization = `Bearer ${authStore.accessToken}`
          return api(originalRequest)
        } else {
          // 刷新失败，跳转到登录页
          router.push({
            path: '/login',
            query: { redirect: router.currentRoute.value.fullPath }
          })
        }
      } catch (refreshError) {
        // 刷新失败，跳转到登录页
        router.push({
          path: '/login',
          query: { redirect: router.currentRoute.value.fullPath }
        })
      }
    }

    return Promise.reject(error)
  }
)

export default api
