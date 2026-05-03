<template>
  <div class="ai-summary-page">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>AI 数据总结助手</span>
          <span class="header-tip">直接基于系统数据查询与总结，也支持补充文本</span>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="系统数据分析" name="data">
          <el-form label-position="top">
            <el-form-item label="总结模板">
              <el-select v-model="templateKey" style="width: 300px">
                <el-option v-for="item in templates" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>

            <el-form-item label="数据范围">
              <el-select v-model="dataScope" style="width: 300px">
                <el-option v-for="item in scopes" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
            <el-alert
              v-if="dataScope === 'all'"
              type="info"
              :closable="false"
              title="全量数据分析耗时较长，建议优先选择具体范围（如出库/仓库）以提高成功率。"
              style="margin-bottom: 12px"
            />

            <el-form-item label="你想让 AI 做什么（必填）">
              <el-input
                v-model="query"
                type="textarea"
                :rows="4"
                placeholder="例如：总结最近出库异常，并给出明天的处理优先级"
                maxlength="1000"
                show-word-limit
              />
            </el-form-item>

            <el-form-item label="补充文本（可选）">
              <el-input
                v-model="content"
                type="textarea"
                :rows="6"
                placeholder="可粘贴会议纪要/临时说明，AI会和系统数据一起分析"
                maxlength="20000"
                show-word-limit
              />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="历史记录" name="history">
          <el-empty v-if="history.length === 0" description="暂无历史记录" />
          <div v-else class="history-list">
            <el-card v-for="item in history" :key="item.id" class="history-item" shadow="never">
              <div class="history-meta">
                <span>{{ item.time }}</span>
                <el-tag size="small">{{ templateLabel(item.templateKey) }}</el-tag>
                <el-tag size="small" type="info">{{ scopeLabel(item.dataScope) }}</el-tag>
              </div>
              <div class="history-query">{{ item.query }}</div>
              <el-input :model-value="item.summary" type="textarea" :rows="6" readonly />
              <div class="history-actions">
                <el-space :size="8" wrap>
                  <el-button size="small" @click="reuseHistory(item)">复用到分析区</el-button>
                  <el-button size="small" type="danger" @click="removeHistory(item)">删除</el-button>
                </el-space>
              </div>
            </el-card>
          </div>
        </el-tab-pane>

        <el-tab-pane label="AI配置" name="config">
          <el-alert
            type="warning"
            :closable="false"
            title="配置将写入后端 manufacture_backend/.env，仅管理员可修改。"
            style="margin-bottom: 12px"
          />
          <el-form label-position="top">
            <el-form-item label="当前 Key 状态">
              <el-tag :type="config.keyConfigured ? 'success' : 'danger'">
                {{ config.keyConfigured ? `已配置 (${config.maskedKey || ''})` : '未配置' }}
              </el-tag>
            </el-form-item>
            <el-form-item label="SiliconFlow API Key">
              <el-input v-model="configForm.apiKey" type="password" show-password placeholder="请输入新的 API Key" />
            </el-form-item>
            <el-form-item label="模型">
              <el-select
                v-model="configForm.model"
                filterable
                allow-create
                default-first-option
                placeholder="选择常用模型或直接输入模型 id"
                style="width: 100%"
              >
                <el-option v-for="m in modelPresets" :key="m" :label="m" :value="m" />
              </el-select>
            </el-form-item>
            <el-form-item label="API URL">
              <el-input v-model="configForm.apiUrl" />
            </el-form-item>
            <el-button type="primary" :loading="savingConfig" @click="saveConfig">保存配置</el-button>
            <el-button @click="loadConfig">刷新配置</el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <div class="actions" v-if="activeTab === 'data'">
        <el-button type="primary" :loading="loading" @click="handleSummarize">
          基于系统数据生成总结
        </el-button>
        <el-button @click="resetInput">清空输入</el-button>
      </div>
      <div class="actions" v-else-if="activeTab === 'history'">
        <el-button type="warning" @click="clearHistory">清空历史</el-button>
      </div>

      <el-divider />

      <div class="result-block">
        <h3>总结结果</h3>
        <el-alert
          v-if="status.text"
          :type="status.type"
          :closable="false"
          :title="status.text"
          class="summary-status-alert"
          style="margin-bottom: 12px"
        />
        <el-empty v-if="!summary && !loading" description="暂无结果" />
        <div v-if="loading && !summary" class="summary-loading">
          <div v-for="line in 8" :key="line" class="loading-line" />
        </div>
        <div
          v-if="summary"
          id="ai-summary-markdown"
          class="markdown-view"
          v-html="renderedSummary"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../utils/axios.js'
