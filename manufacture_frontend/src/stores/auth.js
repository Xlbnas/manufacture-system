import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

// 配置 axios 实例
axios.defaults.withCredentials = true

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
      const response = await axios.post('http://127.0.0.1:9876/api/token/', {
        username,
        password
      })

      user.value = { username: username }
      accessToken.value = response.data.access

      // 设置 axios 默认请求头
      setAuthHeader(response.data.access)

      // 保存刷新令牌
      localStorage.setItem('refresh_token', response.data.refresh)

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
      localStorage.removeItem('refresh_token')
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

    const refreshToken = localStorage.getItem('refresh_token')
    if (!refreshToken) {
      return { success: false }
    }

    isRefreshing.value = true
    refreshPromise = axios.post('http://127.0.0.1:9876/api/token/refresh/', {
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
        localStorage.removeItem('refresh_token')
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
      const response = await axios.get('http://127.0.0.1:9876/api/auth/me/', {
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
    // 尝试刷新令牌（如果存在 refresh token cookie）
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
