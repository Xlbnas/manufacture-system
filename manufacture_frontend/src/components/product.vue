<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '../utils/axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as ExcelJS from 'exceljs'
import {
  TEMPLATE_KEYS,
  templateLabelForKey,
  isKnownTemplateKey,
} from '../constants/productionTemplates.js'

const products = ref([])
const editDialogVisible = ref(false)
const syncing = ref(false)

const editForm = ref({
  id: '',
  name: '',
  colors: '',
  specifications: [],
  production_template_key: '',
})

// 尺码选项
const sizeOptions = ref([
  { value: 'XS', label: 'XS' },
  { value: 'S', label: 'S' },
  { value: 'M', label: 'M' },
  { value: 'L', label: 'L' },
  { value: 'XL', label: 'XL' },
  { value: '2XL', label: '2XL' },
  { value: '3XL', label: '3XL' },
  { value: '4XL', label: '4XL' },
  { value: '5XL', label: '5XL' }
])

// 生命周期
onMounted(() => {
  fetchProducts()
})

function extractProductsList(data) {
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.results)) return data.results
  return []
}

const fetchProducts = async () => {
  try {
    const response = await api.get('/products/')
    products.value = extractProductsList(response.data)
  } catch (error) {
    console.error('Error fetching products:', error)
  }
}

const productsByKey = computed(() => {
  const m = {}
  for (const p of products.value) {
    const k = p.production_template_key
    if (k) m[k] = p
  }
  return m
})

const templateProductRows = computed(() =>
  TEMPLATE_KEYS.map((templateKey) => {
    const p = productsByKey.value[templateKey]
    return {
      templateKey,
      templateLabel: templateLabelForKey(templateKey),
      id: p?.id,
      name: p?.name ?? '',
      colors: p?.colors ?? '',
      specifications: p?.specifications ?? '',
      missing: !p,
    }
  })
)

const orphanProducts = computed(() =>
  products.value.filter(
    (p) => p.production_template_key && !isKnownTemplateKey(p.production_template_key)
  )
)

const syncFromCatalog = async () => {
  syncing.value = true
  try {
    await api.post('/products/sync-from-catalog/')
    ElMessage.success('已按系统模板补全缺失行')
    await fetchProducts()
  } catch (e) {
    const d = e?.response?.data
    let msg = '同步失败'
    if (typeof d === 'string') msg = d
    else if (d?.detail) msg = String(d.detail)
    else if (d && typeof d === 'object') {
      const first = Object.values(d)[0]
      msg = Array.isArray(first) ? String(first[0]) : String(first)
    } else if (e?.message) msg = e.message
    ElMessage.error(msg)
  } finally {
    syncing.value = false
  }
}

const openEditTemplateRow = (row) => {
  const p = productsByKey.value[row.templateKey]
  if (!p) return
  editForm.value = {
    id: p.id,
    name: p.name,
    colors: p.colors,
    specifications: p.specifications ? p.specifications.split(',') : [],
    production_template_key: p.production_template_key,
  }
  editDialogVisible.value = true
}

const openEditOrphan = (product) => {
  editForm.value = {
    id: product.id,
    name: product.name,
    colors: product.colors,
    specifications: product.specifications ? product.specifications.split(',') : [],
    production_template_key: product.production_template_key,
  }
  editDialogVisible.value = true
}

const updateProduct = async () => {
  try {
    editForm.value.name = String(editForm.value.name || '')
    editForm.value.colors = String(editForm.value.colors || '').replace(/，/g, ',')
    let specs = Array.isArray(editForm.value.specifications)
      ? editForm.value.specifications.join(',')
      : String(editForm.value.specifications || '').replace(/，/g, ',')
    if (!specs.trim()) specs = '无'

    await api.patch(`/products/${editForm.value.id}/`, {
      name: editForm.value.name,
      colors: editForm.value.colors,
      specifications: specs,
    })
    editDialogVisible.value = false
    fetchProducts()
    ElMessage.success('已保存')
  } catch (error) {
    console.error('Error updating product:', error)
    const d = error.response?.data
    if (typeof d === 'object' && d) {
      const parts = []
      for (const [field, messages] of Object.entries(d)) {
        parts.push(`${field}: ${Array.isArray(messages) ? messages.join(', ') : messages}`)
      }
      ElMessage.error(parts.join('；') || '更新失败')
    } else {
      ElMessage.error('更新失败')
    }
  }
}