import { useAuthStore } from '../stores/auth.js'
import { deleteWithUndo } from '../composables/deleteWithUndo.js'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
const authStore = useAuthStore()
let summarizeAbortController = null

const STORAGE_KEY = 'ai_summary_history'

/** SiliconFlow 等常用模型 id（可下拉选择或直接输入） */
const modelPresets = [
  'deepseek-ai/DeepSeek-V4-Flash',
  'deepseek-ai/DeepSeek-V3.2',
  'Qwen/Qwen2.5-72B-Instruct',
  'Qwen/Qwen2.5-32B-Instruct',
  'THUDM/glm-4-9b-chat',
  'meta-llama/Llama-3.3-70B-Instruct',
]

const activeTab = ref('data')
const templateKey = ref('general')
const dataScope = ref('all')
const query = ref('')
const content = ref('')
const summary = ref('')
const loading = ref(false)
const history = ref([])
const savingConfig = ref(false)
const status = ref({ type: 'info', text: '' })
const config = ref({
  keyConfigured: false,
  maskedKey: '',
  model: 'deepseek-ai/DeepSeek-V4-Flash',
  apiUrl: 'https://api.siliconflow.cn/v1/chat/completions'
})
const configForm = ref({
  apiKey: '',
  model: 'deepseek-ai/DeepSeek-V4-Flash',
  apiUrl: 'https://api.siliconflow.cn/v1/chat/completions'
})

const escapeHtml = (str = '') => str
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#39;')

const markdownToHtml = (md = '') => {
  let html = escapeHtml(md)
  html = html
    .replace(/^### (.*)$/gm, '<h3>$1</h3>')
    .replace(/^## (.*)$/gm, '<h2>$1</h2>')
    .replace(/^# (.*)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')

  // 处理无序列表
  html = html.replace(/(?:^|\n)- (.*?)(?=\n(?!- )|$)/gs, (match) => {
    const items = match
      .trim()
      .split('\n')
      .filter(line => line.startsWith('- '))
      .map(line => `<li>${line.slice(2)}</li>`)
      .join('')
    return `\n<ul>${items}</ul>\n`
  })

  // 普通换行转段落
  html = html
    .split(/\n{2,}/)
    .map(block => {
      const trimmed = block.trim()
      if (!trimmed) return ''
      if (/^<h[1-3]>|^<ul>|^<pre>|^<blockquote>/.test(trimmed)) return trimmed
      return `<p>${trimmed.replaceAll('\n', '<br/>')}</p>`
    })
    .join('\n')
  return html
}

const renderedSummary = computed(() => markdownToHtml(summary.value || ''))

const templates = [
  { label: '通用总结', value: 'general' },
  { label: '日报总结', value: 'daily' },
  { label: '周报总结', value: 'weekly' },
  { label: '风险排查', value: 'risk' }
]

const scopes = [
  { label: '全量数据', value: 'all' },
  { label: '工厂', value: 'factory' },
  { label: '原料', value: 'material' },
  { label: '产品', value: 'product' },
  { label: '生产计划', value: 'plan' },
  { label: '仓库', value: 'warehouse' },
  { label: '出库', value: 'outbound' }
]

const loadHistory = () => {
  try {
    history.value = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
  } catch {
    history.value = []
  }
}

const persistHistory = () => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history.value.slice(0, 20)))
}

const templateLabel = (value) => templates.find(t => t.value === value)?.label || value
const scopeLabel = (value) => scopes.find(s => s.value === value)?.label || value

const appendHistory = (item) => {
  history.value.unshift(item)
  persistHistory()
}

