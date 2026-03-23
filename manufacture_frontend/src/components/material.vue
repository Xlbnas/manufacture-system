<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import * as ExcelJS from 'exceljs'
import ImportComponent from './ImportComponent.vue'

const materials = ref([])
const suppliers = ref([])
const factories = ref([])
const dialogVisible = ref(false)
const supplierDialogVisible = ref(false)
const supplierManagementVisible = ref(false)
const form = ref({
  type: '辅料',
  name: '',
  quantity: '',
  supplier: '',
  factory: '',
  stock_date: ''
})
const supplierForm = ref({
  name: '',
  type: '辅料'
})

onMounted(() => {
  fetchMaterials()
  fetchSuppliers()
  fetchFactories()
})

const fetchMaterials = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:9876/api/materials/')
    materials.value = response.data
  } catch (error) {
    console.error('Error fetching materials:', error)
  }
}

const fetchSuppliers = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:9876/api/suppliers/')
    suppliers.value = response.data
  } catch (error) {
    console.error('Error fetching suppliers:', error)
  }
}

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
    type: '辅料',
    name: '',
    quantity: '',
    unit: '件',
    supplier: '',
    factory: '',
    stock_date: ''
  }
  dialogVisible.value = true
}

const openSupplierDialog = () => {
  supplierForm.value = {
    name: '',
    type: '辅料'
  }
  supplierDialogVisible.value = true
}

const saveMaterial = async () => {
  try {
    // 验证并转换数据格式
    let stockDate = form.value.stock_date
    // 转换日期格式为YYYY-MM-DD
    if (stockDate instanceof Date) {
      stockDate = stockDate.toISOString().split('T')[0]
    }
    
    const materialData = {
      type: form.value.type,
      name: form.value.name,
      quantity: Number(form.value.quantity) || 0,
      unit: form.value.unit || '件', // 使用用户输入的单位，默认为'件'
      supplier: form.value.supplier ? parseInt(form.value.supplier) : null,
      factory: form.value.factory ? parseInt(form.value.factory) : null,
      stock_date: stockDate
    }
    
    await axios.post('http://127.0.0.1:9876/api/materials/', materialData)
    dialogVisible.value = false
    fetchMaterials()
  } catch (error) {
    console.error('Error saving material:', error)
    // 显示更详细的错误信息
    if (error.response) {
      console.error('Response data:', error.response.data)
      console.error('Response status:', error.response.status)
    }
  }
}

const saveSupplier = async () => {
  try {
    console.log('Saving supplier:', supplierForm.value)
    const response = await axios.post('http://127.0.0.1:9876/api/suppliers/', supplierForm.value)
    console.log('Supplier saved successfully:', response.data)
    supplierDialogVisible.value = false
    fetchSuppliers()
  } catch (error) {
    console.error('Error saving supplier:', error)
    console.error('Error response:', error.response)
    if (error.response) {
      console.error('Response data:', error.response.data)
      console.error('Response status:', error.response.status)
    }
  }
}

const deleteSupplier = async (id) => {
  if (confirm('确定要删除这个供应商吗？')) {
    try {
      await axios.delete(`http://127.0.0.1:9876/api/suppliers/${id}/`)
      fetchSuppliers()
      ElMessage.success('供应商删除成功')
    } catch (error) {
      console.error('Error deleting supplier:', error)
      ElMessage.error('删除失败：' + (error.message || '未知错误'))
    }
  }
}

const openSupplierManagement = () => {
  fetchSuppliers()
  supplierManagementVisible.value = true
}

const openAddSupplierDialog = () => {
  supplierForm.value = {
    name: '',
    type: '辅料'
  }
  supplierDialogVisible.value = true
}

const deleteMaterial = async (id) => {
  try {
    await axios.delete(`http://127.0.0.1:9876/api/materials/${id}/`)
    fetchMaterials()
  } catch (error) {
    console.error('Error deleting material:', error)
  }
}

