import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

// 配置 axios 实例
axios.defaults.withCredentials = true

const REFRESH_TOKEN_KEY = 'refresh_token'
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

const saveRefreshToken = (token, rememberMe) => {
  if (rememberMe) {
    localStorage.setItem(REFRESH_TOKEN_KEY, token)
    sessionStorage.removeItem(REFRESH_TOKEN_KEY)
  } else {
    sessionStorage.setItem(REFRESH_TOKEN_KEY, token)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  }
}

const getStoredRefreshToken = () => (
  localStorage.getItem(REFRESH_TOKEN_KEY) || sessionStorage.getItem(REFRESH_TOKEN_KEY)
)

const clearStoredRefreshToken = () => {
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  sessionStorage.removeItem(REFRESH_TOKEN_KEY)
}

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref(null)
  const accessToken = ref(null)
  const isAuthenticated = computed(() => !!accessToken.value)
  const isRefreshing = ref(false)
  let refreshPromise = null

  // Actions
  const login = async (username, password, rememberMe = false) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/token/`, {
        username,
        password
      })

      user.value = { username: username }
      accessToken.value = response.data.access

      // 设置 axios 默认请求头
      setAuthHeader(response.data.access)

      // 记住我时持久化到 localStorage，否则仅当前会话有效
      saveRefreshToken(response.data.refresh, rememberMe)

      return { success: true, message: '登录成功' }
    } catch (error) {
      return {
        success: false,
        message: error.response?.data?.detail || '登录失败'
      }
    }
  }

  const logout = async () => {
    try {
      // 清除本地存储的令牌
      clearStoredRefreshToken()
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      // 清除状态
      user.value = null
      accessToken.value = null
      delete axios.defaults.headers.common['Authorization']
    }
  }

  const refreshToken = async () => {
    // 防止重复刷新
    if (isRefreshing.value) {
      return refreshPromise
    }

    const refreshToken = getStoredRefreshToken()
    if (!refreshToken) {
      return { success: false }
    }

    isRefreshing.value = true
    refreshPromise = axios.post(`${API_BASE_URL}/token/refresh/`, {
      refresh: refreshToken
    })
      .then(response => {
        accessToken.value = response.data.access
        setAuthHeader(response.data.access)
        return { success: true }
      })
      .catch(error => {
        console.error('Token refresh failed:', error)
        // 刷新失败，清除登录状态
        user.value = null
        accessToken.value = null
        clearStoredRefreshToken()
        delete axios.defaults.headers.common['Authorization']
        return { success: false }
      })
      .finally(() => {
        isRefreshing.value = false
        refreshPromise = null
      })

    return refreshPromise
  }

  const fetchUserInfo = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/auth/me/`, {
        headers: {
          'Authorization': `Bearer ${accessToken.value}`
        }
      })
      user.value = response.data.user
      return { success: true }
    } catch (error) {
      console.error('Fetch user info failed:', error)
      return { success: false }
    }
  }

  const setAuthHeader = (token) => {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
  }

  const initAuth = async () => {
    // 启动时尝试用已存储 refresh token 恢复会话
    const result = await refreshToken()
    if (result.success) {
      await fetchUserInfo()
    }
    return result.success
  }

  return {
    user,
    accessToken,
    isAuthenticated,
    isRefreshing,
    login,
    logout,
    refreshToken,
    fetchUserInfo,
    setAuthHeader,
    initAuth
  }
})