const removeHistory = async (item) => {
  const snapshot = JSON.parse(JSON.stringify(item))
  try {
    await deleteWithUndo({
      confirmMessage: '确定删除这条历史记录？',
      deleteFn: async () => {
        history.value = history.value.filter((x) => x.id !== item.id)
        persistHistory()
      },
      undo: {
        handler: async () => {
          if (!history.value.some((x) => x.id === snapshot.id)) {
            history.value.unshift(snapshot)
            persistHistory()
          }
        },
      },
      successMessage: '历史记录已删除',
    })
  } catch (e) {
    console.error(e)
  }
}

const clearHistory = async () => {
  const backup = JSON.parse(JSON.stringify(history.value))
  try {
    await deleteWithUndo({
      confirmMessage: '确定清空全部 AI 历史记录？',
      deleteFn: async () => {
        history.value = []
        persistHistory()
      },
      undo: {
        handler: async () => {
          history.value = backup
          persistHistory()
        },
      },
      successMessage: '历史已清空',
    })
  } catch (e) {
    console.error(e)
  }
}

const reuseHistory = (item) => {
  templateKey.value = item.templateKey
  dataScope.value = item.dataScope
  query.value = item.query
  content.value = item.content || ''
  summary.value = item.summary || ''
  activeTab.value = 'data'
}

const resetInput = () => {
  query.value = ''
  content.value = ''
  status.value = { type: 'info', text: '' }
}

const loadConfig = async () => {
  try {
    const resp = await api.get('/ai/config/')
    config.value = {
      keyConfigured: !!resp.data?.key_configured,
      maskedKey: resp.data?.masked_key || '',
      model: resp.data?.model || 'deepseek-ai/DeepSeek-V4-Flash',
      apiUrl: resp.data?.api_url || 'https://api.siliconflow.cn/v1/chat/completions'
    }
    configForm.value.model = config.value.model
    configForm.value.apiUrl = config.value.apiUrl
  } catch (err) {
    ElMessage.error(err?.response?.data?.error || '读取 AI 配置失败')
  }
}

const saveConfig = async () => {
  if (!configForm.value.apiKey.trim()) {
    ElMessage.warning('请输入 API Key')
    return
  }
  savingConfig.value = true
  try {
    const resp = await api.put('/ai/config/', {
      api_key: configForm.value.apiKey.trim(),
      model: configForm.value.model.trim(),
      api_url: configForm.value.apiUrl.trim()
    })
    ElMessage.success(resp.data?.message || '保存成功')
    configForm.value.apiKey = ''
    await loadConfig()
  } catch (err) {
    ElMessage.error(err?.response?.data?.error || '保存配置失败')
  } finally {
    savingConfig.value = false
  }
}

/** 解析一块 SSE（以空行分隔事件），返回 { text?, error?, done? } */
const parseSseBlock = (block) => {
  const lines = block.split('\n')
  for (const line of lines) {
    const L = line.trim()
    if (!L.startsWith('data:')) continue
    const raw = L.startsWith('data: ') ? L.slice(6).trim() : L.slice(5).trim()
    if (raw === '[DONE]') return { done: true }
    try {
      const o = JSON.parse(raw)
      if (o.d) return { done: true }
      if (o.e) return { error: String(o.e) }
      if (o.t) return { text: String(o.t) }
    } catch {
      /* ignore non-JSON line */
    }
  }
  return {}
}

