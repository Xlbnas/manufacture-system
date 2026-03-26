<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'
import ImportComponent from './ImportComponent.vue'
import * as ExcelJS from 'exceljs'

// 响应式数据
const factories = ref([])
const selectedFactory = ref('')
const products = ref([])
const warehouseData = ref([])
const batchMode = ref(false)
const dialogVisible = ref(false)
const editDialogVisible = ref(false)
// 导入相关
const importVisible = ref(false)
const importProgress = ref(0)
const importSuccessCount = ref(0)
const importErrorCount = ref(0)
const importErrors = ref([])
const form = ref({
  product: '',
  color: '',
  size: '',
  quantity: '',
  factory: ''
})
const editForm = ref({
  id: '',
  product: '',
  color: '',
  size: '',
  quantity: '',
  factory: ''
})
const batchForm = ref({
  factory: '',
  items: [
    { product: '', color: '', sizes: [], quantity: '' }
  ]
})
// 计划添加相关
const planDialogVisible = ref(false)
const selectedPlan = ref(null)
const productColors = ref([])
const productSizes = ref([])
const batchItemColors = ref({})
const batchItemSizes = ref({})

// 生产计划数据
const productionPlans = ref([])

// 图表实例
const pieChartRef = ref(null)
const pieChart = ref(null)

// 饼图层级状态 - 与首页一致
const currentInventoryLevel = ref('factory') // factory, product, color, size
const currentFactory = ref('')
const currentProduct = ref('')
const currentColor = ref('')
const showBackButton = ref(false)

// 颜色选项
const colorOptions = [
  { value: 'red', label: '红色' },
  { value: 'blue', label: '蓝色' },
  { value: 'green', label: '绿色' },
  { value: 'black', label: '黑色' },
  { value: 'white', label: '白色' }
]

// 尺码选项
const sizeOptions = [
  { value: 'S', label: 'S' },
  { value: 'M', label: 'M' },
  { value: 'L', label: 'L' },
  { value: 'XL', label: 'XL' },
  { value: 'XXL', label: 'XXL' },
  { value: '3XL', label: '3XL' },
  { value: '4XL', label: '4XL' },
  { value: '5XL', label: '5XL' }
]

// 计算属性：当前工厂的库存数据
const currentWarehouseData = computed(() => {
  if (!selectedFactory.value) return warehouseData.value
  return warehouseData.value.filter(item => item.factory === selectedFactory.value)
})

// 计算属性：按工厂分组的库存数据
const factoryGroupedData = computed(() => {
  const grouped = {}
  warehouseData.value.forEach(item => {
    const factoryName = item.factory?.name || item.factory
    if (!grouped[factoryName]) {
      grouped[factoryName] = 0
    }
    grouped[factoryName] += item.quantity
  })
  return Object.entries(grouped).map(([name, value]) => ({
    name,
    value
  }))
})

// 计算属性：按产品分组的库存数据（在选定工厂内）
const productGroupedData = computed(() => {
  const grouped = {}
  const filteredData = currentFactory.value
    ? warehouseData.value.filter(item => (item.factory?.name || item.factory) === currentFactory.value)
    : warehouseData.value
  
  filteredData.forEach(item => {
    const productName = item.product?.name || item.product
    if (!grouped[productName]) {
      grouped[productName] = 0
    }
    grouped[productName] += item.quantity
  })
  return Object.entries(grouped).map(([name, value]) => ({
    name,
    value
  }))
})

// 计算属性：按颜色分组的库存数据（在选定工厂和产品内）
const colorGroupedData = computed(() => {
  const grouped = {}
  let filteredData = warehouseData.value
  
  if (currentFactory.value) {
    filteredData = filteredData.filter(item => (item.factory?.name || item.factory) === currentFactory.value)
  }
  if (currentProduct.value) {
    filteredData = filteredData.filter(item => (item.product?.name || item.product) === currentProduct.value)
  }
  
  filteredData.forEach(item => {
    if (!grouped[item.color]) {
      grouped[item.color] = 0
    }
    grouped[item.color] += item.quantity
  })
  return Object.entries(grouped).map(([name, value]) => ({
    name,
    value
  }))
})