const deleteOrphanProduct = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除「${row.name}」？仅适用于迁移遗留等非模板线产品。`, '确认删除')
    await api.delete(`/products/${row.id}/`)
    ElMessage.success('已删除')
    fetchProducts()
  } catch (e) {
    if (e !== 'cancel') {
      const msg = e?.response?.data?.detail || e?.response?.data || e?.message || '删除失败'
      ElMessage.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    }
  }
}

// 导入导出功能
const exportProducts = async () => {
  try {
    // 显示导出进度提示
    const loading = ElMessage({
      message: '正在导出数据，请稍候...',
      type: 'info',
      duration: 0,
      showClose: true
    })
    
    // 创建Excel工作簿
    const workbook = new ExcelJS.Workbook()
    workbook.creator = '产品管理系统'
    workbook.lastModifiedBy = '产品管理系统'
    workbook.created = new Date()
    workbook.modified = new Date()
    
    // 添加工作表
    const worksheet = workbook.addWorksheet('产品记录')
    
    // 设置表头
    const headers = ['排产模板键', '产品名称', '颜色选项', '规格参数']
    worksheet.addRow(headers)
    
    // 设置表头样式
    worksheet.getRow(1).font = {
      bold: true,
      size: 12
    }
    worksheet.getRow(1).fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FFE0EBF5' }
    }
    
    // 设置列宽
    worksheet.columns = [
      { header: '排产模板键', key: 'key', width: 14 },
      { header: '产品名称', key: 'name', width: 20 },
      { header: '颜色选项', key: 'colors', width: 30 },
      { header: '规格参数', key: 'specifications', width: 30 }
    ]

    for (const product of products.value) {
      worksheet.addRow([
        product.production_template_key || '—',
        product.name,
        product.colors || '无',
        product.specifications || '无'
      ])
    }
    
    // 生成Excel文件
    const buffer = await workbook.xlsx.writeBuffer()
    const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `模板成品_${new Date().toISOString().split('T')[0]}.xlsx`
    link.click()
    URL.revokeObjectURL(url)
    
    // 关闭加载提示
    loading.close()
    
    // 显示完成反馈
    ElMessage({
      message: '导出完成！',
      type: 'success',
      duration: 3000
    })
  } catch (error) {
    console.error('Error exporting products:', error)
    ElMessage({
      message: '导出失败：' + (error.message || '未知错误'),
      type: 'error',
      duration: 3000
    })
  }
}

</script>

<template>
  <div class="product-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>模板成品</span>
          <div class="header-actions">
            <el-button type="primary" :loading="syncing" @click="syncFromCatalog">同步系统模板行</el-button>
            <el-button type="success" @click="exportProducts">导出</el-button>
          </div>
        </div>
      </template>
      <p class="hint">
        每条系统模板键对应一条成品档案（库存 SKU = 模板键 + 颜色 + 尺码）。缺行时点「同步系统模板行」；显示名与颜色/尺码提示可编辑，模板键不可改。
      </p>
      <el-table :data="templateProductRows" style="width: 100%" border>
        <el-table-column prop="templateKey" label="模板键" width="100" />
        <el-table-column prop="templateLabel" label="模板" width="100" />
        <el-table-column prop="name" label="显示名称" min-width="140" />
        <el-table-column prop="colors" label="颜色选项" width="180" />
        <el-table-column prop="specifications" label="规格参数" min-width="120" />
        <el-table-column label="状态" width="88">
          <template #default="{ row }">
            <el-tag v-if="row.missing" type="warning" size="small">待同步</el-tag>
            <el-tag v-else type="success" size="small">已建档</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              :disabled="row.missing"
              @click="openEditTemplateRow(row)"
            >
              编辑
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-card v-if="orphanProducts.length" shadow="never" style="margin-top: 16px">
        <template #header>迁移遗留（非当前模板清单）</template>
        <el-table :data="orphanProducts" size="small">
          <el-table-column prop="production_template_key" label="模板键" width="120" />
          <el-table-column prop="name" label="名称" />
          <el-table-column label="操作" width="160">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="openEditOrphan(row)">编辑</el-button>
              <el-button type="danger" link size="small" @click="deleteOrphanProduct(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-card>

    <el-dialog v-model="editDialogVisible" title="编辑模板成品" width="520px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="模板键">
          <el-input :model-value="editForm.production_template_key" disabled />
        </el-form-item>
        <el-form-item label="显示名称" required>
          <el-input v-model="editForm.name" placeholder="可与模板中文名不同" style="width: 100%" />
        </el-form-item>
        <el-form-item label="颜色选项">
          <el-input v-model="editForm.colors" placeholder="逗号分隔，供调拨与提示" style="width: 100%" />
        </el-form-item>
        <el-form-item label="规格参数">
          <el-select
            v-model="editForm.specifications"
            multiple
            placeholder="选择尺码"
            style="width: 100%"
          >
            <el-option
              v-for="option in sizeOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="updateProduct">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.product-management {
  padding: 20px 0;
}

.hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
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
  height: 36px; /* 确保所有按钮在同一高度 */
}

.header-actions .el-button {
  height: 36px; /* 统一按钮高度 */
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-actions .upload-demo {
  height: 36px; /* 确保上传组件与按钮同高 */
  display: flex;
  align-items: center;
}

.header-actions .upload-demo .el-upload {
  height: 100%;
  display: flex;
  align-items: center;
}

.dialog-footer {
  width: 100%;
  display: flex;
  justify-content: flex-end;
}

:deep(.dark-mode .product-management .el-select__wrapper) {
  background-color: #30343d !important;
  box-shadow: 0 0 0 1px #4a4f58 inset !important;
}

:deep(.dark-mode .product-management .el-select__wrapper.is-hovering) {
  box-shadow: 0 0 0 1px #6b7280 inset !important;
}

:deep(.dark-mode .product-management .el-select .el-tag) {
  background-color: #4a505c !important;
  border-color: #5a6270 !important;
  color: #f2f3f5 !important;
}
</style>