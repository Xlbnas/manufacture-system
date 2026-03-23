<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as ExcelJS from 'exceljs'
import ImportComponent from './ImportComponent.vue'

const outboundRecords = ref([])
const warehouses = ref([])
const factories = ref([])
const products = ref([])
const colors = ref([])
const sizes = ref([])
const dialogVisible = ref(false)
// 导入相关
const importVisible = ref(false)
const importProgress = ref(0)
const importSuccessCount = ref(0)
const importErrorCount = ref(0)
const importErrors = ref([])
const form = ref({
  factory: '',
  product: '',
  color: '',
  outbound_date: ''
})
const sizeQuantities = ref({})
const selectedSizes = ref([])

// 格式化日期为 YYYY-MM-DD（处理时区问题）
const formatDate = (date) => {
  if (!date) return ''
  const d = new Date(date)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

onMounted(() => {
  fetchOutboundRecords()
  fetchFactories()
  fetchWarehouses()
})

const fetchOutboundRecords = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:9876/api/outbound-records/')
    outboundRecords.value = response.data
  } catch (error) {
    console.error('Error fetching outbound records:', error)
  }
}

// 处理后的出库记录数据（排序后用于合并）
const processedOutboundRecords = computed(() => {
  // 按日期、仓库、颜色排序
  return [...outboundRecords.value].sort((a, b) => {
    // 先按日期排序
    if (a.outbound_date !== b.outbound_date) {
      return a.outbound_date.localeCompare(b.outbound_date)
    }
    // 再按仓库排序
    if (a.warehouse !== b.warehouse) {
      return a.warehouse.localeCompare(b.warehouse)
    }
    // 最后按颜色排序
    return (a.color || '').localeCompare(b.color || '')
  })
})

// 计算合并单元格
const spanArr = ref([])
const pos = ref(0)

// 计算日期列的合并
const getDateSpan = (data) => {
  const span = []
  let pos = 0
  for (let i = 0; i < data.length; i++) {
    if (i === 0) {
      span.push(1)
      pos = 0
    } else {
      if (data[i].outbound_date === data[i - 1].outbound_date) {
        span[pos] += 1
        span.push(0)
      } else {
        span.push(1)
        pos = i
      }
    }
  }
  return span
}

// 计算仓库列的合并
const getWarehouseSpan = (data) => {
  const span = []
  let pos = 0
  for (let i = 0; i < data.length; i++) {
    if (i === 0) {
      span.push(1)
      pos = 0
    } else {
      // 同一日期且同一仓库才合并
      if (data[i].outbound_date === data[i - 1].outbound_date &&
          data[i].warehouse === data[i - 1].warehouse) {
        span[pos] += 1
        span.push(0)
      } else {
        span.push(1)
        pos = i
      }
    }
  }
  return span
}

// 计算颜色列的合并
const getColorSpan = (data) => {
  const span = []
  let pos = 0
  for (let i = 0; i < data.length; i++) {
    if (i === 0) {
      span.push(1)
      pos = 0
    } else {
      // 同一日期、同一仓库且同一颜色才合并
      if (data[i].outbound_date === data[i - 1].outbound_date &&
          data[i].warehouse === data[i - 1].warehouse &&
          data[i].color === data[i - 1].color) {
        span[pos] += 1
        span.push(0)
      } else {
        span.push(1)
        pos = i
      }
    }
  }
  return span
}

// 单元格合并方法
const objectSpanMethod = ({ row, column, rowIndex, columnIndex }) => {
  const data = processedOutboundRecords.value
  
  if (columnIndex === 0) { // 日期列
    const span = getDateSpan(data)
    return {
      rowspan: span[rowIndex],
      colspan: 1
    }
  }
  
  if (columnIndex === 1) { // 仓库列
    const span = getWarehouseSpan(data)
    return {
      rowspan: span[rowIndex],
      colspan: 1
    }
  }
  
  if (columnIndex === 2) { // 颜色列
    const span = getColorSpan(data)
    return {
      rowspan: span[rowIndex],
      colspan: 1
    }
  }
  
  return {
    rowspan: 1,
    colspan: 1
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

const fetchWarehouses = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:9876/api/warehouse/')
    warehouses.value = response.data
  } catch (error) {
    console.error('Error fetching warehouses:', error)
  }
}

const openDialog = () => {
  form.value = {
    factory: '',
    product: '',
    color: '',
    outbound_date: ''
  }
  sizeQuantities.value = {}
  selectedSizes.value = []
  colors.value = []
  sizes.value = []
  dialogVisible.value = true
}