// 计算属性：按尺码分组的库存数据（在选定工厂、产品和颜色内）
const sizeGroupedData = computed(() => {
  const grouped = {}
  let filteredData = warehouseData.value
  
  if (currentFactory.value) {
    filteredData = filteredData.filter(item => (item.factory?.name || item.factory) === currentFactory.value)
  }
  if (currentProduct.value) {
    filteredData = filteredData.filter(item => (item.product?.name || item.product) === currentProduct.value)
  }
  if (currentColor.value) {
    filteredData = filteredData.filter(item => item.color === currentColor.value)
  }
  
  filteredData.forEach(item => {
    if (!grouped[item.size]) {
      grouped[item.size] = 0
    }
    grouped[item.size] += item.quantity
  })
  return Object.entries(grouped).map(([name, value]) => ({
    name,
    value
  }))
})

// 计算属性：获取生产计划中的数量限制
const getProductionPlanLimit = computed(() => {
  return (factoryId, productId, color, size) => {
    if (!factoryId || !productId) return null
    
    // 获取工厂名称
    const factory = factories.value.find(f => f.id === factoryId)
    if (!factory) return null
    
    // 获取产品名称
    const product = products.value.find(p => p.id === productId)
    if (!product) return null
    
    let totalLimit = 0
    
    // 遍历所有生产计划
    productionPlans.value.forEach(plan => {
      // 检查是否匹配工厂
      if (plan.factory?.id === factoryId || plan.factory_id === factoryId) {
        // 遍历型号数据
        const modelsData = plan.models_data || plan.models || []
        modelsData.forEach(model => {
          // 检查是否匹配产品
          if (model.name === product.name) {
            // 遍历尺码数据
            const sizesData = plan.sizes_data || plan.sizes || []
            sizesData.forEach(sizeItem => {
              // 检查是否匹配颜色和尺码
              if (sizeItem.color === color && sizeItem.size === size) {
                const qty = Number(sizeItem.quantities?.[modelsData.indexOf(model)]) || 0
                totalLimit += qty
              }
            })
          }
        })
      }
    })
    
    return totalLimit > 0 ? totalLimit : null
  }
})

// 计算属性：获取已入库数量
const getCurrentWarehouseQuantity = computed(() => {
  return (factoryId, productId, color, size) => {
    if (!factoryId || !productId) return 0
    
    let totalQuantity = 0
    warehouseData.value.forEach(item => {
      if (item.factory?.id === factoryId && 
          item.product?.id === productId && 
          item.color === color && 
          item.size === size) {
        totalQuantity += Number(item.quantity) || 0
      }
    })
    
    return totalQuantity
  }
})

// 生命周期
onMounted(() => {
  fetchFactories()
  fetchProducts()
  fetchWarehouseData()
  fetchProductionPlans()
})

// 数据获取
const fetchFactories = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:9876/api/factories/')
    factories.value = response.data
  } catch (error) {
    console.error('Error fetching factories:', error)
  }
}

const fetchProducts = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:9876/api/products/')
    products.value = response.data
  } catch (error) {
    console.error('Error fetching products:', error)
  }
}

const fetchWarehouseData = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:9876/api/warehouse/')
    warehouseData.value = response.data
    initPieChart()
  } catch (error) {
    console.error('Error fetching warehouse data:', error)
  }
}

// 获取生产计划数据
const fetchProductionPlans = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:9876/api/production-plan-details/')
    productionPlans.value = response.data
  } catch (error) {
    console.error('Error fetching production plans:', error)
  }
}

// 检查是否为深色模式
const isDarkMode = () => document.documentElement.classList.contains('dark-mode')

