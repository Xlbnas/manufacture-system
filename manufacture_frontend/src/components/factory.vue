<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import ImportComponent from './ImportComponent.vue'
import * as ExcelJS from 'exceljs'

const factories = ref([])
const dialogVisible = ref(false)
// 导入相关
const importVisible = ref(false)
const importProgress = ref(0)
const importSuccessCount = ref(0)
const importErrorCount = ref(0)
const importErrors = ref([])
const form = ref({
  location: '',
  workshop: ''
})

onMounted(() => {
  fetchFactories()
})

const fetchFactories = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:9876/api/factories/')
    factories.value = response.data
  } catch (error) {
    console.error('Error fetching factories:', error)
  }
}

const openDialog = () => {
  form.value = {
    location: '',
    workshop: ''
  }
  dialogVisible.value = true
}

const saveFactory = async () => {
  try {
    // 处理车间输入，支持逗号分隔多个车间
    const workshops = form.value.workshop.split(/[,，]/).map(w => w.trim()).filter(w => w)
    
    // 为每个车间创建一个工厂记录
    for (const workshop of workshops) {
      await axios.post('http://127.0.0.1:9876/api/factories/', {
        name: `${form.value.location} ${workshop}车间`,
        location: form.value.location,
        workshop: workshop
      })
    }
    
    dialogVisible.value = false
    fetchFactories()
  } catch (error) {
    console.error('Error saving factory:', error)
  }
}

const deleteFactory = async (id) => {
  try {
    await axios.delete(`http://127.0.0.1:9876/api/factories/${id}/`)
    fetchFactories()
  } catch (error) {
    console.error('Error deleting factory:', error)
  }
}

// 导出功能
const exportFactories = async () => {
  const workbook = new ExcelJS.Workbook()
  const worksheet = workbook.addWorksheet('工厂数据')

  // 设置表头
  worksheet.columns = [
    { header: '地区', key: 'location', width: 20 },
    { header: '车间', key: 'workshop', width: 20 }
  ]

  // 填充数据
  factories.value.forEach(item => {
    worksheet.addRow({
      location: item.location,
      workshop: item.workshop
    })
  })

  // 生成Excel文件
  const buffer = await workbook.xlsx.writeBuffer()
  const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `工厂数据_${new Date().toISOString().split('T')[0]}.xlsx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// 导入功能
const openImportDialog = () => {
  importVisible.value = true
}

const validateImportData = (data) => {
  const errors = []
  data.forEach((row, index) => {
    if (!row.location) {
      errors.push(`第 ${index + 1} 行：地区不能为空`)
    }
    if (!row.workshop) {
      errors.push(`第 ${index + 1} 行：车间不能为空`)
    }
  })
  return errors
}

const handleImportSuccess = async (data) => {
  importProgress.value = 0
  importSuccessCount.value = 0
  importErrorCount.value = 0
  importErrors.value = []

  const total = data.length
  for (let i = 0; i < total; i++) {
    const row = data[i]
    try {
      // 保存数据
      await axios.post('http://127.0.0.1:9876/api/factories/', {
        name: `${row.location} ${row.workshop}车间`,
        location: row.location,
        workshop: row.workshop
      })
      importSuccessCount.value++
    } catch (error) {
      importErrorCount.value++
      importErrors.value.push(`第 ${i + 1} 行：${error.message}`)
    }
    importProgress.value = Math.round((i + 1) / total * 100)
  }

  await fetchFactories()
  importVisible.value = false
}
</script>

<template>
  <div class="factory-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
            <span>工厂管理</span>
            <div class="header-actions">
              <el-button type="primary" @click="openDialog">添加工厂</el-button>
              <el-button type="success" @click="exportFactories">导出数据</el-button>
              <el-button type="warning" @click="openImportDialog">导入数据</el-button>
            </div>
          </div>
      </template>
      <el-table :data="factories" style="width: 100%">
        <el-table-column label="工厂" width="250">
          <template #default="scope">
            {{ scope.row.location }} {{ scope.row.workshop }}车间
          </template>
        </el-table-column>
        <el-table-column prop="location" label="地区" width="180" />
        <el-table-column prop="workshop" label="车间" width="180" />
        <el-table-column label="操作">
          <template #default="scope">
            <el-button type="danger" @click="deleteFactory(scope.row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      title="添加工厂"
      width="500px"
    >
      <el-form :model="form" label-width="80px">
        <el-form-item label="地区">
          <el-input v-model="form.location" placeholder="例如：琴断口" />
        </el-form-item>
        <el-form-item label="车间">
          <el-input v-model="form.workshop" placeholder="例如：二，八（多个车间用逗号分隔）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveFactory">保存</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 导入组件 -->
    <ImportComponent
      v-model:visible="importVisible"
      :validate="validateImportData"
      @success="handleImportSuccess"
      :fields="['location', 'workshop']"
      :field-labels="{ location: '地区', workshop: '车间' }"
    />
  </div>
</template>

<style scoped>
.factory-management {
  padding: 20px;
  width: 100%;
  box-sizing: border-box;
}

.el-card {
  width: 100%;
  box-sizing: border-box;
}

.el-card__body {
  padding: 20px;
  box-sizing: border-box;
}

.el-table {
  width: 100%;
  box-sizing: border-box;
  max-height: 500px;
  overflow-y: auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.dialog-footer {
  width: 100%;
  display: flex;
  justify-content: flex-end;
}
</style>