// 工厂变化时更新产品列表
const factoryProducts = computed(() => {
  if (!form.value.factory) return []
  const factoryId = parseInt(form.value.factory)
  const factoryWarehouses = warehouses.value.filter(item => item.factory.id === factoryId)
  const productIds = [...new Set(factoryWarehouses.map(item => item.product.id))]
  return products.value.filter(product => productIds.includes(product.id))
})

// 产品变化时更新颜色列表
const productColors = computed(() => {
  if (!form.value.factory || !form.value.product) return []
  const factoryId = parseInt(form.value.factory)
  const productId = parseInt(form.value.product)
  const productWarehouses = warehouses.value.filter(item => 
    item.factory.id === factoryId && item.product.id === productId
  )
  const colorSet = [...new Set(productWarehouses.map(item => item.color))]
  return colorSet.map(color => ({ value: color, label: color }))
})

// 颜色变化时更新尺码列表
const productSizes = computed(() => {
  if (!form.value.factory || !form.value.product || !form.value.color) return []
  const factoryId = parseInt(form.value.factory)
  const productId = parseInt(form.value.product)
  const color = form.value.color
  return warehouses.value.filter(item => 
    item.factory.id === factoryId && 
    item.product.id === productId && 
    item.color === color
  )
})

// 监听工厂变化，加载产品数据
watch(() => form.value.factory, async (newFactoryId) => {
  if (newFactoryId) {
    try {
      const response = await axios.get('http://127.0.0.1:9876/api/products/')
      products.value = response.data
    } catch (error) {
      console.error('Error fetching products:', error)
    }
  }
})

// 验证出库数据
const validateOutbound = () => {
  if (!form.value.factory || !form.value.product || !form.value.color) {
    return false
  }
  if (!form.value.outbound_date) {
    return false
  }
  if (selectedSizes.value.length === 0) {
    return false
  }
  // 验证每个选中尺码的出库数量不超过库存
  for (const size of selectedSizes.value) {
    const warehouseItem = productSizes.value.find(item => item.size === size)
    if (warehouseItem && sizeQuantities.value[size] > warehouseItem.quantity) {
      return false
    }
  }
  return true
}

// 获取验证错误信息
const getValidationError = () => {
  if (!form.value.factory) {
    return '请选择出库工厂'
  }
  if (!form.value.product) {
    return '请选择出库产品'
  }
  if (!form.value.color) {
    return '请选择出库颜色'
  }
  if (!form.value.outbound_date) {
    return '请选择出库日期'
  }
  if (selectedSizes.value.length === 0) {
    return '请至少选择一个尺码'
  }
  // 验证每个选中尺码的出库数量
  for (const size of selectedSizes.value) {
    const warehouseItem = productSizes.value.find(item => item.size === size)
    if (!warehouseItem) {
      return `尺码 ${size} 的库存信息不存在`
    }
    if (!sizeQuantities.value[size] || sizeQuantities.value[size] <= 0) {
      return `请输入尺码 ${size} 的出库数量`
    }
    if (sizeQuantities.value[size] > warehouseItem.quantity) {
      return `尺码 ${size} 的出库数量超过库存（库存：${warehouseItem.quantity}）`
    }
  }
  return null
}