// 导出原料记录
const exportMaterials = async () => {
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
    workbook.creator = '原料管理系统'
    workbook.lastModifiedBy = '原料管理系统'
    workbook.created = new Date()
    workbook.modified = new Date()
    
    // 添加工作表
    const worksheet = workbook.addWorksheet('原料记录')
    
    // 设置表头
    const headers = ['入库日期', '原料类型', '供应商', '原料名称', '数量', '目标工厂', '附件']
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
      { header: '入库日期', key: 'stock_date', width: 15 },
      { header: '原料类型', key: 'type', width: 12 },
      { header: '供应商', key: 'supplier', width: 20 },
      { header: '原料名称', key: 'name', width: 20 },
      { header: '数量', key: 'quantity', width: 10 },
      { header: '目标工厂', key: 'factory', width: 20 },
      { header: '附件', key: 'attachment', width: 30 }
    ]
    
    // 遍历原料数据，添加每一行
    for (let i = 0; i < materials.value.length; i++) {
      const material = materials.value[i]
      const row = worksheet.addRow([
        material.stock_date,
        material.type,
        material.supplier?.name || '未知',
        material.name,
        material.quantity,
        material.factory?.name || '未知',
        material.attachment ? '有附件' : '无'
      ])
      
      // 下载并添加图片
      if (material.attachment) {
        try {
          const imageUrl = material.attachment.startsWith('/media/') ? `http://127.0.0.1:9876${material.attachment}` : material.attachment
          const response = await axios.get(imageUrl, { responseType: 'arraybuffer' })
          
          // 添加图片到工作簿
          const imageId = workbook.addImage({
            buffer: response.data,
            extension: 'png'
          })
          
          // 计算图片位置
          const rowNumber = i + 2 // 从第二行开始（第一行是表头）
          
          // 添加图片到工作表
          worksheet.addImage(imageId, {
            tl: { col: 6, row: rowNumber - 1 },
            br: { col: 7, row: rowNumber + 4 },
            editAs: 'oneCell'
          })
        } catch (error) {
          console.error('Error adding image:', error)
        }
      }
    }
    
    // 生成Excel文件
    const buffer = await workbook.xlsx.writeBuffer()
    const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `原料记录_${new Date().toISOString().split('T')[0]}.xlsx`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    // 关闭加载提示
    loading.close()
    
    // 显示完成反馈
    ElMessage({
      message: '导出完成！',
      type: 'success',
      duration: 3000
    })
  } catch (error) {
    console.error('Error exporting materials:', error)
    ElMessage({
      message: '导出失败：' + (error.message || '未知错误'),
      type: 'error',
      duration: 3000
    })
  }
}

// 处理附件上传
const handleAttachmentUpload = async (event, materialId) => {
  const file = event.target.files[0]
  if (!file) return
  
  const formData = new FormData()
  formData.append('attachment', file)
  
  try {
    await axios.put(`http://127.0.0.1:9876/api/materials/${materialId}/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    fetchMaterials()
    alert('附件上传成功！')
  } catch (error) {
    console.error('Error uploading attachment:', error)
    console.error('Error response:', error.response)
    if (error.response) {
      console.error('Response data:', error.response.data)
      console.error('Response status:', error.response.status)
    }
    alert('附件上传失败：' + (error.response?.data || error.message || '未知错误'))
  }
}

// 预览附件
const previewDialogVisible = ref(false)
const previewImageUrl = ref('')

const previewAttachment = (attachmentUrl) => {
  if (attachmentUrl) {
    // 确保使用正确的后端URL
    if (attachmentUrl.startsWith('/media/')) {
      previewImageUrl.value = `http://127.0.0.1:9876${attachmentUrl}`
    } else {
      previewImageUrl.value = attachmentUrl
    }
    previewDialogVisible.value = true
  }
}

// 附件管理
const attachmentsDialogVisible = ref(false)
const allAttachments = ref([])

// 导入相关状态
const importDialogVisible = ref(false)

const openAttachmentsDialog = () => {
  // 收集所有附件
  allAttachments.value = []
  materials.value.forEach(material => {
    if (material.attachment) {
      allAttachments.value.push({
        id: material.id,
        name: material.name,
        attachment: material.attachment,
        stock_date: material.stock_date
      })
    }
  })
  attachmentsDialogVisible.value = true
}

