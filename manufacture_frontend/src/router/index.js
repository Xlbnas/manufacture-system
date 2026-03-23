import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../components/Login.vue'),
    meta: { public: true }
  },
  {
    path: '/',
    name: 'Home',
    redirect: '/dashboard'
  },
  {
    path: '/production',
    name: 'Production',
    component: () => import('../components/production.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/warehouse',
    name: 'Warehouse',
    component: () => import('../components/warehouse.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/outbound',
    name: 'Outbound',
    component: () => import('../components/outbound.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../components/dashboard.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/factory',
    name: 'Factory',
    component: () => import('../components/factory.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/material',
    name: 'Material',
    component: () => import('../components/material.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/product',
    name: 'Product',
    component: () => import('../components/product.vue'),
    meta: { requiresAuth: true }
  },

]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach(async (to, from) => {
  const authStore = useAuthStore()

  // 公开页面直接放行
  if (to.meta.public) {
    // 已登录用户访问登录页，重定向到首页
    if (authStore.isAuthenticated && to.path === '/login') {
      return '/'
    }
    return true
  }

  // 需要认证的页面
  if (to.meta.requiresAuth) {
    if (authStore.isAuthenticated) {
      return true
    } else {
      // 尝试刷新令牌
      const refreshed = await authStore.refreshToken()
      if (refreshed.success) {
        return true
      } else {
        // 刷新失败，跳转到登录页
        return {
          path: '/login',
          query: { redirect: to.fullPath }
        }
      }
    }
  }

  return true
})

export default router