const saveOutboundRecord = async () => {
  try {
    // 验证出库数据
    const validationError = getValidationError()
    if (validationError) {
      alert(validationError)
      return
    }
    
    // 获取工厂名称
    const factoryId = parseInt(form.value.factory)
    const factory = factories.value.find(f => f.id === factoryId)
    if (!factory) {
      alert('未找到指定工厂')
      return
    }
    
    // 为每个选中的尺码创建出库记录
    for (const size of selectedSizes.value) {
      const warehouseItem = productSizes.value.find(item => item.size === size)
      if (warehouseItem && sizeQuantities.value[size] > 0) {
        // 准备出库记录数据
        const outboundData = {
          product_id: parseInt(form.value.product),
          color: form.value.color,
          size: size,
          quantity: parseInt(sizeQuantities.value[size]),
          outbound_date: form.value.outbound_date ? formatDate(form.value.outbound_date) : '',
          warehouse: factory.name
        }
        
        console.log('Outbound data:', outboundData)
        
        // 创建出库记录
        await axios.post('http://127.0.0.1:9876/api/outbound-records/', outboundData)
        
        // 更新仓库库存
        try {
          await axios.put(`http://127.0.0.1:9876/api/warehouse/${warehouseItem.id}/`, {
            product: parseInt(warehouseItem.product.id || warehouseItem.product),
            factory: parseInt(warehouseItem.factory.id || warehouseItem.factory),
            color: warehouseItem.color,
            size: warehouseItem.size,
            quantity: warehouseItem.quantity - parseInt(sizeQuantities.value[size])
          })
        } catch (error) {
          console.error('Error updating warehouse:', error)
          console.error('Warehouse update data:', {
            product: warehouseItem.product,
            factory: warehouseItem.factory,
            color: warehouseItem.color,
            size: warehouseItem.size,
            quantity: warehouseItem.quantity - parseInt(sizeQuantities.value[size])
          })
        }
      }
    }
    
    dialogVisible.value = false
    fetchOutboundRecords()
    fetchWarehouses()
  } catch (error) {
    console.error('Error saving outbound record:', error)
    console.error('Error response:', error.response?.data)
    // 提取错误信息
    let errorMsg = '数据格式错误'
    if (error.response?.data) {
      if (typeof error.response.data === 'string') {
        errorMsg = error.response.data
      } else if (error.response.data.message) {
        errorMsg = error.response.data.message
      } else if (error.response.data.detail) {
        errorMsg = error.response.data.detail
      } else {
        // 将对象转换为字符串
        errorMsg = Object.entries(error.response.data)
          .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(', ') : value}`)
          .join('; ')
      }
    } else if (error.message) {
      errorMsg = error.message
    }
    alert('保存失败：' + errorMsg)
  }
}

const deleteOutboundRecord = async (id) => {
  try {
    await axios.delete(`http://127.0.0.1:9876/api/outbound-records/${id}/`)
    fetchOutboundRecords()
  } catch (error) {
    console.error('Error deleting outbound record:', error)
  }
}

// 撤回出库记录
const revokeOutboundRecord = async (record) => {
  try {
    await ElMessageBox.confirm(
      `确定要撤回这条出库记录吗？<br><br>
      <strong>产品：</strong>${record.product?.name || record.product}<br>
      <strong>颜色：</strong>${record.color || '-'}<br>
      <strong>尺码：</strong>${record.size || '-'}<br>
      <strong>数量：</strong>${record.quantity}<br><br>
      撤回后库存将自动返还。`,
      '确认撤回',
      {
        confirmButtonText: '确认撤回',
        cancelButtonText: '取消',
        type: 'warning',
        dangerouslyUseHTMLString: true
      }
    )
    
    // 用户点击确认后才执行撤回
    await axios.post(`http://127.0.0.1:9876/api/outbound-records/${record.id}/revoke/`)
    ElMessage.success('撤回成功，库存已返还')
    fetchOutboundRecords()
    fetchWarehouses() // 刷新仓库数据
  } catch (error) {
    // 用户点击取消时不显示错误
    if (error === 'cancel' || error?.message === 'cancel') {
      return
    }
    console.error('Error revoking outbound record:', error)
    ElMessage.error('撤回失败：' + (error.response?.data?.error || error.message))
  }
}

// 处理尺码选择
const handleSizeSelection = (val, size) => {
  if (val) {
    if (!selectedSizes.value.includes(size)) {
      selectedSizes.value.push(size)
    }
  } else {
    selectedSizes.value = selectedSizes.value.filter(s => s !== size)
  }
}

// 导出表格为Excel
const exportToExcel = async () => {
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
    workbook.creator = '出库管理系统'
    workbook.lastModifiedBy = '出库管理系统'
    workbook.created = new Date()
    workbook.modified = new Date()
    
    // 添加工作表
    const worksheet = workbook.addWorksheet('出库记录')
    
    // 设置表头
    const headers = ['日期', '仓库', '产品', '颜色', '尺码', '数量']
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
      { header: '日期', key: 'outbound_date', width: 15 },
      { header: '仓库', key: 'warehouse', width: 20 },
      { header: '产品', key: 'product', width: 20 },
      { header: '颜色', key: 'color', width: 12 },
      { header: '尺码', key: 'size', width: 12 },
      { header: '数量', key: 'quantity', width: 10 }
    ]
    
    // 按日期排序
    const sortedRecords = [...outboundRecords.value].sort((a, b) => {
      return new Date(a.outbound_date) - new Date(b.outbound_date)
    })
    
    // 遍历出库记录数据，添加每一行
    let currentDate = null
    let startRow = 2 // 从第二行开始（第一行是表头）
    
    for (let i = 0; i < sortedRecords.length; i++) {
      const record = sortedRecords[i]
      const productName = record.product?.name || record.product
      const row = worksheet.addRow([
        record.outbound_date,
        record.warehouse,
        productName,
        record.color || '',
        record.size || '',
        record.quantity
      ])
      
      // 检查日期是否变化
      if (record.outbound_date !== currentDate) {
        // 如果不是第一条记录，并且前一个日期有多个记录，合并单元格
        if (currentDate !== null && startRow < i + 2) {
          worksheet.mergeCells(`A${startRow}:A${i + 1}`)
        }
        // 更新当前日期和起始行
        currentDate = record.outbound_date
        startRow = i + 2
      }
      
      // 处理最后一组相同日期的记录
      if (i === sortedRecords.length - 1 && startRow < i + 2) {
        worksheet.mergeCells(`A${startRow}:A${i + 2}`)
      }
    }
    
    // 生成Excel文件
    const buffer = await workbook.xlsx.writeBuffer()
    const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.setAttribute('href', url)
    link.setAttribute('download', `出库记录_${new Date().toISOString().split('T')[0]}.xlsx`)
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
    console.error('Error exporting outbound records:', error)
    ElMessage({
      message: '导出失败：' + (error.message || '未知错误'),
      type: 'error',
      duration: 3000
    })
  }
}

