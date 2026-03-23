<template>
  <el-dialog
    :model-value="localVisible"
    @update:model-value="localVisible = $event"
    :title="title"
    width="800px"
  >
    <div class="import-container">
      <!-- 文件上传区域 -->
      <div class="upload-section">
        <el-upload
          class="upload-demo"
          action="#"
          :auto-upload="false"
          :on-change="handleFileChange"
          accept=".xlsx,.xls,.csv"
          :show-file-list="false"
          drag
        >
          <el-icon class="el-icon--upload"><Upload /></el-icon>
          <div class="el-upload__text">
            拖拽文件到此处，或 <em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              支持上传 Excel (.xlsx, .xls) 和 CSV 文件
            </div>
          </template>
        </el-upload>
      </div>

      <!-- 预览区域 -->
      <div v-if="previewData.length > 0" class="preview-section">
        <h4>数据预览</h4>
        <el-table :data="previewData" style="width: 100%" border>
          <el-table-column
            v-for="(column, index) in columns"
            :key="index"
            :prop="column"
            :label="column"
          />
        </el-table>
      </div>

      <!-- 错误提示 -->
      <div v-if="errors.length > 0" class="error-section">
        <el-alert
          v-for="(error, index) in errors"
          :key="index"
          :title="error"
          type="error"
          show-icon
        />
      </div>

      <!-- 进度条 -->
      <div v-if="showProgress" class="progress-section">
        <el-progress :percentage="progress" status="success" />
        <div class="progress-text">{{ progressText }}</div>
      </div>
    </div>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="cancel">取消</el-button>
        <el-button
          type="primary"
          @click="confirmImport"
          :loading="loading"
          :disabled="!canImport"
        >
          确认导入
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import * as XLSX from 'xlsx'

// Props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: '导入数据'
  },
  validate: {
    type: Function,
    default: null
  },
  fields: {
    type: Array,
    default: () => []
  },
  fieldLabels: {
    type: Object,
    default: () => {}
  }
})

// Emits
const emit = defineEmits(['update:visible', 'success', 'import-error'])

// 响应式数据
const localVisible = ref(props.visible)
const file = ref(null)
const previewData = ref([])
const columns = ref([])
const errors = ref([])
const loading = ref(false)
const showProgress = ref(false)
const progress = ref(0)
const progressText = ref('')

// 计算属性
const canImport = computed(() => {
  return previewData.value.length > 0 && errors.value.length === 0
})

// 监听visible变化
watch(() => props.visible, (newValue) => {
  localVisible.value = newValue
})

// 监听localVisible变化
watch(() => localVisible.value, (newValue) => {
  emit('update:visible', newValue)
  if (!newValue) {
    resetState()
  }
})

// 处理文件变化
const handleFileChange = (uploadFile) => {
  if (!uploadFile) return
  
  const file = uploadFile.raw
  if (!file) return
  
  const ext = file.name.split('.').pop().toLowerCase()
  if (!['xlsx', 'xls', 'csv'].includes(ext)) {
    ElMessage.error('请上传Excel或CSV文件')
    return
  }

  parseFile(file)
}

// 解析文件
const parseFile = (file) => {
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const data = new Uint8Array(e.target.result)
      const workbook = XLSX.read(data, { type: 'array' })
      const firstSheetName = workbook.SheetNames[0]
      const worksheet = workbook.Sheets[firstSheetName]
      const jsonData = XLSX.utils.sheet_to_json(worksheet)
      
      if (jsonData.length === 0) {
        ElMessage.warning('文件中没有数据')
        return
      }

      // 提取列名
      columns.value = Object.keys(jsonData[0])
      previewData.value = jsonData
      errors.value = []

      // 验证数据
      if (props.validate) {
        errors.value = props.validate(jsonData)
      }
    } catch (error) {
      console.error('解析文件失败:', error)
      ElMessage.error('解析文件失败，请检查文件格式')
    }
  }
  reader.readAsArrayBuffer(file)
}

// 确认导入
const confirmImport = async () => {
  if (!canImport.value) return

  loading.value = true
  showProgress.value = true
  progress.value = 0
  progressText.value = '正在导入...'

  try {
    // 模拟导入过程
    for (let i = 0; i < 100; i += 10) {
      await new Promise(resolve => setTimeout(resolve, 100))
      progress.value = i
    }
    progress.value = 100
    progressText.value = '导入完成'

    // 延迟一下让用户看到完成状态
    await new Promise(resolve => setTimeout(resolve, 500))

    emit('success', previewData.value)
    ElMessage.success('导入成功')
    cancel()
  } catch (error) {
    console.error('导入失败:', error)
    ElMessage.error('导入失败，请重试')
    emit('import-error', error)
  } finally {
    loading.value = false
    showProgress.value = false
  }
}

// 取消
const cancel = () => {
  localVisible.value = false
}

// 重置状态
const resetState = () => {
  file.value = null
  previewData.value = []
  columns.value = []
  errors.value = []
  loading.value = false
  showProgress.value = false
  progress.value = 0
  progressText.value = ''
}
</script>

<style scoped>
.import-container {
  padding: 20px 0;
}

.upload-section {
  margin-bottom: 30px;
}

.preview-section {
  margin-bottom: 20px;
}

.preview-section h4 {
  margin: 0 0 15px 0;
  font-size: 16px;
  font-weight: bold;
}

.error-section {
  margin-bottom: 20px;
}

.progress-section {
  margin-top: 20px;
}

.progress-text {
  margin-top: 10px;
  text-align: center;
  color: #666;
}

.dialog-footer {
  width: 100%;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>