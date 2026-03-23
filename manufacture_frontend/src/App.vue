<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { PieChart, OfficeBuilding, Box, Refresh, Goods, Moon, Sunny, HomeFilled, User, SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from './stores/auth.js'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const darkMode = ref(false)

// 计算当前激活的菜单
const activeMenu = computed(() => {
  return route.path.substring(1) || 'dashboard'
})

// 切换菜单
const handleMenuClick = (key) => {
  router.push('/' + key)
}

// 切换暗黑模式
const toggleDarkMode = () => {
  darkMode.value = !darkMode.value
  if (darkMode.value) {
    document.documentElement.classList.add('dark-mode')
  } else {
    document.documentElement.classList.remove('dark-mode')
  }
}

// 登出
const handleLogout = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要登出吗？',
      '确认登出',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await authStore.logout()
    ElMessage.success('登出成功')
    router.push('/login')
  } catch {
    // 用户取消
  }
}
</script>

<template>
  <div class="app-container">
    <!-- 登录页面不需要侧边栏 -->
    <template v-if="route.path !== '/login'">
      <el-aside class="aside">
        <el-menu
          :default-active="activeMenu"
          class="el-menu-vertical-demo"
          @select="handleMenuClick"
        >
          <el-menu-item index="dashboard">
            <el-icon><PieChart /></el-icon>
            <span>数据看板</span>
          </el-menu-item>
          <el-menu-item index="factory">
            <el-icon><OfficeBuilding /></el-icon>
            <span>工厂管理</span>
          </el-menu-item>
          <el-menu-item index="material">
            <el-icon><Box /></el-icon>
            <span>原料管理</span>
          </el-menu-item>
          <el-menu-item index="product">
            <el-icon><Goods /></el-icon>
            <span>产品管理</span>
          </el-menu-item>
          <el-menu-item index="production">
            <el-icon><Refresh /></el-icon>
            <span>生产管理</span>
          </el-menu-item>
          <el-menu-item index="warehouse">
            <el-icon><HomeFilled /></el-icon>
            <span>工厂仓库</span>
          </el-menu-item>
          <el-menu-item index="outbound">
            <el-icon><Goods /></el-icon>
            <span>出库管理</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <div class="content-container">
        <el-header class="header">
          <div class="header-content">
            <h1>工厂生产管理系统</h1>
            <div class="header-right">
              <!-- 用户信息 -->
              <div v-if="authStore.user" class="user-info">
                <el-icon><User /></el-icon>
                <span>{{ authStore.user.username }}</span>
              </div>
              <!-- 主题切换 -->
              <el-button 
                type="primary" 
                circle 
                @click="toggleDarkMode"
                :icon="darkMode ? Sunny : Moon"
                class="theme-toggle"
              />
              <!-- 登出按钮 -->
              <el-button
                type="danger"
                circle
                @click="handleLogout"
                :icon="SwitchButton"
                class="logout-btn"
                title="登出"
              />
            </div>
          </div>
        </el-header>
        <el-main class="main">
          <router-view />
        </el-main>
      </div>
    </template>
    
    <!-- 登录页面 -->
    <template v-else>
      <router-view />
    </template>
  </div>
</template>

<style>
/* 全局样式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  font-family: 'Microsoft YaHei', 'SimHei', Arial, sans-serif;
  font-size: 14px;
  line-height: 1.5;
  color: #333;
  background-color: #f5f7fa;
  height: 100%;
  width: 100%;
  overflow: hidden;
}

/* 黑夜模式 */
.dark-mode {
  --bg-color: #1a1a1a;
  --text-color: #e0e0e0;
  --card-bg: #2c2c2c;
  --header-bg: #303133;
  --aside-bg: #202020;
  --border-color: #444;
}

.dark-mode body {
  background-color: var(--bg-color);
  color: var(--text-color);
}

.dark-mode span {
  color: var(--text-color);
}

.dark-mode h1, .dark-mode h2, .dark-mode h3, .dark-mode h4, .dark-mode h5, .dark-mode h6 {
  color: var(--text-color);
}

.dark-mode .el-card {
  background-color: var(--card-bg);
  border-color: var(--border-color);
}

.dark-mode .el-card__header {
  background-color: var(--card-bg);
  border-color: var(--border-color);
}

.dark-mode .el-table {
  background-color: var(--card-bg);
  color: var(--text-color);
}

.dark-mode .el-table th {
  background-color: var(--header-bg);
  color: var(--text-color);
  border-color: var(--border-color);
}

.dark-mode .el-table td {
  border-color: var(--border-color);
}

.dark-mode .el-menu {
  background-color: var(--aside-bg);
  border-color: var(--border-color);
}

.dark-mode .el-menu-item {
  color: var(--text-color);
}

.dark-mode .el-menu-item:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.dark-mode .el-menu-item.is-active {
  color: #409EFF;
  background-color: rgba(64, 158, 255, 0.2);
}

.dark-mode .el-input__wrapper {
  background-color: var(--card-bg);
  border-color: var(--border-color);
}

.dark-mode .el-input__inner {
  color: var(--text-color);
}

.dark-mode .el-dialog {
  background-color: var(--card-bg);
  color: var(--text-color);
  border-color: var(--border-color);
}

.dark-mode .el-dialog__header {
  border-color: var(--border-color);
}

.dark-mode .el-dialog__title {
  color: var(--text-color);
}

.dark-mode .el-form-item__label {
  color: var(--text-color);
}