const handleSummarize = async () => {
  if (!query.value.trim()) {
    ElMessage.warning('请先输入你要分析的问题')
    return
  }
  summarizeAbortController?.abort()
  summarizeAbortController = new AbortController()
  const signal = summarizeAbortController.signal

  loading.value = true
  status.value = { type: 'info', text: 'AI 正在读取系统数据并生成总结，请稍候...' }
  summary.value = ''
  let streamError = null

  try {
    const resp = await fetch(`${API_BASE}/ai/summarize/stream/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(authStore.accessToken ? { Authorization: `Bearer ${authStore.accessToken}` } : {}),
      },
      body: JSON.stringify({
        query: query.value,
        content: content.value,
        template_key: templateKey.value,
        data_scope: dataScope.value,
      }),
      credentials: 'include',
      signal,
    })

    if (!resp.ok) {
      let msg = `请求失败 (${resp.status})`
      try {
        const j = await resp.json()
        if (j?.error) msg = j.error
      } catch {
        /* 可能是 HTML 错误页 */
      }
      status.value = { type: 'error', text: msg }
      ElMessage.error(msg)
      return
    }

    const reader = resp.body?.getReader()
    if (!reader) {
      const msg = '浏览器不支持流式读取'
      status.value = { type: 'error', text: msg }
      ElMessage.error(msg)
      return
    }

    const decoder = new TextDecoder()
    let buffer = ''
    let closed = false

    while (!closed) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() ?? ''
      for (const part of parts) {
        const trimmed = part.trim()
        if (!trimmed) continue
        const ev = parseSseBlock(trimmed)
        if (ev.error) {
          streamError = ev.error
          closed = true
          break
        }
        if (ev.text) {
          summary.value += ev.text
          if (status.value.type === 'info') {
            status.value = { type: 'info', text: '正在输出总结（流式）…' }
          }
        }
        if (ev.done) {
          closed = true
          break
        }
      }
    }

    if (buffer.trim()) {
      const ev = parseSseBlock(buffer.trim())
      if (ev.error) streamError = ev.error
      if (ev.text) summary.value += ev.text
    }

    if (signal.aborted) {
      status.value = { type: 'warning', text: '已取消生成' }
      return
    }

    if (streamError) {
      status.value = { type: 'error', text: streamError }
      ElMessage.error(streamError)
      return
    }

    if (!summary.value.trim()) {
      status.value = { type: 'warning', text: 'AI 返回为空，请调整问题后重试。' }
      ElMessage.warning('模型返回为空，请重试')
    } else {
      status.value = { type: 'success', text: 'AI 总结生成成功。' }
      appendHistory({
        id: `${Date.now()}`,
        time: new Date().toLocaleString(),
        templateKey: templateKey.value,
        dataScope: dataScope.value,
        query: query.value,
        content: content.value,
        summary: summary.value,
      })
    }
  } catch (err) {
    if (err?.name === 'AbortError') {
      status.value = { type: 'warning', text: '已取消生成' }
      return
    }
    const msg = err?.message || '总结失败，请稍后重试'
    status.value = { type: 'error', text: msg }
    ElMessage.error(msg)
  } finally {
    loading.value = false
    summarizeAbortController = null
  }
}

onMounted(async () => {
  loadHistory()
  await loadConfig()
})

onUnmounted(() => {
  summarizeAbortController?.abort()
})
</script>

<style scoped>
.ai-summary-page {
  padding: 20px 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-tip {
  color: #909399;
  font-size: 13px;
}

.actions {
  display: flex;
  gap: 10px;
}

.result-block h3 {
  margin: 0 0 12px 0;
}

.summary-loading {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.loading-line {
  height: 14px;
  border-radius: 6px;
  background: linear-gradient(90deg, #d8dbe2 25%, #eef1f6 50%, #d8dbe2 75%);
  background-size: 200% 100%;
  animation: shimmer 1.2s ease-in-out infinite;
}

.loading-line:nth-child(1) { width: 100%; }
.loading-line:nth-child(2) { width: 35%; }
.loading-line:nth-child(3) { width: 100%; }
.loading-line:nth-child(4) { width: 100%; }
.loading-line:nth-child(5) { width: 100%; }
.loading-line:nth-child(6) { width: 100%; }
.loading-line:nth-child(7) { width: 100%; }
.loading-line:nth-child(8) { width: 62%; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.markdown-view {
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  padding: 14px;
  background: #ffffff;
  color: #303133;
  line-height: 1.7;
  white-space: normal;
}

.markdown-view :deep(p) {
  margin: 0 0 10px 0;
}

.markdown-view :deep(ul),
.markdown-view :deep(ol) {
  margin: 8px 0 12px 20px;
}

.markdown-view :deep(code) {
  background: #f2f4f8;
  border-radius: 4px;
  padding: 2px 6px;
}

.markdown-view :deep(pre) {
  background: #f2f4f8;
  padding: 10px;
  border-radius: 8px;
  overflow: auto;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-item {
  border: 1px solid #ebeef5;
}

.history-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.history-query {
  font-weight: 600;
  margin-bottom: 8px;
}

.history-actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}

/* 暗黑模式下拉框可读性修复 */
:global(.dark-mode) .ai-summary-page .el-select__wrapper {
  background-color: #30343d !important;
  box-shadow: 0 0 0 1px #4a4f58 inset !important;
}

:global(.dark-mode) .ai-summary-page .el-select__selected-item,
:global(.dark-mode) .ai-summary-page .el-select__placeholder,
:global(.dark-mode) .ai-summary-page .el-select__input {
  color: #f2f3f5 !important;
}

/* 暗色下字数统计（el-textarea 的 el-input__count）可读性 */
:global(.dark-mode) .ai-summary-page .el-textarea .el-input__count,
:global(.dark-mode) .ai-summary-page .el-input__count {
  color: #b5bcc8 !important;
  background: transparent !important;
}

:global(.dark-mode) .ai-summary-page .loading-line {
  background: linear-gradient(90deg, #3b414c 25%, #4a5160 50%, #3b414c 75%);
  background-size: 200% 100%;
}

:global(.dark-mode) .ai-summary-page .summary-status-alert.el-alert--success.is-light {
  background-color: rgba(103, 194, 58, 0.16) !important;
  border-color: rgba(103, 194, 58, 0.35) !important;
}

:global(.dark-mode) .ai-summary-page .summary-status-alert.el-alert--success .el-alert__title {
  color: #b3e19d !important;
}

:global(.dark-mode) .ai-summary-page .summary-status-alert .el-alert__title {
  color: #e8eaed !important;
}

:global(.dark-mode) .ai-summary-page .el-alert.is-light {
  border-color: #4a4f58 !important;
}

:global(.dark-mode) .ai-summary-page .el-alert--info.is-light {
  background-color: rgba(64, 158, 255, 0.14) !important;
  border-color: rgba(64, 158, 255, 0.35) !important;
}

:global(.dark-mode) .ai-summary-page .el-alert--info .el-alert__title {
  color: #9ecfff !important;
}

:global(.dark-mode) .ai-summary-page .el-alert--warning.is-light {
  background-color: rgba(230, 162, 60, 0.14) !important;
  border-color: rgba(230, 162, 60, 0.35) !important;
}

:global(.dark-mode) .ai-summary-page .el-alert--warning .el-alert__title {
  color: #f3d19e !important;
}

:global(.dark-mode) .ai-summary-page .el-alert--error.is-light {
  background-color: rgba(245, 108, 108, 0.14) !important;
  border-color: rgba(245, 108, 108, 0.35) !important;
}

:global(.dark-mode) .ai-summary-page .el-alert--error .el-alert__title {
  color: #fab6b6 !important;
}

:global(.dark-mode) .ai-summary-page .markdown-view {
  background: #2f343d;
  border-color: #4a4f58;
  color: #f2f3f5;
}

:global(.dark-mode) .ai-summary-page .markdown-view :deep(code),
:global(.dark-mode) .ai-summary-page .markdown-view :deep(pre) {
  background: #262a31;
  color: #e8eaed;
}
</style>

<style>
html.dark-mode #ai-summary-markdown {
  background: #2f343d !important;
  border-color: #4a4f58 !important;
  color: #e8eaed !important;
}

html.dark-mode #ai-summary-markdown :is(h1, h2, h3, h4, p, li, strong, em, ul, ol) {
  color: #e8eaed !important;
  background-color: transparent !important;
}

html.dark-mode #ai-summary-markdown :is(code, pre) {
  background: #262a31 !important;
  color: #dce1ea !important;
}

html.dark-mode .ai-summary-page .header-tip {
  color: #a8b0bd !important;
}

html.dark-mode .ai-summary-page .result-block > h3 {
  color: #e8eaed !important;
}

html.dark-mode .ai-summary-page .history-item {
  border-color: #4a4f58 !important;
  background-color: #2c3038 !important;
}

html.dark-mode .ai-summary-page .history-query {
  color: #f2f3f5 !important;
}
</style>
