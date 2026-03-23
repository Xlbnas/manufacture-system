<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import * as ExcelJS from 'exceljs'
import ImportComponent from './ImportComponent.vue'

// 响应式数据
const products = ref([])
const dialogVisible = ref(false)
const editDialogVisible = ref(false)
// 导入相关
const importVisible = ref(false)
const importProgress = ref(0)
const importSuccessCount = ref(0)
const importErrorCount = ref(0)
const importErrors = ref([])
const form = ref({
  name: '',
  colors: '',
  specifications: []
})
const editForm = ref({
  id: '',
  name: '',
  colors: '',
  specifications: []
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

// 数据获取
const fetchProducts = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:9876/api/products/')
    products.value = response.data
  } catch (error) {
    console.error('Error fetching products:', error)
  }
}

// 表单操作
const openDialog = () => {
  form.value = {
    name: '',
    colors: '',
    specifications: ''
  }
  dialogVisible.value = true
}

const openEditDialog = (product) => {
  editForm.value = {
    id: product.id,
    name: product.name,
    colors: product.colors,
    specifications: product.specifications ? product.specifications.split(',') : []
  }
  editDialogVisible.value = true
}

const saveProduct = async () => {
  try {
    // 验证产品名称是否为空
    if (!form.value.name || form.value.name.trim() === '') {
      alert('产品名称不能为空')
      return
    }
    
    // 确保所有字段都是字符串类型
    form.value.name = String(form.value.name || '')
    form.value.colors = String(form.value.colors || '').replace(/，/g, ',')
    form.value.specifications = Array.isArray(form.value.specifications) ? form.value.specifications.join(',') : String(form.value.specifications || '').replace(/，/g, ',')
    
    // 确保specifications字段不为空
    if (!form.value.specifications || form.value.specifications.trim() === '') {
      form.value.specifications = '无'
    }
    
    console.log('Sending product data:', form.value)
    console.log('Data types:', {
      name: typeof form.value.name,
      colors: typeof form.value.colors,
      specifications: typeof form.value.specifications
    })
    
    const response = await axios.post('http://127.0.0.1:9876/api/products/', form.value)
    console.log('Response:', response)
    dialogVisible.value = false
    fetchProducts()
  } catch (error) {
    console.error('Error saving product:', error)
    console.error('Error response:', error.response)
    if (error.response && error.response.data) {
      console.error('Error data:', error.response.data)
      // 显示具体的错误信息
      if (typeof error.response.data === 'object') {
        let errorMessages = ''
        for (const [field, messages] of Object.entries(error.response.data)) {
          if (Array.isArray(messages)) {
            errorMessages += `${field}: ${messages.join(', ')}\n`
          } else {
            errorMessages += `${field}: ${messages}\n`
          }
        }
        alert('保存失败:\n' + errorMessages)
      } else {
        alert('保存失败: ' + error.response.data)
      }
    } else {
      console.error('Error without response:', error.message)
      alert('保存失败: ' + error.message)
    }
  }
}

const updateProduct = async () => {
  try {
    // 确保所有字段都是字符串类型
    editForm.value.name = String(editForm.value.name || '')
    editForm.value.colors = String(editForm.value.colors || '').replace(/，/g, ',')
    editForm.value.specifications = Array.isArray(editForm.value.specifications) ? editForm.value.specifications.join(',') : String(editForm.value.specifications || '').replace(/，/g, ',')
    
    // 确保specifications字段不为空
    if (!editForm.value.specifications || editForm.value.specifications.trim() === '') {
      editForm.value.specifications = '无'
    }
    
    console.log('Sending update data:', editForm.value)
    console.log('Data types:', {
      name: typeof editForm.value.name,
      colors: typeof editForm.value.colors,
      specifications: typeof editForm.value.specifications
    })
    
    await axios.put(`http://127.0.0.1:9876/api/products/${editForm.value.id}/`, editForm.value)
    editDialogVisible.value = false
    fetchProducts()
  } catch (error) {
    console.error('Error updating product:', error)
    if (error.response && error.response.data) {
      console.error('Error data:', error.response.data)
      if (typeof error.response.data === 'object') {
        let errorMessages = ''
        for (const [field, messages] of Object.entries(error.response.data)) {
          if (Array.isArray(messages)) {
            errorMessages += `${field}: ${messages.join(', ')}\n`
          } else {
            errorMessages += `${field}: ${messages}\n`
          }
        }
        alert('更新失败:\n' + errorMessages)
      } else {
        alert('更新失败: ' + error.response.data)
      }
    } else {
      console.error('Error without response:', error.message)
      alert('更新失败: ' + error.message)
    }
  }
}

