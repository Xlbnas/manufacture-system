import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import axios from 'axios'
import { createPinia } from 'pinia'
import router from './router'
import { useAuthStore } from './stores/auth.js'

const app = createApp(App)
const pinia = createPinia()

app.use(ElementPlus)
app.use(pinia)
app.use(router)
app.config.globalProperties.$axios = axios

// 初始化认证状态
const authStore = useAuthStore()
authStore.initAuth().then(() => {
  app.mount('#app')
})