// 处理饼图点击事件 - 与首页一致
const handlePieClick = (params) => {
  switch (currentInventoryLevel.value) {
    case 'factory':
      // 点击工厂，显示工厂产品分布
      currentFactory.value = params.name
      currentInventoryLevel.value = 'product'
      showBackButton.value = true
      initPieChart()
      break
    case 'product':
      // 点击产品，显示产品颜色分布
      currentProduct.value = params.name
      currentInventoryLevel.value = 'color'
      showBackButton.value = true
      initPieChart()
      break
    case 'color':
      // 点击颜色，显示颜色尺码分布
      currentColor.value = params.name
      currentInventoryLevel.value = 'size'
      showBackButton.value = true
      initPieChart()
      break
    default:
      break
  }
}

// 返回上一级
const goBack = () => {
  switch (currentInventoryLevel.value) {
    case 'size':
      currentInventoryLevel.value = 'color'
      currentColor.value = ''
      initPieChart()
      break
    case 'color':
      currentInventoryLevel.value = 'product'
      currentProduct.value = ''
      initPieChart()
      break
    case 'product':
      currentInventoryLevel.value = 'factory'
      currentFactory.value = ''
      showBackButton.value = false
      initPieChart()
      break
    default:
      break
  }
}

// 图表初始化 - 完全复用首页饼图代码
const initPieChart = () => {
  if (!pieChartRef.value) return
  
  try {
    // 先销毁现有实例，避免重复初始化
    if (pieChart.value) {
      pieChart.value.dispose()
    }
    
    pieChart.value = echarts.init(pieChartRef.value)
    const isDark = isDarkMode()
    
    // 根据当前层级获取数据
    let chartData = []
    let seriesName = '库存数量'
    
    // 定义颜色方案 - 与首页一致
    const colorScheme = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4']
    
    switch (currentInventoryLevel.value) {
      case 'factory':
        chartData = factoryGroupedData.value
        seriesName = '工厂库存'
        break
      case 'product':
        chartData = productGroupedData.value
        seriesName = '产品库存'
        break
      case 'color':
        chartData = colorGroupedData.value
        seriesName = '颜色库存'
        break
      case 'size':
        chartData = sizeGroupedData.value
        seriesName = '尺码库存'
        break
      default:
        chartData = factoryGroupedData.value
        seriesName = '库存数量'
    }
    
    const option = {
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        borderColor: '#409EFF',
        borderWidth: 1,
        textStyle: {
          color: '#fff',
          fontSize: 12
        },
        formatter: function(params) {
          return params.seriesName + '<br/>' +
                 params.marker + params.name + ': ' + params.value + ' (' + params.percent + '%)'
        }
      },
      legend: {
        orient: 'vertical',
        left: 'left',
        type: 'scroll',
        textStyle: {
          color: isDark ? '#e0e0e0' : '#333'
        },
        formatter: function(name) {
          return name.length > 8 ? name.substring(0, 8) + '...' : name
        },
        top: '10%',
        bottom: '10%'
      },
      color: colorScheme,
      series: [
        {
          name: seriesName,
          type: 'pie',
          radius: ['40%', '70%'],
          center: ['60%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 10,
            borderColor: isDark ? '#333' : '#fff',
            borderWidth: 2
          },
          label: {
            show: false,
            position: 'center'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 18,
              fontWeight: 'bold',
              color: isDark ? '#e0e0e0' : '#333'
            },
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          },
          labelLine: {
            show: false
          },
          data: chartData
        }
      ]
    }
    
    pieChart.value.setOption(option)
    
    // 添加点击事件
    pieChart.value.off('click')
    pieChart.value.on('click', handlePieClick)
  } catch (error) {
    console.error('Error initializing pie chart:', error)
  }
}

// 工厂切换
const handleFactoryChange = () => {
  // 重置饼图层级
  currentInventoryLevel.value = 'factory'
  currentFactory.value = ''
  currentProduct.value = ''
  currentColor.value = ''
  showBackButton.value = false
  initPieChart()
}