// 清除表格内容
const clearTable = async () => {
  if (confirm('确定要清除所有出库记录吗？\n\n提示：清除后数据将不可恢复。')) {
    try {
      // 导出备份
      exportToExcel()
      
      // 批量删除所有记录
      for (const record of outboundRecords.value) {
        await axios.delete(`http://127.0.0.1:9876/api/outbound-records/${record.id}/`)
      }
      
      // 刷新数据
      fetchOutboundRecords()
      alert('出库记录已清除并导出备份')
    } catch (error) {
      console.error('Error clearing outbound records:', error)
      alert('清除失败：' + (error.message || '未知错误'))
    }
  }
}

// 导入功能
const openImportDialog = () => {
  importVisible.value = true
}

const validateImportData = (data) => {
  const errors = []
  data.forEach((row, index) => {
    if (!row.date) {
      errors.push(`第 ${index + 1} 行：日期不能为空`)
    }
    if (!row.warehouse) {
      errors.push(`第 ${index + 1} 行：仓库不能为空`)
    }
    if (!row.product) {
      errors.push(`第 ${index + 1} 行：产品不能为空`)
    }
    if (!row.color) {
      errors.push(`第 ${index + 1} 行：颜色不能为空`)
    }
    if (!row.size) {
      errors.push(`第 ${index + 1} 行：尺码不能为空`)
    }
    if (!row.quantity || isNaN(row.quantity) || Number(row.quantity) <= 0) {
      errors.push(`第 ${index + 1} 行：数量必须是大于0的数字`)
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
      // 查找工厂
      const factory = factories.value.find(f => f.name === row.warehouse)
      if (!factory) {
        throw new Error(`工厂 ${row.warehouse} 不存在`)
      }

      // 查找产品
      const product = products.value.find(p => p.name === row.product)
      if (!product) {
        throw new Error(`产品 ${row.product} 不存在`)
      }

      // 查找仓库记录
      const warehouseItem = warehouses.value.find(item => 
        item.factory.id === factory.id && 
        item.product.id === product.id && 
        item.color === row.color && 
        item.size === row.size
      )

      if (!warehouseItem) {
        throw new Error(`库存记录不存在：${row.product} - ${row.color} - ${row.size}`)
      }

      if (Number(row.quantity) > warehouseItem.quantity) {
        throw new Error(`出库数量超过库存：${row.quantity} > ${warehouseItem.quantity}`)
      }

      // 创建出库记录
      const outboundData = {
        product_id: product.id,
        color: row.color,
        size: row.size,
        quantity: Number(row.quantity),
        outbound_date: row.date,
        warehouse: row.warehouse
      }

      await axios.post('http://127.0.0.1:9876/api/outbound-records/', outboundData)

      // 更新仓库库存
      await axios.put(`http://127.0.0.1:9876/api/warehouse/${warehouseItem.id}/`, {
        product: product.id,
        factory: factory.id,
        color: row.color,
        size: row.size,
        quantity: warehouseItem.quantity - Number(row.quantity)
      })

      importSuccessCount.value++
    } catch (error) {
      importErrorCount.value++
      importErrors.value.push(`第 ${i + 1} 行：${error.message}`)
    }
    importProgress.value = Math.round((i + 1) / total * 100)
  }

  await fetchOutboundRecords()
  await fetchWarehouses()
  importVisible.value = false
}
</script>

<template>
  <div class="outbound-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>出库管理</span>
          <div class="header-buttons">
            <el-button type="primary" @click="openDialog">添加出库记录</el-button>
            <el-button type="success" @click="exportToExcel">导出记录</el-button>
            <el-button type="warning" @click="openImportDialog">导入记录</el-button>
            <el-button type="danger" @click="clearTable">清除记录</el-button>
          </div>
        </div>
      </template>
      <el-table 
        :data="processedOutboundRecords" 
        style="width: 100%"
        :span-method="objectSpanMethod"
        border
      >
        <el-table-column prop="outbound_date" label="日期" width="100" align="center" />
        <el-table-column prop="warehouse" label="仓库" width="120" align="center" />
        <el-table-column prop="color" label="颜色" width="80" align="center" />
        <el-table-column label="产品" width="120" align="center">
          <template #default="scope">
            {{ scope.row.product?.name || scope.row.product }}
          </template>
        </el-table-column>
        <el-table-column prop="size" label="尺码" width="80" align="center" />
        <el-table-column prop="quantity" label="出库数量" width="90" align="center" />
        <el-table-column label="操作" width="140" align="center">
          <template #default="scope">
            <el-button type="warning" size="small" @click="revokeOutboundRecord(scope.row)">撤回</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      title="添加出库记录"
      width="600px"
    >
      <el-form :model="form" label-width="80px">
        <el-form-item label="出库工厂">
          <el-select v-model="form.factory" style="width: 100%" placeholder="选择工厂">
            <el-option
              v-for="factory in factories"
              :key="factory.id"
              :label="factory.name"
              :value="factory.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="出库品种">
          <el-select v-model="form.product" style="width: 100%" placeholder="选择产品">
            <el-option
              v-for="product in factoryProducts"
              :key="product.id"
              :label="product.name"
              :value="product.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="出库颜色">
          <el-select v-model="form.color" style="width: 100%" placeholder="选择颜色">
            <el-option
              v-for="color in productColors"
              :key="color.value"
              :label="color.label"
              :value="color.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="尺码选择">
          <div v-if="productSizes.length > 0" class="size-table">
            <el-table :data="productSizes" style="width: 100%">
              <el-table-column label="选择">
                <template #default="scope">
                  <el-checkbox 
                    :checked="selectedSizes.includes(scope.row.size)" 
                    @change="(val) => handleSizeSelection(val, scope.row.size)" 
                  />
                </template>
              </el-table-column>
              <el-table-column prop="size" label="尺码" />
              <el-table-column prop="quantity" label="库存数量" />
              <el-table-column label="出库数量">
                <template #default="scope">
                  <el-input 
                    v-model.number="sizeQuantities[scope.row.size]" 
                    type="number" 
                    placeholder="输入数量" 
                    :disabled="!selectedSizes.includes(scope.row.size)"
                  />
                </template>
              </el-table-column>
            </el-table>
          </div>
          <div v-else class="no-sizes">
            请选择工厂、产品和颜色
          </div>
        </el-form-item>
        <el-form-item label="出库日期">
          <el-date-picker
            v-model="form.outbound_date"
            type="date"
            style="width: 100%"
            placeholder="选择日期"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveOutboundRecord" :disabled="!validateOutbound()">保存</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 导入组件 -->
    <ImportComponent
      v-model:visible="importVisible"
      :validate="validateImportData"
      @success="handleImportSuccess"
      :fields="['date', 'warehouse', 'product', 'color', 'size', 'quantity']"
      :field-labels="{ date: '日期', warehouse: '仓库', product: '产品', color: '颜色', size: '尺码', quantity: '数量' }"
    />
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.header-buttons {
  display: flex;
  gap: 10px;
}

.size-table {
  margin-top: 10px;
  width: 100%;
}

.size-table .el-table {
  width: 100% !important;
}

.no-sizes {
  padding: 20px;
  text-align: center;
  color: #909399;
  background-color: #f5f7fa;
  border-radius: 4px;
  margin-top: 10px;
}

/* 修复数字输入问题 */
.el-input__inner[type="number"] {
  -moz-appearance: textfield;
}

.el-input__inner[type="number"]::-webkit-outer-spin-button,
.el-input__inner[type="number"]::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

/* 确保表格列宽合理分配 */
.size-table .el-table__header-wrapper th,
.size-table .el-table__body-wrapper td {
  padding: 12px;
}

.size-table .el-table__header-wrapper th:first-child,
.size-table .el-table__body-wrapper td:first-child {
  width: 80px;
}

.size-table .el-table__header-wrapper th:nth-child(2),
.size-table .el-table__body-wrapper td:nth-child(2) {
  width: 100px;
}

.size-table .el-table__header-wrapper th:nth-child(3),
.size-table .el-table__body-wrapper td:nth-child(3) {
  width: 120px;
}

.size-table .el-table__header-wrapper th:nth-child(4),
.size-table .el-table__body-wrapper td:nth-child(4) {
  width: 150px;
}

</style>