<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import * as ExcelJS from 'exceljs'
import ImportComponent from './ImportComponent.vue'

const materials = ref([])
const suppliers = ref([])
const factories = ref([])
const dialogVisible = ref(false)
const form = ref({
  type: '辅料',
  name: '',
  quantity: '',
  unit: '件',
  supplier: '',
  recipientType: '',
  recipient: '',
  stock_date: '',
  remark: ''
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
    recipientType: '',
    recipient: '',
    stock_date: '',
    remark: ''
  }
  dialogVisible.value = true
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
      factory: form.value.recipient ? parseInt(form.value.recipient) : null,
      stock_date: stockDate,
      remark: form.value.remark
    }
    
    // 如果是添加染色布（面料），并且有供应商和收货方，需要减少布厂的布料数量
    if (form.value.type === '面料' && form.value.supplier && form.value.recipient) {
      // 获取所有材料数据
      const materialsResponse = await axios.get('http://127.0.0.1:9876/api/materials/')
      const allMaterials = materialsResponse.data
      
      // 查找布厂的布料
      const clothMaterial = allMaterials.find(m => 
        m.type === '布料' && 
        m.supplier === parseInt(form.value.supplier) &&
        m.factory === parseInt(form.value.recipient)
      )
      
      if (clothMaterial) {
        // 计算剩余数量
        const remainingQuantity = parseFloat(clothMaterial.quantity) - parseFloat(form.value.quantity)
        if (remainingQuantity < 0) {
          alert('布厂的布料数量不足！')
          return
        }
        
        // 更新布厂的布料数量
        await axios.put(`http://127.0.0.1:9876/api/materials/${clothMaterial.id}/`, {
          ...clothMaterial,
          quantity: remainingQuantity
        })
      }
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
    const headers = ['入库日期', '原料类型', '供应商', '原料名称', '数量', '目标工厂', '附件', '备注']
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
      { header: '附件', key: 'attachment', width: 30 },
      { header: '备注', key: 'remark', width: 40 }
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
        material.attachment ? '有附件' : '无',
        material.remark || ''
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

// 编辑备注相关状态
const editRemarkDialogVisible = ref(false)
const currentMaterial = ref(null)
const editRemarkForm = ref({ remark: '' })

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

// 处理原料类型变化
const handleTypeChange = () => {
  // 重置供应商和收货方选择
  form.value.supplier = ''
  form.value.recipient = ''
  form.value.recipientType = ''
  
  // 如果选择的是布料类型，设置默认单位为米
  if (form.value.type === '布料') {
    form.value.unit = '米'
  } else if (form.value.type === '面料') {
    form.value.unit = '米'
  } else {
    form.value.unit = '件'
  }
}

// 过滤供应商/工厂列表
const filteredSuppliers = computed(() => {
  if (!form.value.type) return suppliers.value
  
  // 当原料类型为工厂退货时，返回工厂列表
  if (form.value.type === '工厂退货') {
    return factories.value
  }
  
  // 其他类型返回对应类型的供应商
  return suppliers.value.filter(supplier => supplier.type === form.value.type)
})

// 处理收货方类型变化
const handleRecipientTypeChange = () => {
  // 重置收货方选择
  form.value.recipient = ''
}

// 收货方选项
const recipientOptions = computed(() => {
  if (!form.value.recipientType) return []
  
  switch (form.value.recipientType) {
    case '工厂':
      return factories.value
    case '辅料':
    case '面料':
    case '布料':
      // 对于面料（染色布），收货方应该是染厂
      if (form.value.recipientType === '面料') {
        return suppliers.value.filter(supplier => supplier.type === '面料')
      }
      return suppliers.value.filter(supplier => supplier.type === form.value.recipientType)
    default:
      return []
  }
})

// 供应商标签文本
const supplierLabel = computed(() => {
  return form.value.type === '工厂退货' ? '退货工厂' : '供应商'
})

// 搜索和筛选
const searchQuery = ref('')
const filterType = ref('')

// 重置筛选
const resetFilter = () => {
  searchQuery.value = ''
  filterType.value = ''
}

// 点击汇总卡片切换材料类型
const handleSummaryClick = (type) => {
  filterType.value = type
}

// 过滤后的材料列表
const filteredMaterials = computed(() => {
  return materials.value.filter(material => {
    // 搜索过滤
    const matchesSearch = !searchQuery.value || 
      material.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      (material.supplier?.name && material.supplier.name.toLowerCase().includes(searchQuery.value.toLowerCase()))
    
    // 类型过滤
    const matchesType = !filterType.value || material.type === filterType.value
    
    return matchesSearch && matchesType
  })
})

// 材料数量汇总
const totalQuantity = computed(() => {
  const total = materials.value.reduce((total, material) => total + (parseFloat(material.quantity || 0) || 0), 0)
  return total.toFixed(2)
})

// 辅料数量
const 辅料数量 = computed(() => {
  const total = materials.value.filter(m => m.type === '辅料').reduce((total, material) => total + (parseFloat(material.quantity || 0) || 0), 0)
  return total.toFixed(2)
})

// 布料数量
const 布料数量 = computed(() => {
  const total = materials.value.filter(m => m.type === '布料').reduce((total, material) => total + (parseFloat(material.quantity || 0) || 0), 0)
  return total.toFixed(2)
})

// 染色布数量
const 染色布数量 = computed(() => {
  const total = materials.value.filter(m => m.type === '面料').reduce((total, material) => total + (parseFloat(material.quantity || 0) || 0), 0)
  return total.toFixed(2)
})

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
        stock_date: item.入库日期,
        remark: item.备注 || ''
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

// 打开编辑备注对话框
const openEditRemarkDialog = (material) => {
  currentMaterial.value = material
  editRemarkForm.value = { remark: material.remark || '' }
  editRemarkDialogVisible.value = true
}

// 保存备注
const saveRemark = async () => {
  if (!currentMaterial.value) return
  
  try {
    await axios.put(`http://127.0.0.1:9876/api/materials/${currentMaterial.value.id}/`, {
      remark: editRemarkForm.value.remark
    })
    
    // 刷新数据
    fetchMaterials()
    editRemarkDialogVisible.value = false
    ElMessage.success('备注更新成功')
  } catch (error) {
    console.error('更新备注失败:', error)
    ElMessage.error('更新备注失败，请重试')
  }
}

// 颜色管理相关状态
const colors = ref(['黑色', '卡其', '军绿', '丛林', '三沙', '藏蓝', '数码丛林', '数码海洋', '数码沙漠', '黑蟒纹', '绿蟒纹', '绿废墟', '灰废墟', '小绿人', '黑cp', 'cp', '绿cp'])
const colorDialogVisible = ref(false)
const colorListDialogVisible = ref(false)
const editingColor = ref('')
const colorAction = ref('add') // 'add' or 'edit'

// 打开颜色管理对话框
const openColorDialog = (action, color = '') => {
  if (action === 'add' && !color) {
    // 点击颜色管理按钮时打开颜色列表
    colorListDialogVisible.value = true
  } else {
    colorAction.value = action
    editingColor.value = color
    colorDialogVisible.value = true
  }
}

// 保存颜色
const saveColor = () => {
  if (!editingColor.value.trim()) {
    ElMessage.error('颜色名称不能为空')
    return
  }
  
  if (colorAction.value === 'add') {
    if (!colors.value.includes(editingColor.value)) {
      colors.value.push(editingColor.value)
      ElMessage.success('颜色添加成功')
    } else {
      ElMessage.warning('颜色已存在')
    }
  } else if (colorAction.value === 'edit') {
    const index = colors.value.findIndex(c => c === editingColor.value)
    if (index !== -1) {
      colors.value[index] = editingColor.value
      ElMessage.success('颜色更新成功')
    }
  }
  
  colorDialogVisible.value = false
  editingColor.value = ''
}

// 删除颜色
const deleteColor = (color) => {
  ElMessageBox.confirm(`确定要删除颜色 "${color}" 吗？`, '确认删除', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    const index = colors.value.findIndex(c => c === color)
    if (index !== -1) {
      colors.value.splice(index, 1)
      ElMessage.success('颜色删除成功')
    }
  }).catch(() => {})
}
</script>