// 产品颜色和尺码自动获取
const handleProductChange = async (productId, index = null) => {
  try {
    const response = await axios.get(`http://127.0.0.1:9876/api/products/${productId}/`)
    const colors = response.data.colors ? response.data.colors.split(',').map(color => ({ value: color, label: color })) : []
    const sizes = response.data.specifications ? response.data.specifications.split(',').map(size => ({ value: size, label: size })) : []
    
    if (index !== null) {
      // 批量模式下更新对应项的颜色和尺码
      batchItemColors.value[index] = colors
      batchItemSizes.value[index] = sizes
    } else {
      // 单个模式下更新全局颜色和尺码
      productColors.value = colors
      productSizes.value = sizes
    }
  } catch (error) {
    console.error('Error fetching product details:', error)
  }
}

// 表单操作
const openDialog = () => {
  form.value = {
    product: '',
    color: '',
    size: '',
    quantity: '',
    factory: selectedFactory.value
  }
  productColors.value = []
  dialogVisible.value = true
}

// 编辑操作
const openEditDialog = (item) => {
  editForm.value = {
    id: item.id,
    product: item.product.id,
    color: item.color,
    size: item.size,
    quantity: item.quantity,
    factory: item.factory.id
  }
  handleProductChange(item.product.id)
  editDialogVisible.value = true
}

// 保存编辑
const saveEdit = async () => {
  try {
    // 验证数量限制
    const validation = validateQuantityLimit(
      editForm.value.factory,
      editForm.value.product,
      editForm.value.color,
      editForm.value.size,
      editForm.value.quantity,
      editForm.value.id
    )
    
    if (!validation.valid) {
      alert(validation.message)
      return
    }
    
    await axios.put(`http://127.0.0.1:9876/api/warehouse/${editForm.value.id}/`, editForm.value)
    editDialogVisible.value = false
    fetchWarehouseData()
  } catch (error) {
    console.error('Error updating warehouse item:', error)
  }
}

// 删除操作
const deleteItem = async (id) => {
  try {
    await axios.delete(`http://127.0.0.1:9876/api/warehouse/${id}/`)
    fetchWarehouseData()
  } catch (error) {
    console.error('Error deleting warehouse item:', error)
  }
}

const addBatchItem = () => {
  batchForm.value.items.push({ product: '', color: '', size: '', quantity: '' })
}

const removeBatchItem = (index) => {
  batchForm.value.items.splice(index, 1)
}

// 验证数量是否超过生产计划限制
const validateQuantityLimit = (factoryId, productId, color, size, quantity, excludeId = null) => {
  const limit = getProductionPlanLimit.value(factoryId, productId, color, size)
  if (!limit) return { valid: true, message: null }
  
  const currentQty = getCurrentWarehouseQuantity.value(factoryId, productId, color, size)
  // 如果是编辑模式，需要减去当前记录的原有数量
  let existingQty = 0
  if (excludeId) {
    const existingItem = warehouseData.value.find(item => item.id === excludeId)
    if (existingItem) {
      existingQty = Number(existingItem.quantity) || 0
    }
  }
  
  const newTotal = currentQty - existingQty + Number(quantity)
  
  if (newTotal > limit) {
    return {
      valid: false,
      message: `添加数量超过生产计划限制！\n\n计划数量：${limit}\n已入库：${currentQty - existingQty}\n本次添加：${quantity}\n超出：${newTotal - limit}`
    }
  }
  
  return { valid: true, message: null }
}

const saveSingleItem = async () => {
  try {
    // 验证数量限制
    const validation = validateQuantityLimit(
      form.value.factory,
      form.value.product,
      form.value.color,
      form.value.size,
      form.value.quantity
    )
    
    if (!validation.valid) {
      alert(validation.message)
      return
    }
    
    await axios.post('http://127.0.0.1:9876/api/warehouse/', form.value)
    dialogVisible.value = false
    fetchWarehouseData()
  } catch (error) {
    console.error('Error saving warehouse item:', error)
  }
}