// 下载附件
const downloadAttachment = (attachmentUrl) => {
  if (attachmentUrl) {
    const url = attachmentUrl.startsWith('/media/') ? `http://127.0.0.1:9876${attachmentUrl}` : attachmentUrl
    const link = document.createElement('a')
    link.href = url
    link.download = attachmentUrl.split('/').pop()
    link.click()
  }
}

// 删除附件
const deleteAttachment = async (materialId) => {
  if (confirm('确定要删除这个附件吗？')) {
    try {
      await axios.put(`http://127.0.0.1:9876/api/materials/${materialId}/`, {
        attachment: null
      })
      fetchMaterials()
      // 重新收集附件
      openAttachmentsDialog()
      alert('附件删除成功！')
    } catch (error) {
      console.error('Error deleting attachment:', error)
      alert('附件删除失败：' + (error.message || '未知错误'))
    }
  }
}

// 打开导入对话框
const openImportDialog = () => {
  importDialogVisible.value = true
}

// 验证导入数据
const validateImportData = (item, rowIndex) => {
  if (!item.入库日期) {
    return '入库日期不能为空'
  }
  if (!item.原料类型) {
    return '原料类型不能为空'
  }
  if (!item.原料名称) {
    return '原料名称不能为空'
  }
  if (!item.数量) {
    return '数量不能为空'
  }
  if (isNaN(item.数量)) {
    return '数量必须是数字'
  }
  return null
}

// 处理导入成功
const handleImportSuccess = async (data) => {
  // 处理导入的数据
  console.log('导入的原料数据:', data)
  
  try {
    // 批量导入原料数据
    for (const item of data) {
      const materialData = {
        type: item.原料类型,
        name: item.原料名称,
        quantity: Number(item.数量) || 0,
        unit: item.单位 || '件',
        supplier: null, // 可以根据需要处理供应商映射
        factory: null, // 可以根据需要处理工厂映射
        stock_date: item.入库日期
      }
      
      await axios.post('http://127.0.0.1:9876/api/materials/', materialData)
    }
    
    // 刷新数据
    fetchMaterials()
    ElMessage.success('原料数据导入成功')
  } catch (error) {
    console.error('导入原料数据失败:', error)
    ElMessage.error('导入原料数据失败，请重试')
  }
}
</script>