<template>
  <div class="material-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>材料溯源</span>
          <div class="header-actions">
            <el-button type="primary" @click="openDialog">添加原料</el-button>
            <el-button type="warning" @click="openAttachmentsDialog">管理附件</el-button>
            <el-button type="info" @click="openColorDialog('add')">颜色管理</el-button>
            <el-button type="success" @click="exportMaterials">导出记录</el-button>
            <el-button type="info" @click="openImportDialog">导入记录</el-button>
          </div>
        </div>
      </template>
      
      <!-- 材料汇总卡片 -->
      <div class="material-summary">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-card shadow="hover" class="summary-card" @click="handleSummaryClick('')">
              <div class="summary-item">
                <div class="summary-label">总材料数量</div>
                <div class="summary-value">{{ totalQuantity }}</div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="summary-card" @click="handleSummaryClick('辅料')">
              <div class="summary-item">
                <div class="summary-label">辅料数量</div>
                <div class="summary-value">{{辅料数量}}</div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="summary-card" @click="handleSummaryClick('布料')">
              <div class="summary-item">
                <div class="summary-label">布料数量</div>
                <div class="summary-value">{{布料数量}}</div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="summary-card" @click="handleSummaryClick('面料')">
              <div class="summary-item">
                <div class="summary-label">染色布数量</div>
                <div class="summary-value">{{染色布数量}}</div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
      
      <!-- 搜索和筛选 -->
      <div class="material-filter">
        <el-row :gutter="20" style="margin-bottom: 20px;">
          <el-col :span="12">
            <el-input
              v-model="searchQuery"
              placeholder="搜索材料名称或供应商"
              prefix-icon="el-icon-search"
            />
          </el-col>
          <el-col :span="8">
            <el-select v-model="filterType" placeholder="筛选原料类型" style="width: 100%">
              <el-option label="全部" value="" />
              <el-option label="辅料" value="辅料" />
              <el-option label="布料" value="布料" />
              <el-option label="染色布" value="面料" />
              <el-option label="工厂退货" value="工厂退货" />
            </el-select>
          </el-col>
          <el-col :span="4">
            <el-button type="primary" @click="resetFilter">重置筛选</el-button>
          </el-col>
        </el-row>
      </div>
      
      <el-table :data="filteredMaterials" style="width: 100%" size="small" fit>
        <el-table-column prop="stock_date" label="入库日期" min-width="120" />
        <el-table-column prop="type" label="原料类型" min-width="100" />
        <el-table-column label="供应商/退货工厂" min-width="150">
          <template #default="scope">
            {{ scope.row.supplier?.name || '未知' }}
          </template>
        </el-table-column>
        <el-table-column prop="name" label="原料名称" min-width="150" />
        <el-table-column prop="quantity" label="数量" min-width="100" />
        <el-table-column label="收货方" min-width="150">
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
        <el-table-column label="备注" min-width="250">
          <template #default="scope">
            <div class="remark-cell">
              <el-tooltip :content="scope.row.remark || '无备注'" placement="top" effect="dark">
                <div class="remark-content" :class="{ 'has-remark': scope.row.remark }">
                  {{ scope.row.remark ? (scope.row.remark.length > 30 ? scope.row.remark.substring(0, 30) + '...' : scope.row.remark) : '无备注' }}
                </div>
              </el-tooltip>
              <el-button type="text" size="small" @click="openEditRemarkDialog(scope.row)" style="margin-left: 8px;">编辑</el-button>
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
      <el-form :model="form" label-width="100px">
        <el-form-item label="原料类型">
          <el-select v-model="form.type" style="width: 100%" @change="handleTypeChange">
            <el-option label="辅料" value="辅料" />
            <el-option label="布料" value="布料" />
            <el-option label="染色布" value="面料" />
            <el-option label="工厂退货" value="工厂退货" />
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
        <el-form-item :label="supplierLabel">
          <el-select v-model="form.supplier" style="width: 100%" :placeholder="`选择${supplierLabel}`">
            <el-option
              v-for="supplier in filteredSuppliers"
              :key="supplier.id"
              :label="supplier.name"
              :value="supplier.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="收货方类型">
          <el-select v-model="form.recipientType" style="width: 100%" placeholder="选择收货方类型" @change="handleRecipientTypeChange">
            <el-option label="染厂" value="面料" />
            <el-option label="辅料" value="辅料" />
            <el-option label="工厂" value="工厂" />
            <el-option label="布料" value="布料" />
          </el-select>
        </el-form-item>
        <el-form-item label="收货方">
          <el-select v-model="form.recipient" style="width: 100%" placeholder="选择收货方">
            <el-option
              v-for="item in recipientOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
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
        <el-form-item label="备注">
          <el-input
            v-model="form.remark"
            type="textarea"
            :rows="3"
            placeholder="请输入备注信息"
            style="width: 100%"
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

    <!-- 编辑备注对话框 -->
    <el-dialog
      v-model="editRemarkDialogVisible"
      title="编辑备注"
      width="500px"
    >
      <el-form :model="editRemarkForm" label-width="80px">
        <el-form-item label="备注">
          <el-input
            v-model="editRemarkForm.remark"
            type="textarea"
            :rows="5"
            placeholder="请输入备注信息"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editRemarkDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveRemark">保存</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 颜色管理对话框 -->
    <el-dialog
      v-model="colorDialogVisible"
      :title="colorAction === 'add' ? '添加颜色' : '编辑颜色'"
      width="500px"
    >
      <el-form :model="{ color: editingColor }" label-width="80px">
        <el-form-item label="颜色名称">
          <el-input v-model="editingColor" placeholder="请输入颜色名称" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="colorDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveColor">保存</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 颜色列表对话框 -->
    <el-dialog
      v-model="colorListDialogVisible"
      title="颜色管理"
      width="600px"
    >
      <el-table :data="colors" style="width: 100%">
        <el-table-column prop="" label="颜色名称" width="300">
          <template #default="scope">
            {{ scope.row }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button type="primary" size="small" @click="openColorDialog('edit', scope.row)">编辑</el-button>
            <el-button type="danger" size="small" @click="deleteColor(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 20px; text-align: right">
        <el-button type="primary" @click="openColorDialog('add')">添加颜色</el-button>
      </div>
    </el-dialog>
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

.remark-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.remark-content {
  flex: 1;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.4;
  min-height: 2.8em;
  display: flex;
  align-items: center;
}

.remark-content.has-remark {
  color: #606266;
}

/* 材料汇总卡片样式 */
.material-summary {
  margin-bottom: 20px;
}

.summary-card {
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
}

.summary-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.summary-card:active {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.summary-item {
  text-align: center;
  padding: 10px;
  box-sizing: border-box;
}

.summary-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.summary-value {
  font-size: 24px;
  font-weight: bold;
  color: #409EFF;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 筛选区域样式 */
.material-filter {
  margin-bottom: 20px;
}
</style>