const deleteProduct = async (id) => {
  if (confirm('确定要删除这个产品吗？')) {
    try {
      await axios.delete(`http://127.0.0.1:9876/api/products/${id}/`)
      fetchProducts()
    } catch (error) {
      console.error('Error deleting product:', error)
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
    const headers = ['产品名称', '颜色选项', '规格参数']
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
      { header: '产品名称', key: 'name', width: 20 },
      { header: '颜色选项', key: 'colors', width: 30 },
      { header: '规格参数', key: 'specifications', width: 30 }
    ]
    
    // 遍历产品数据，添加每一行
    for (const product of products.value) {
      worksheet.addRow([
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
    link.download = `产品记录_${new Date().toISOString().split('T')[0]}.xlsx`
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

const handleFileUpload = (event) => {
  const file = event.target.files[0]
  if (file) {
    const reader = new FileReader()
    reader.onload = async (e) => {
      try {
        const importedProducts = JSON.parse(e.target.result)
        for (const product of importedProducts) {
          await axios.post('http://127.0.0.1:9876/api/products/', product)
        }
        fetchProducts()
        alert('产品数据导入成功！')
      } catch (error) {
        console.error('Error importing products:', error)
        alert('产品数据导入失败！')
      }
    }
    reader.readAsText(file)
  }
}

// 导入功能
const openImportDialog = () => {
  importVisible.value = true
}

const validateImportData = (data) => {
  const errors = []
  data.forEach((row, index) => {
    if (!row.name) {
      errors.push(`第 ${index + 1} 行：产品名称不能为空`)
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
      // 准备产品数据
      const productData = {
        name: row.name,
        colors: row.colors || '',
        specifications: row.specifications || ''
      }

      // 确保颜色和规格格式正确
      productData.colors = String(productData.colors).replace(/，/g, ',')
      productData.specifications = String(productData.specifications).replace(/，/g, ',')

      // 确保specifications字段不为空
      if (!productData.specifications || productData.specifications.trim() === '') {
        productData.specifications = '无'
      }

      // 保存数据
      await axios.post('http://127.0.0.1:9876/api/products/', productData)
      importSuccessCount.value++
    } catch (error) {
      importErrorCount.value++
      importErrors.value.push(`第 ${i + 1} 行：${error.message}`)
    }
    importProgress.value = Math.round((i + 1) / total * 100)
  }

  await fetchProducts()
  importVisible.value = false
}
</script>

<template>
  <div class="product-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>产品管理</span>
          <div class="header-actions">
            <el-button type="primary" @click="openDialog">添加产品</el-button>
            <el-button type="success" @click="exportProducts">导出产品</el-button>
            <el-button type="warning" @click="openImportDialog">导入产品</el-button>
          </div>
        </div>
      </template>
      
      <el-table :data="products" style="width: 100%">
        <el-table-column prop="name" label="产品名称" width="180" />
        <el-table-column prop="colors" label="颜色选项" width="200" />
        <el-table-column prop="specifications" label="规格参数" />
        <el-table-column label="操作" width="150">
          <template #default="scope">
            <el-button type="primary" size="small" @click="openEditDialog(scope.row)">编辑</el-button>
            <el-button type="danger" size="small" @click="deleteProduct(scope.row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 添加产品对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="添加产品"
      width="500px"
    >
      <el-form :model="form" label-width="80px">
        <el-form-item label="产品名称" required>
          <el-input v-model="form.name" placeholder="输入产品名称" style="width: 100%" />
        </el-form-item>
        <el-form-item label="颜色选项">
          <el-input v-model="form.colors" placeholder="输入颜色选项，用逗号分隔" style="width: 100%" />
        </el-form-item>
        <el-form-item label="规格参数">
          <el-select
            v-model="form.specifications"
            multiple
            placeholder="选择规格参数"
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
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveProduct">保存</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 编辑产品对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑产品"
      width="500px"
    >
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="产品名称" required>
          <el-input v-model="editForm.name" placeholder="输入产品名称" style="width: 100%" />
        </el-form-item>
        <el-form-item label="颜色选项">
          <el-input v-model="editForm.colors" placeholder="输入颜色选项，用逗号分隔" style="width: 100%" />
        </el-form-item>
        <el-form-item label="规格参数">
          <el-select
            v-model="editForm.specifications"
            multiple
            placeholder="选择规格参数"
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
    
    <!-- 导入组件 -->
    <ImportComponent
      v-model:visible="importVisible"
      :validate="validateImportData"
      @success="handleImportSuccess"
      :fields="['name', 'colors', 'specifications']"
      :field-labels="{ name: '产品名称', colors: '颜色选项', specifications: '规格参数' }"
    />
  </div>
</template>

<style scoped>
.product-management {
  padding: 20px 0;
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
</style>