<template>
  <div class="material-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>原料管理</span>
          <div class="header-actions">
            <el-button type="primary" @click="openDialog">添加原料</el-button>
            <el-button @click="openSupplierManagement">管理供应商</el-button>
            <el-button type="warning" @click="openAttachmentsDialog">管理附件</el-button>
            <el-button type="success" @click="exportMaterials">导出记录</el-button>
            <el-button type="info" @click="openImportDialog">导入记录</el-button>
          </div>
        </div>
      </template>
      <el-table :data="materials" style="width: 100%" size="small" fit>
        <el-table-column prop="stock_date" label="入库日期" min-width="120" />
        <el-table-column prop="type" label="原料类型" min-width="100" />
        <el-table-column label="供应商" min-width="150">
          <template #default="scope">
            {{ scope.row.supplier?.name || '未知' }}
          </template>
        </el-table-column>
        <el-table-column prop="name" label="原料名称" min-width="150" />
        <el-table-column prop="quantity" label="数量" min-width="100" />
        <el-table-column label="目标工厂" min-width="150">
          <template #default="scope">
            {{ scope.row.factory?.name || '未知' }}
          </template>
        </el-table-column>
        <el-table-column label="附件" min-width="160">
          <template #default="scope">
            <div v-if="scope.row.attachment" style="white-space: nowrap;">
              <el-button type="text" size="small" @click="previewAttachment(scope.row.attachment)">查看附件</el-button>
            </div>
            <div v-else style="white-space: nowrap;">
              <el-upload
                class="upload-demo"
                :auto-upload="false"
                :on-change="(file) => handleAttachmentUpload({ target: { files: [file.raw] } }, scope.row.id)"
                accept=".jpg,.jpeg,.png,.pdf"
              >
                <el-button size="small">上传附件</el-button>
              </el-upload>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="80" align="center">
          <template #default="scope">
            <el-button type="danger" size="small" @click="deleteMaterial(scope.row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      title="添加原料"
      width="500px"
    >
      <el-form :model="form" label-width="80px">
        <el-form-item label="原料类型">
          <el-select v-model="form.type" style="width: 100%">
            <el-option label="辅料" value="辅料" />
            <el-option label="面料" value="面料" />
          </el-select>
        </el-form-item>
        <el-form-item label="原料名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="数量">
          <div style="display: flex; align-items: center;">
            <el-input v-model.number="form.quantity" type="number" style="width: 70%" />
            <el-input v-model="form.unit" placeholder="单位" style="width: 30%; margin-left: 10px" />
          </div>
        </el-form-item>
        <el-form-item label="供应商">
          <el-select v-model="form.supplier" style="width: 100%" placeholder="选择供应商">
            <el-option
              v-for="supplier in suppliers"
              :key="supplier.id"
              :label="supplier.name"
              :value="supplier.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="目标工厂">
          <el-select v-model="form.factory" style="width: 100%" placeholder="选择工厂">
            <el-option
              v-for="factory in factories"
              :key="factory.id"
              :label="factory.name"
              :value="factory.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="入库日期">
          <el-date-picker
            v-model="form.stock_date"
            type="date"
            style="width: 100%"
            placeholder="选择日期"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveMaterial">保存</el-button>
        </span>
      </template>
    </el-dialog>

    <el-dialog
      v-model="supplierDialogVisible"
      title="添加供应商"
      width="500px"
    >
      <el-form :model="supplierForm" label-width="80px">
        <el-form-item label="供应商名称">
          <el-input v-model="supplierForm.name" placeholder="输入供应商名称" style="width: 100%" />
        </el-form-item>
        <el-form-item label="供应商类型">
          <el-select v-model="supplierForm.type" style="width: 100%">
            <el-option label="辅料" value="辅料" />
            <el-option label="面料" value="面料" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="supplierDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveSupplier">保存</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 附件管理对话框 -->
    <el-dialog
      v-model="attachmentsDialogVisible"
      title="附件管理"
      width="90%"
    >
      <el-table :data="allAttachments" style="width: 100%">
        <el-table-column prop="name" label="原料名称" width="200" />
        <el-table-column prop="stock_date" label="入库日期" width="150" />
        <el-table-column label="附件预览" width="200">
          <template #default="scope">
            <el-button type="text" @click="previewAttachment(scope.row.attachment)">查看附件</el-button>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button type="primary" size="small" @click="downloadAttachment(scope.row.attachment)">下载</el-button>
            <el-button type="danger" size="small" @click="deleteAttachment(scope.row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 供应商管理对话框 -->
    <el-dialog
      v-model="supplierManagementVisible"
      title="供应商管理"
      width="800px"
    >
      <div style="margin-bottom: 20px;">
        <el-button type="primary" @click="openAddSupplierDialog">添加供应商</el-button>
      </div>
      <el-table :data="suppliers" style="width: 100%">
        <el-table-column prop="name" label="供应商名称" width="200" />
        <el-table-column prop="type" label="供应商类型" width="150" />
        <el-table-column label="操作" width="150" align="center">
          <template #default="scope">
            <el-button type="danger" size="small" @click="deleteSupplier(scope.row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 附件预览对话框 -->
    <el-dialog
      v-model="previewDialogVisible"
      title="附件预览"
      width="80%"
      center
    >
      <div class="preview-container">
        <el-image
          :src="previewImageUrl"
          fit="contain"
          class="preview-image"
        />
      </div>
    </el-dialog>

    <!-- 导入组件 -->
    <ImportComponent
      v-model:visible="importDialogVisible"
      title="导入原料数据"
      :validate="validateImportData"
      @success="handleImportSuccess"
    />
  </div>
</template>

<style scoped>
.material-management {
  padding: 20px 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dialog-footer {
  width: 100%;
  display: flex;
  justify-content: flex-end;
}

.preview-container {
  min-height: 400px;
  max-height: 600px;
  overflow: auto;
  padding: 20px;
}

.preview-image {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 0 auto;
}
</style>