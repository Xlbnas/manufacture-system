<template>
  <div class="system-backup">
    <el-card>
      <template #header>
        <div class="card-header">
          <div>
            <h2>系统备份</h2>
            <p>导出或恢复完整生产数据，包含数据库和上传附件。</p>
          </div>
          <el-button type="primary" :loading="exporting" @click="exportBackup">
            导出完整备份
          </el-button>
        </div>
      </template>

      <el-alert
        class="safety-alert"
        title="生产数据安全提示"
        type="warning"
        show-icon
        :closable="false"
        description="恢复备份会覆盖当前数据库和附件。系统会在恢复前自动保存一份当前备份，但仍建议先手动导出一份并妥善保存。"
      />

      <div class="section">
        <h3>备份包内容</h3>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="格式">ZIP 压缩包</el-descriptions-item>
          <el-descriptions-item label="包含">db.sqlite3 数据库、media 附件、manifest 校验文件</el-descriptions-item>
          <el-descriptions-item label="权限">仅超级管理员可导出和恢复</el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="section">
        <h3>恢复备份</h3>
        <el-upload
          class="backup-upload"
          action="#"
          accept=".zip"
          :auto-upload="false"
          :show-file-list="false"
          :on-change="handleFileChange"
          drag
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">拖拽备份 ZIP 到这里，或 <em>点击选择</em></div>
          <template #tip>
            <div class="el-upload__tip">选择后会先检查备份包，不会立即恢复。</div>
          </template>
        </el-upload>

        <el-card v-if="selectedFile" class="inspect-card" shadow="never">
          <template #header>
            <div class="inspect-header">
              <span>已选择：{{ selectedFile.name }}</span>
              <el-button link type="primary" :loading="inspecting" @click="inspectBackup">
                重新检查
              </el-button>
            </div>
          </template>

          <el-descriptions v-if="backupInfo" :column="2" border>
            <el-descriptions-item label="备份时间">{{ formatDate(backupInfo.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="格式版本">{{ backupInfo.format_version }}</el-descriptions-item>
            <el-descriptions-item label="数据库大小">{{ formatBytes(backupInfo.database_size) }}</el-descriptions-item>
            <el-descriptions-item label="附件数量">{{ backupInfo.media_file_count }}</el-descriptions-item>
            <el-descriptions-item label="附件总大小">{{ formatBytes(backupInfo.media_total_size) }}</el-descriptions-item>
            <el-descriptions-item label="数据库校验">{{ shortHash(backupInfo.database_sha256) }}</el-descriptions-item>
          </el-descriptions>

          <el-alert
            v-if="inspectError"
            class="restore-alert"
            :title="inspectError"
            type="error"
            show-icon
            :closable="false"
          />
        </el-card>
      </div>

      <div class="section restore-section">
        <h3>确认恢复</h3>
        <el-alert
          class="restore-alert"
          title="这是高风险操作"
          type="error"
          show-icon
          :closable="false"
          description="恢复会覆盖当前生产数据。请输入确认文本后才能执行。"
        />
        <el-input
          v-model="confirmText"
          class="confirm-input"
          :placeholder="`请输入：${requiredConfirmText}`"
          clearable
        />
        <el-button
          type="danger"
          :loading="restoring"
          :disabled="!canRestore"
          @click="restoreBackup"
        >
          恢复此备份
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import api from '../utils/axios'
import router from '../router'
import { useAuthStore } from '../stores/auth'

const requiredConfirmText = '我确认恢复备份'
const exporting = ref(false)
const inspecting = ref(false)
const restoring = ref(false)
const selectedFile = ref(null)
const backupInfo = ref(null)
const inspectError = ref('')
const confirmText = ref('')
const authStore = useAuthStore()

const canRestore = computed(() => (
  selectedFile.value &&
  backupInfo.value &&
  confirmText.value.trim() === requiredConfirmText.valueOf() &&
  !restoring.value
))

const formatBytes = (bytes) => {
  const value = Number(bytes || 0)
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  if (value < 1024 * 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`
  return `${(value / 1024 / 1024 / 1024).toFixed(1)} GB`
}

const formatDate = (value) => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

const shortHash = (hash) => {
  if (!hash) return '-'
  return `${hash.slice(0, 10)}...${hash.slice(-8)}`
}

const getFilename = (disposition) => {
  const fallback = `manufacture-backup-${new Date().toISOString().slice(0, 10)}.zip`
  if (!disposition) return fallback
  const match = disposition.match(/filename="?([^"]+)"?/i)
  return match?.[1] || fallback
}

const exportBackup = async () => {
  exporting.value = true
  try {
    const response = await api.get('/system/backup/export/', {
      responseType: 'blob'
    })
    const blob = new Blob([response.data], { type: 'application/zip' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = getFilename(response.headers['content-disposition'])
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
    ElMessage.success('备份已开始下载')
  } catch (error) {
    ElMessage.error(error?.response?.data?.error || '导出备份失败')
  } finally {
    exporting.value = false
  }
}

const handleFileChange = (uploadFile) => {
  const file = uploadFile?.raw
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.zip')) {
    ElMessage.error('请上传 ZIP 备份包')
    return
  }
  selectedFile.value = file
  backupInfo.value = null
  inspectError.value = ''
  confirmText.value = ''
  inspectBackup()
}

const buildFormData = () => {
  const formData = new FormData()
  formData.append('file', selectedFile.value)
  return formData
}

const inspectBackup = async () => {
  if (!selectedFile.value) return
  inspecting.value = true
  inspectError.value = ''
  backupInfo.value = null
  try {
    const response = await api.post('/system/backup/inspect/', buildFormData())
    backupInfo.value = response.data
    ElMessage.success('备份包检查通过')
  } catch (error) {
    inspectError.value = error?.response?.data?.error || '备份包检查失败'
    ElMessage.error(inspectError.value)
  } finally {
    inspecting.value = false
  }
}

const restoreBackup = async () => {
  if (!canRestore.value) return
  try {
    await ElMessageBox.confirm(
      '恢复会覆盖当前数据库和附件。系统会先自动保存当前状态，确定继续吗？',
      '确认恢复备份',
      {
        confirmButtonText: '确定恢复',
        cancelButtonText: '取消',
        type: 'error'
      }
    )
  } catch {
    return
  }

  restoring.value = true
  try {
    const formData = buildFormData()
    formData.append('confirm_text', confirmText.value.trim())
    await api.post('/system/backup/restore/', formData, {
      timeout: 120000
    })
    ElMessage.success('恢复完成，请重新登录')
    await authStore.logout()
    router.push('/login')
  } catch (error) {
    ElMessage.error(error?.response?.data?.error || '恢复备份失败')
  } finally {
    restoring.value = false
  }
}
</script>

<style scoped>
.system-backup {
  max-width: 1080px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: center;
}

.card-header h2 {
  margin: 0 0 6px;
}

.card-header p {
  margin: 0;
  color: #606266;
}

.safety-alert,
.restore-alert {
  margin-bottom: 20px;
}

.section {
  margin-top: 24px;
}

.section h3 {
  margin: 0 0 14px;
}

.backup-upload {
  margin-bottom: 18px;
}

.inspect-card {
  margin-top: 16px;
}

.inspect-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.restore-section {
  border-top: 1px solid #ebeef5;
  padding-top: 24px;
}

.confirm-input {
  max-width: 420px;
  margin: 0 12px 12px 0;
}

.dark-mode .card-header p {
  color: #b8beca;
}

.dark-mode .restore-section {
  border-top-color: var(--border-color);
}
</style>