const saveBatchItems = async () => {
  try {
    // 先验证所有项目的数量限制
    for (const item of batchForm.value.items) {
      const sizes = item.sizes && item.sizes.length > 0 ? item.sizes : [item.size]
      
      for (const size of sizes) {
        if (!size) continue
        
        const validation = validateQuantityLimit(
          batchForm.value.factory,
          item.product,
          item.color,
          size,
          item.quantity
        )
        
        if (!validation.valid) {
          alert(`产品 ${item.product} - ${item.color} - ${size}:\n${validation.message}`)
          return
        }
      }
    }
    
    // 验证通过后保存
    for (const item of batchForm.value.items) {
      // 如果选择了多个尺码，为每个尺码创建一条记录
      if (item.sizes && item.sizes.length > 0) {
        for (const size of item.sizes) {
          await axios.post('http://127.0.0.1:9876/api/warehouse/', {
            product: item.product,
            color: item.color,
            size: size,
            quantity: item.quantity,
            factory: batchForm.value.factory
          })
        }
      } else if (item.size) {
        // 兼容旧的单个尺码模式
        await axios.post('http://127.0.0.1:9876/api/warehouse/', {
          ...item,
          factory: batchForm.value.factory
        })
      }
    }
    batchForm.value = {
      factory: '',
      items: [{ product: '', color: '', sizes: [], quantity: '' }]
    }
    batchItemColors.value = {}
    batchItemSizes.value = {}
    fetchWarehouseData()
  } catch (error) {
    console.error('Error saving batch items:', error)
  }
}

// 响应式调整
const handleResize = () => {
  if (pieChart.value) {
    pieChart.value.resize()
  }
  if (detailChart.value) {
    detailChart.value.resize()
  }
}

window.addEventListener('resize', handleResize)

// 计划添加功能
const openPlanDialog = () => {
  selectedPlan.value = null
  planDialogVisible.value = true
}

const savePlanProducts = async () => {
  if (!selectedPlan.value) return
  
  try {
    const plan = selectedPlan.value
    const sizesData = plan.sizes_data || plan.sizes || []
    const modelsData = plan.models_data || plan.models || []
    
    // 遍历所有尺码和型号，创建出库记录
    for (const sizeItem of sizesData) {
      for (let modelIndex = 0; modelIndex < modelsData.length; modelIndex++) {
        const model = modelsData[modelIndex]
        const quantity = Number(sizeItem.quantities?.[modelIndex]) || 0
        
        if (quantity > 0) {
          // 查找对应的产品
          const product = products.value.find(p => p.name === model.name)
          if (product) {
            // 验证数量限制
            const validation = validateQuantityLimit(
              plan.factory?.id || plan.factory_id,
              product.id,
              model.color,
              sizeItem.name,
              quantity
            )
            
            if (!validation.valid) {
              alert(`产品 ${model.name} - ${model.color} - ${sizeItem.name}:
${validation.message}`)
              return
            }
            
            // 保存出库记录
            await axios.post('http://127.0.0.1:9876/api/warehouse/', {
              product: product.id,
              color: model.color,
              size: sizeItem.name,
              quantity: quantity,
              factory: plan.factory?.id || plan.factory_id
            })
          }
        }
      }
    }
    
    planDialogVisible.value = false
    fetchWarehouseData()
  } catch (error) {
    console.error('Error saving plan products:', error)
  }
}

// 导入功能
const openImportDialog = () => {
  importVisible.value = true
}

