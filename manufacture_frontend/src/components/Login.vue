<template>
  <div class="login-page">
    <div class="login-container">
      <el-card class="login-card" shadow="hover">
        <template #header>
          <h2 class="login-title">系统登录</h2>
        </template>

        <el-form
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          @keyup.enter="handleLogin"
        >
          <el-form-item prop="username">
            <el-input
              v-model="loginForm.username"
              placeholder="用户名"
              :prefix-icon="User"
              size="large"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="密码"
              :prefix-icon="Lock"
              size="large"
              show-password
            />
          </el-form-item>

          <el-form-item>
            <el-checkbox v-model="loginForm.rememberMe">
              记住我（30天内免登录）
            </el-checkbox>
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              @click="handleLogin"
              style="width: 100%"
            >
              登录
            </el-button>
          </el-form-item>
        </el-form>

        <div class="login-tips">
          <el-alert
            v-if="errorMessage"
            :title="errorMessage"
            type="error"
            :closable="false"
            show-icon
          />
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth.js'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const loginFormRef = ref(null)
const loading = ref(false)
const errorMessage = ref('')

// 登录表单
const loginForm = reactive({
  username: '',
  password: '',
  rememberMe: false
})

const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!loginFormRef.value) return

  try {
    await loginFormRef.value.validate()
  } catch {
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    const result = await authStore.login(
      loginForm.username,
      loginForm.password,
      loginForm.rememberMe
    )

    if (result.success) {
      ElMessage.success('登录成功')
      // 跳转到之前尝试访问的页面，或首页
      const redirect = route.query.redirect || '/'
      router.push(redirect)
    } else {
      errorMessage.value = result.message
    }
  } catch (error) {
    errorMessage.value = '登录失败，请稍后重试'
    console.error('Login error:', error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* 登录页面外层容器 - 全屏 */
.login-page {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  /* 背景图片 */
  background-image: url('/images/login-bg-placeholder.png');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  /* 确保在底层但不被覆盖 */
  z-index: 1;
  /* 确保不被其他元素影响 */
  overflow: hidden;
}

/* 登录容器 - 居中 */
.login-container {
  position: relative;
  z-index: 2;
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

/* 登录卡片 */
.login-card {
  width: 400px;
  max-width: 90%;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
}

.login-title {
  text-align: center;
  margin: 0;
  color: #333;
  font-size: 24px;
}

.login-tips {
  margin-top: 20px;
}
</style>