.dark-mode .main {
  background-color: var(--bg-color) !important;
  color: var(--text-color);
}

/* 按钮样式 */
.dark-mode .el-button {
  background-color: var(--card-bg) !important;
  color: var(--text-color) !important;
  border-color: var(--border-color) !important;
}

.dark-mode .el-button:hover {
  background-color: rgba(255, 255, 255, 0.1) !important;
  border-color: var(--border-color) !important;
}

.dark-mode .el-button--primary {
  background-color: #409EFF !important;
  border-color: #409EFF !important;
  color: #fff !important;
}

.dark-mode .el-button--primary:hover {
  background-color: #66b1ff !important;
  border-color: #66b1ff !important;
}

/* 表格样式 */
.dark-mode .el-table__row {
  background-color: var(--card-bg) !important;
  color: var(--text-color) !important;
}

.dark-mode .el-table__row:hover {
  background-color: rgba(255, 255, 255, 0.05) !important;
}

/* 上传组件 */
.dark-mode .el-upload {
  background-color: var(--card-bg) !important;
  color: var(--text-color) !important;
}

/* 图表容器 */
.dark-mode .chart-container {
  background-color: var(--card-bg) !important;
  border-color: var(--border-color) !important;
}

.dark-mode .chart-header {
  color: var(--text-color) !important;
  border-bottom-color: var(--border-color) !important;
}

/* 表格表头 */
.dark-mode .el-table th {
  background-color: var(--header-bg) !important;
  color: var(--text-color) !important;
  border-color: var(--border-color) !important;
}

/* 卡片组件 */
.dark-mode .el-card {
  background-color: var(--card-bg) !important;
  border-color: var(--border-color) !important;
}

.dark-mode .el-card__header {
  background-color: var(--card-bg) !important;
  border-color: var(--border-color) !important;
  color: var(--text-color) !important;
}

.dark-mode .el-card__body {
  background-color: var(--card-bg) !important;
  color: var(--text-color) !important;
}

/* 表格单元格 */
.dark-mode .el-table td {
  border-color: var(--border-color) !important;
  color: var(--text-color) !important;
}

/* 修复:before伪元素样式 */
.dark-mode .el-table__inner-wrapper:before {
  background-color: var(--bg-color) !important;
}

.dark-mode *:before {
  background-color: var(--bg-color) !important;
  border-color: var(--border-color) !important;
  color: var(--text-color) !important;
}
</style>

<style scoped>
/* 重置 Element Plus 样式 */
:deep(.el-container) {
  margin: 0 !important;
  padding: 0 !important;
  border: none !important;
}

:deep(.el-aside) {
  margin: 0 !important;
  padding: 0 !important;
  border: none !important;
}

/* 主容器 */
.app-container {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  display: flex;
  flex-direction: row;
}

/* 侧边栏 */
.el-aside {
  flex: 0 0 200px;
  width: 200px !important;
  height: 100vh;
  background-color: #303133;
  color: #fff;
  overflow-y: auto;
  border-right: 1px solid #444;
}

/* 内容容器 */
.content-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

/* 头部 */
.header {
  background-color: #409EFF;
  color: #fff;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Microsoft YaHei', 'SimHei', Arial, sans-serif;
  font-size: 20px;
  font-weight: bold;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  border-bottom: 1px solid #3a8ee6;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  max-width: 1200px;
  padding: 0 20px;
}

.header h1 {
  margin: 0;
  padding: 0;
  font-size: 20px;
  font-weight: bold;
  line-height: 1;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-right: 10px;
  font-size: 14px;
}

.theme-toggle, .logout-btn {
  width: 40px !important;
  height: 40px !important;
  font-size: 18px;
  border-radius: 50% !important;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 0 !important;
  min-width: 40px !important;
}

.theme-toggle:hover, .logout-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  border-radius: 50%;
}

.theme-toggle:active, .logout-btn:active {
  transform: scale(0.95);
  border-radius: 50%;
}

/* 主内容区域 */
.main {
  padding: 20px;
  background-color: #f5f7fa;
  overflow-y: auto;
  flex: 1;
  min-width: 0;
}

/* 菜单样式 */
.el-menu-vertical-demo:not(.el-menu--collapse) {
  width: 200px;
  height: 100%;
  border-right: none !important;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .el-aside {
    flex: 0 0 180px;
    width: 180px !important;
  }
  
  .el-menu-vertical-demo:not(.el-menu--collapse) {
    width: 180px;
  }
  
  .header h1 {
    font-size: 18px;
  }
  
  .main {
    padding: 10px;
  }
}

/* 修复右侧空白和水平滚动条问题 */
body {
  overflow-x: hidden;
}

/* 黑夜模式下的样式 */
:deep(.dark-mode .header) {
  background-color: var(--header-bg);
  border-bottom-color: var(--border-color);
}

:deep(.dark-mode .main) {
  background-color: var(--bg-color);
}

:deep(.dark-mode .el-aside) {
  background-color: var(--aside-bg);
  border-right-color: var(--border-color);
}

:deep(.dark-mode .el-menu) {
  background-color: var(--aside-bg) !important;
  border-right-color: var(--border-color);
}

:deep(.dark-mode .el-menu-vertical-demo) {
  background-color: var(--aside-bg) !important;
  border-right-color: var(--border-color);
}

:deep(.dark-mode .el-menu--vertical) {
  background-color: var(--aside-bg) !important;
  border-right-color: var(--border-color);
}
</style>