const validateImportData = (data) => {
  const errors = []
  data.forEach((row, index) => {
    if (!row.product) {
      errors.push(`第 ${index + 1} 行：产品名称不能为空`)
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
    if (!row.factory) {
      errors.push(`第 ${index + 1} 行：工厂名称不能为空`)
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
      // 查找产品ID
      const product = products.value.find(p => p.name === row.product)
      if (!product) {
        throw new Error(`产品 ${row.product} 不存在`)
      }

      // 查找工厂ID
      const factory = factories.value.find(f => f.name === row.factory)
      if (!factory) {
        throw new Error(`工厂 ${row.factory} 不存在`)
      }

      // 验证数量限制
      const validation = validateQuantityLimit(
        factory.id,
        product.id,
        row.color,
        row.size,
        row.quantity
      )

      if (!validation.valid) {
        throw new Error(validation.message)
      }

      // 保存数据
      await axios.post('http://127.0.0.1:9876/api/warehouse/', {
        product: product.id,
        color: row.color,
        size: row.size,
        quantity: row.quantity,
        factory: factory.id
      })
      importSuccessCount.value++
    } catch (error) {
      importErrorCount.value++
      importErrors.value.push(`第 ${i + 1} 行：${error.message}`)
    }
    importProgress.value = Math.round((i + 1) / total * 100)
  }

  await fetchWarehouseData()
  importVisible.value = false
}

// 计算计划总数量
const calculatePlanTotal = (plan) => {
  let total = 0
  const sizesData = plan.sizes_data || plan.sizes || []
  sizesData.forEach(sizeItem => {
    const quantities = sizeItem.quantities || []
    quantities.forEach(qty => {
      total += Number(qty) || 0
    })
  })
  return total
}

// 导出功能
const exportToExcel = async () => {
  const workbook = new ExcelJS.Workbook()
  const worksheet = workbook.addWorksheet('计划出库数据')

  // 设置表头
  worksheet.columns = [
    { header: '产品', key: 'product', width: 20 },
    { header: '颜色', key: 'color', width: 10 },
    { header: '尺码', key: 'size', width: 10 },
    { header: '数量', key: 'quantity', width: 10 },
    { header: '工厂', key: 'factory', width: 20 }
  ]

  // 填充数据
  warehouseData.value.forEach(item => {
    worksheet.addRow({
      product: item.product?.name || item.product,
      color: item.color,
      size: item.size,
      quantity: item.quantity,
      factory: item.factory?.name || item.factory
    })
  })

  // 生成Excel文件
  const buffer = await workbook.xlsx.writeBuffer()
  const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `计划出库数据_${new Date().toISOString().split('T')[0]}.xlsx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div class="warehouse-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>计划出库管理</span>
          <div class="header-actions">
            <el-select v-model="selectedFactory" placeholder="选择工厂" @change="handleFactoryChange">
              <el-option
                v-for="factory in factories"
                :key="factory.id"
                :label="factory.name"
                :value="factory.id"
              />
            </el-select>
            <el-button type="primary" @click="openDialog">添加产品</el-button>
            <el-button type="info" @click="openPlanDialog">按计划添加</el-button>
            <el-button @click="batchMode = !batchMode">
              {{ batchMode ? '单个添加' : '批量录入' }}
            </el-button>
            <el-button type="success" @click="exportToExcel">导出数据</el-button>
            <el-button type="warning" @click="openImportDialog">导入数据</el-button>
          </div>
        </div>
      </template>
      
      <!-- 批量录入模式 -->
      <div v-if="batchMode" class="batch-mode">
        <el-form :model="batchForm" label-width="80px">
          <el-form-item label="工厂">
            <el-select v-model="batchForm.factory" placeholder="选择工厂" style="width: 100%">
              <el-option
                v-for="factory in factories"
                :key="factory.id"
                :label="factory.name"
                :value="factory.id"
              />
            </el-select>
          </el-form-item>
          
          <div v-for="(item, index) in batchForm.items" :key="index" class="batch-item">
            <el-divider :content-inset="'40px'">产品 {{ index + 1 }}</el-divider>
            <el-form :model="item" label-width="80px">
              <el-form-item label="产品">
                <el-select v-model="item.product" placeholder="选择产品" style="width: 100%" @change="handleProductChange(item.product, index)">
                  <el-option
                    v-for="product in products"
                    :key="product.id"
                    :label="product.name"
                    :value="product.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="颜色">
                <el-select v-model="item.color" placeholder="选择颜色" style="width: 100%">
                  <el-option
                    v-for="color in batchItemColors[index] || []"
                    :key="color.value"
                    :label="color.label"
                    :value="color.value"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="尺码">
                <el-select v-model="item.sizes" multiple placeholder="选择尺码" style="width: 100%">
                  <el-option
                    v-for="size in batchItemSizes[index] || []"
                    :key="size.value"
                    :label="size.label"
                    :value="size.value"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="数量">
                <el-input v-model.number="item.quantity" type="number" placeholder="输入数量" />
              </el-form-item>
              <el-button type="danger" @click="removeBatchItem(index)" v-if="batchForm.items.length > 1">删除</el-button>
            </el-form>
          </div>
          
          <el-button type="primary" @click="addBatchItem">添加产品</el-button>
          <el-button type="success" @click="saveBatchItems" style="margin-left: 10px">保存批量数据</el-button>
        </el-form>
      </div>
      
      <!-- 单个添加模式 -->
      <div v-else class="single-mode">
        <el-table :data="currentWarehouseData" style="width: 100%">
          <el-table-column label="产品" width="180">
            <template #default="scope">
              {{ scope.row.product.name }}
            </template>
          </el-table-column>
          <el-table-column prop="color" label="颜色" width="120" />
          <el-table-column prop="size" label="尺码" width="100" />
          <el-table-column prop="quantity" label="数量" width="120" />
          <el-table-column label="工厂">
            <template #default="scope">
              {{ scope.row.factory.name }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150">
            <template #default="scope">
              <el-button type="primary" size="small" @click="openEditDialog(scope.row)">编辑</el-button>
              <el-button type="danger" size="small" @click="deleteItem(scope.row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
    
    <!-- 库存分布图表 -->
    <el-card shadow="hover" style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <span>库存分布</span>
          <el-button v-if="showBackButton" type="info" @click="goBack">返回上一级</el-button>
        </div>
      </template>
      <div ref="pieChartRef" style="width: 100%; height: 400px;"></div>
    </el-card>
    
    <!-- 添加产品对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="添加产品"
      width="500px"
    >
      <el-form :model="form" label-width="80px">
        <el-form-item label="产品">
          <el-select v-model="form.product" placeholder="选择产品" style="width: 100%" @change="handleProductChange">
            <el-option
              v-for="product in products"
              :key="product.id"
              :label="product.name"
              :value="product.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="颜色">
          <el-select v-model="form.color" placeholder="选择颜色" style="width: 100%">
            <el-option
              v-for="color in productColors"
              :key="color.value"
              :label="color.label"
              :value="color.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="尺码">
          <el-select v-model="form.size" placeholder="选择尺码" style="width: 100%">
            <el-option
              v-for="size in sizeOptions"
              :key="size.value"
              :label="size.label"
              :value="size.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="数量">
          <el-input v-model.number="form.quantity" type="number" placeholder="输入数量" />
        </el-form-item>
        <el-form-item label="工厂">
          <el-select v-model="form.factory" placeholder="选择工厂" style="width: 100%">
            <el-option
              v-for="factory in factories"
              :key="factory.id"
              :label="factory.name"
              :value="factory.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveSingleItem">保存</el-button>
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
        <el-form-item label="产品">
          <el-select v-model="editForm.product" placeholder="选择产品" style="width: 100%" @change="handleProductChange">
            <el-option
              v-for="product in products"
              :key="product.id"
              :label="product.name"
              :value="product.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="颜色">
          <el-select v-model="editForm.color" placeholder="选择颜色" style="width: 100%">
            <el-option
              v-for="color in productColors"
              :key="color.value"
              :label="color.label"
              :value="color.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="尺码">
          <el-select v-model="editForm.size" placeholder="选择尺码" style="width: 100%">
            <el-option
              v-for="size in sizeOptions"
              :key="size.value"
              :label="size.label"
              :value="size.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="数量">
          <el-input v-model.number="editForm.quantity" type="number" placeholder="输入数量" />
        </el-form-item>
        <el-form-item label="工厂">
          <el-select v-model="editForm.factory" placeholder="选择工厂" style="width: 100%">
            <el-option
              v-for="factory in factories"
              :key="factory.id"
              :label="factory.name"
              :value="factory.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveEdit">保存</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 导入组件 -->
    <ImportComponent
      v-model:visible="importVisible"
      :validate="validateImportData"
      @success="handleImportSuccess"
      :fields="['product', 'color', 'size', 'quantity', 'factory']"
      :field-labels="{ product: '产品', color: '颜色', size: '尺码', quantity: '数量', factory: '工厂' }"
    />
    
    <!-- 计划选择对话框 -->
    <el-dialog
      v-model="planDialogVisible"
      title="按计划添加产品"
      width="600px"
    >
      <el-form label-width="80px">
        <el-form-item label="选择计划">
          <el-select v-model="selectedPlan" placeholder="选择生产计划" style="width: 100%">
            <el-option
              v-for="plan in productionPlans"
              :key="plan.id"
              :label="`${plan.name} (${plan.date})`"
              :value="plan"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="selectedPlan">
          <el-card shadow="hover">
            <div class="plan-details">
              <p><strong>计划名称：</strong>{{ selectedPlan.name }}</p>
              <p><strong>计划日期：</strong>{{ selectedPlan.date }}</p>
              <p><strong>目标工厂：</strong>{{ selectedPlan.factory?.name || '未知' }}</p>
              <p><strong>型号数量：</strong>{{ (selectedPlan.models_data || selectedPlan.models || []).length }} 个</p>
              <p><strong>总数量：</strong>{{ calculatePlanTotal(selectedPlan) }} 套</p>
            </div>
          </el-card>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="planDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="savePlanProducts">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.warehouse-management {
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
}

.batch-mode {
  padding: 20px 0;
}

.batch-item {
  margin-bottom: 20px;
  padding: 10px;
  border: 1px solid #eaeaea;
  border-radius: 4px;
}

.single-mode {
  padding: 20px 0;
}

.dialog-footer {
  width: 100%;
  display: flex;
  justify-content: flex-end;
}

/* 深色模式支持 */
:deep(.dark-mode .el-select__wrapper) {
  background-color: var(--card-bg) !important;
  border-color: var(--border-color) !important;
}

:deep(.dark-mode .el-select__placeholder) {
  color: var(--text-color) !important;
}

:deep(.dark-mode .el-select__caret) {
  color: var(--text-color) !important;
}

:deep(.dark-mode .el-select-dropdown) {
  background-color: var(--card-bg) !important;
  border-color: var(--border-color) !important;
}

:deep(.dark-mode .el-select-dropdown__item) {
  color: var(--text-color) !important;
}

:deep(.dark-mode .el-select-dropdown__item:hover) {
  background-color: rgba(255, 255, 255, 0.1) !important;
}

:deep(.dark-mode .el-select-dropdown__item.selected) {
  background-color: rgba(64, 158, 255, 0.2) !important;
  color: #409EFF !important;
}

/* 表格样式调整 */
.single-mode .el-table {
  width: 100% !important;
}

.single-mode .el-table__inner-wrapper {
  width: 100% !important;
  overflow-x: hidden !important;
}

.single-mode .el-table__header-wrapper {
  width: 100% !important;
}

.single-mode .el-table__header {
  width: 100% !important;
  min-width: 100% !important;
}

.single-mode .el-table__body-wrapper {
  width: 100% !important;
}

.single-mode .el-table__body {
  width: 100% !important;
  min-width: 100% !important;
}

.single-mode .el-table__row {
  width: 100% !important;
  min-width: 100% !important;
}

.single-mode .el-table__cell {
  box-sizing: border-box !important;
}
</style>