<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <h2>生产数据看板</h2>
      <div class="header-actions">
        <el-button v-if="showBackButton" type="info" @click="goBack">返回上一级</el-button>
        <el-button type="success" @click="openDataManagement">数据管理</el-button>
      </div>
    </div>
    <div class="chart-row">
      <div class="chart-item">
        <div class="chart-header">生产进度</div>
        <div ref="chartContainer1" class="chart-container"></div>
      </div>
      <div class="chart-item">
        <div class="chart-header">{{ inventoryChartTitle }}</div>
        <div ref="chartContainer2" class="chart-container"></div>
      </div>
      <div class="chart-item">
        <div class="chart-header">调拨趋势</div>
        <div ref="chartContainer3" class="chart-container"></div>
      </div>
    </div>

    <!-- 数据管理弹窗 -->
    <el-dialog
      v-model="dataManagementVisible"
      title="数据管理"
      width="600px"
    >
      <div class="data-management-content">
        <h3>一键备份所有数据</h3>
        <p>点击下方按钮可以将所有模块的数据导出为Excel文件，包含：</p>
        <ul>
          <li>工厂数据</li>
          <li>产品数据</li>
          <li>仓库数据</li>
          <li>出库记录</li>
        </ul>
        
        <el-button type="primary" @click="backupAllData" :disabled="backupProgress > 0">
          {{ backupProgress > 0 ? '备份中...' : '一键备份' }}
        </el-button>
        
        <div v-if="backupProgress > 0" class="progress-container">
          <el-progress :percentage="backupProgress" :format="() => `${backupProgress}%`" />
        </div>
        
        <div v-if="backupSuccess" class="success-message">
          <el-icon name="Check" /> 备份成功！文件已下载
        </div>
        
        <div v-if="backupError" class="error-message">
          <el-icon name="Close" /> 备份失败：{{ backupError }}
        </div>
        
        <div class="divider"></div>
        
        <h3>一键导入所有数据</h3>
        <p>上传Excel文件可以批量导入所有模块的数据</p>
        
        <el-upload
          class="upload-demo"
          :auto-upload="false"
          :on-change="handleFileUpload"
          accept=".xlsx"
        >
          <el-button type="warning">选择Excel文件</el-button>
        </el-upload>
        
        <div v-if="importProgress > 0" class="progress-container">
          <el-progress :percentage="importProgress" :format="() => `${importProgress}%`" />
        </div>
        
        <div v-if="importSuccess" class="success-message">
          <el-icon name="Check" /> 导入成功！
        </div>
        
        <div v-if="importError" class="error-message">
          <el-icon name="Close" /> 导入失败：{{ importError }}
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dataManagementVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import * as echarts from 'echarts'
import api from '../utils/axios'
import * as ExcelJS from 'exceljs'
import { ElMessage } from 'element-plus'
import { Check, Close } from '@element-plus/icons-vue'
import { templateLabelForKey, isKnownTemplateKey } from '../constants/productionTemplates.js'

export default {
  data() {
    return {
      chart1: null,
      chart2: null,
      chart3: null,
      // 图表交互相关
      showBackButton: false,
      inventoryChartTitle: '库存分布',
      currentInventoryLevel: 'factory', // factory, product, color, size
      currentFactory: '',
      currentProduct: '',
      currentColor: '',
      // 数据管理相关
      dataManagementVisible: false,
      backupProgress: 0,
      importProgress: 0,
      backupSuccess: false,
      importSuccess: false,
      backupError: '',
      importError: '',
      /** 成品库存原始行（双仓），用于饼图下钻与汇总 */
      warehouseStocksRaw: [],
      /** 生产进度柱状图：name / plan / actual，来自 API */
      productionData: [],
      /** 库存饼图顶层：按仓库汇总 */
      inventoryData: [],
      /** 调拨趋势折线：按月汇总已完成调拨件数 */
      outboundData: []
    }
  },
  methods: {
    extractList(res) {
      const d = res?.data
      if (Array.isArray(d)) return d
      if (d && Array.isArray(d.results)) return d.results
      return []
    },
    /** 与生产页模板用语一致：已知模板键用中文名，否则用产品显示名 */
    displayProductLabel(product) {
      if (!product) return '产品'
      if (typeof product === 'object') {
        const k = product.production_template_key
        if (k && isKnownTemplateKey(k)) return templateLabelForKey(k)
        return product.name || `产品#${product.id}`
      }
      return `产品#${product}`
    },
    /** 从后端拉取看板三张图所需数据 */
    async loadDashboardFromApi() {
      try {
        const [plansRes, progressRes, productsRes, warehouseRes] = await Promise.all([
          api.get('/production-plans/'),
          api.get('/production-progress/'),
          api.get('/products/'),
          api.get('/warehouse/')
        ])
        const plans = this.extractList(plansRes)
        const progresses = this.extractList(progressRes)
        const products = this.extractList(productsRes)
        const stocks = this.extractList(warehouseRes)

        const productNameById = {}
        for (const p of products) {
          productNameById[p.id] = this.displayProductLabel(p)
        }

        const actualByPlanId = {}
        for (const pr of progresses) {
          const pid = pr.plan
          if (pid == null) continue
          const q = Number(pr.current_quantity) || 0
          actualByPlanId[pid] = Math.max(actualByPlanId[pid] || 0, q)
        }

        this.productionData = plans.map((plan) => ({
          name: `${productNameById[plan.product] || '产品'} #${plan.id}`,
          plan: Number(plan.quantity) || 0,
          actual: actualByPlanId[plan.id] != null ? actualByPlanId[plan.id] : 0
        }))

        this.warehouseStocksRaw = stocks
        this.inventoryData = this.aggregateStocksByWarehouseName(stocks)

        const ordersRes = await api.get('/transfer-orders/')
        const orders = this.extractList(ordersRes)
        this.outboundData = this.buildTransferMonthlySeries(orders)
      } catch (e) {
        console.error('loadDashboardFromApi', e)
        ElMessage.error('看板数据加载失败，请检查网络或重新登录')
        this.productionData = []
        this.warehouseStocksRaw = []
        this.inventoryData = []
        this.outboundData = []
      }
    },
    aggregateStocksByWarehouseName(stocks) {
      const map = {}
      for (const row of stocks || []) {
        const wname = row.warehouse?.name || '未分配仓库'
        const q = Number(row.quantity) || 0
        map[wname] = (map[wname] || 0) + q
      }
      return Object.entries(map).map(([name, value]) => ({ name, value }))
    },
    stocksFilteredByWarehouse(warehouseName) {
      return (this.warehouseStocksRaw || []).filter(
        (r) => (r.warehouse?.name || '未分配仓库') === warehouseName
      )
    },
    aggregateByProductName(stocks) {
      const map = {}
      for (const row of stocks || []) {
        const pname = this.displayProductLabel(row.product)
        const q = Number(row.quantity) || 0
        map[pname] = (map[pname] || 0) + q
      }
      return Object.entries(map).map(([name, value]) => ({ name, value }))
    },
    aggregateByColor(stocks) {
      const map = {}
      for (const row of stocks || []) {
        const c = row.color || '—'
        const q = Number(row.quantity) || 0
        map[c] = (map[c] || 0) + q
      }
      return Object.entries(map).map(([name, value]) => ({ name, value }))
    },
    aggregateBySize(stocks) {
      const map = {}
      for (const row of stocks || []) {
        const s = row.size || '—'
        const q = Number(row.quantity) || 0
        map[s] = (map[s] || 0) + q
      }
      return Object.entries(map).map(([name, value]) => ({ name, value }))
    },
    buildTransferMonthlySeries(orders) {
      const completed = (orders || []).filter((o) => o.status === 'completed')
      const bucket = {}
      for (const o of completed) {
        const raw = o.completed_at || o.created_at
        if (!raw) continue
        const d = new Date(raw)
        if (Number.isNaN(d.getTime())) continue
        const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
        const items = o.items || []
        let qty = 0
        for (const it of items) {
          qty += Number(it.quantity) || 0
        }
        bucket[key] = (bucket[key] || 0) + qty
      }
      const keys = Object.keys(bucket).sort()
      if (!keys.length) {
        return []
      }
      return keys.map((k) => {
        const [y, m] = k.split('-').map(Number)
        const label = `${y}年${m}月`
        return { month: label, value: bucket[k] }
      })
    },
    updateCharts() {
      // 更新所有图表
      this.initChart1()
      this.initChart2()
      this.initChart3()
    },
    handleResize() {
      if (this.chart1) this.chart1.resize()
      if (this.chart2) this.chart2.resize()
      if (this.chart3) this.chart3.resize()
    },
    initCharts() {
      this.outboundData = this.sanitizeOutboundChartData(this.outboundData)
      
      // 确保容器尺寸正确
      const containers = [
        this.$refs.chartContainer1,
        this.$refs.chartContainer2,
        this.$refs.chartContainer3
      ]
      
      containers.forEach(container => {
        if (container) {
          container.style.width = '100%'
          container.style.height = '300px'
          container.style.minHeight = '300px'
          container.style.boxSizing = 'border-box'
        }
      })
      
      // 强制浏览器重排，确保容器尺寸已确定
      window.dispatchEvent(new Event('resize'))
      
      // 延迟初始化，确保容器尺寸已确定
      setTimeout(() => {
        this.initChart1()
        this.initChart2()
        this.initChart3()
      }, 500)
    },
    // 检查是否为深色模式
    isDarkMode() {
      return document.documentElement.classList.contains('dark-mode')
    },
    /** 调拨趋势：localStorage/手工数据可能把 month 写成 "NaN" 或非字符串，类目轴会原样显示 */
    sanitizeOutboundChartData(source) {
      if (!source || !Array.isArray(source) || source.length === 0) {
        return []
      }
      const out = []
      for (let i = 0; i < source.length; i++) {
        const item = source[i]
        if (!item || typeof item !== 'object') continue
        const rawMonth = item.month
        const rawVal = item.value
        let monthStr = ''
        if (rawMonth != null && !(typeof rawMonth === 'number' && !Number.isFinite(rawMonth))) {
          monthStr = typeof rawMonth === 'string' ? rawMonth.trim() : String(rawMonth).trim()
        }
        if (
          !monthStr ||
          monthStr === 'NaN' ||
          monthStr === 'undefined' ||
          monthStr === 'null'
        ) {
          monthStr = `${out.length + 1}月`
        }
        const v = Number(rawVal)
        out.push({ month: monthStr, value: Number.isFinite(v) ? v : 0 })
      }
      return out
    },
    initChart1() {
      const chartContainer1 = this.$refs.chartContainer1
      if (!chartContainer1) return
      
      try {
        // 先销毁现有实例，避免重复初始化
        if (this.chart1) {
          this.chart1.dispose()
        }
        
        let rows = Array.isArray(this.productionData) ? this.productionData : []
        rows = rows
          .map((item) => ({
            name: item.name || '',
            plan: Number(item.plan) || 0,
            actual: Number(item.actual) || 0
          }))
          .filter((item) => item.name)
        if (!rows.length) {
          rows = [{ name: '暂无生产计划', plan: 0, actual: 0 }]
        }

        this.chart1 = echarts.init(chartContainer1)
        const isDark = this.isDarkMode()

        const planData = rows.map((item) => Number(item.plan) || 0)
        const actualData = rows.map((item) => Number(item.actual) || 0)
        const names = rows.map((item) => item.name || '')
        
        const option = {
          tooltip: {
            trigger: 'axis',
            axisPointer: {
              type: 'shadow',
              snap: true, // 吸附到数据点
              label: {
                show: true,
                position: 'top',
                formatter: function(params) {
                  return params.value;
                },
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                borderColor: '#409EFF',
                borderWidth: 1,
                color: '#fff',
                fontSize: 12
              }
            },
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            borderColor: '#409EFF',
            borderWidth: 1,
            color: '#fff',
            fontSize: 12,
            formatter: function(params) {
              let result = params[0].name + '<br/>';
              params.forEach(function(item) {
                result += item.marker + item.seriesName + ': ' + item.value + '<br/>';
              });
              return result;
            },
            position: 'top',
            triggerOn: 'mousemove'
          },
          legend: {
            data: ['计划数量', '已完成数量'],
            textStyle: {
              color: isDark ? '#e0e0e0' : '#333'
            },
            top: 'bottom', // 调整图例位置到底部
            bottom: '5%'
          },
          grid: {
            left: '3%',
            right: '4%',
            bottom: '15%', // 增加底部空间
            containLabel: true
          },
          xAxis: [
            {
              type: 'category',
              data: names,
              axisLabel: {
                rotate: 45,
                interval: 0,
                fontSize: 12,
                color: isDark ? '#e0e0e0' : '#333'
              },
              axisLine: {
                lineStyle: {
                  color: isDark ? '#444' : '#ccc'
                }
              },
              axisTick: {
                lineStyle: {
                  color: isDark ? '#444' : '#ccc'
                }
              }
            }
          ],
          yAxis: [
            {
              type: 'value',
              axisLabel: {
                color: isDark ? '#e0e0e0' : '#333'
              },
              axisLine: {
                lineStyle: {
                  color: isDark ? '#444' : '#ccc'
                }
              },
              axisTick: {
                lineStyle: {
                  color: isDark ? '#444' : '#ccc'
                }
              },
              splitLine: {
                lineStyle: {
                  color: isDark ? '#333' : '#eee'
                }
              }
            }
          ],
          series: [
            {
              name: '计划数量',
              type: 'bar',
              data: planData,
              label: {
                show: true,
                position: 'top',
                formatter: function(params) {
                  return params.value;
                },
                color: isDark ? '#e0e0e0' : '#333',
                fontSize: 12
              },
              emphasis: {
                itemStyle: {
                  shadowBlur: 10,
                  shadowOffsetX: 0,
                  shadowColor: 'rgba(0, 0, 0, 0.5)'
                }
              }
            },
            {
              name: '已完成数量',
              type: 'bar',
              data: actualData,
              label: {
                show: true,
                position: 'top',
                formatter: function(params) {
                  return params.value;
                },
                color: isDark ? '#e0e0e0' : '#333',
                fontSize: 12
              },
              emphasis: {
                itemStyle: {
                  shadowBlur: 10,
                  shadowOffsetX: 0,
                  shadowColor: 'rgba(0, 0, 0, 0.5)'
                }
              }
            }
          ]
        }
        this.chart1.setOption(option)
      } catch (error) {
        console.error('Error initializing chart 1:', error)
      }
    },
    // 返回上一级
    goBack() {
      switch (this.currentInventoryLevel) {
        case 'size':
          this.currentInventoryLevel = 'color'
          this.inventoryChartTitle = `${this.currentProduct} 颜色分布`
          this.initChart2()
          break
        case 'color':
          this.currentInventoryLevel = 'product'
          this.inventoryChartTitle = `${this.currentFactory} 产品分布`
          this.initChart2()
          break
        case 'product':
          this.currentInventoryLevel = 'factory'
          this.inventoryChartTitle = '库存分布'
          this.showBackButton = false
          this.initChart2()
          break
        default:
          break
      }
    },
    
    // 处理饼图点击事件
    handlePieClick(params) {
      switch (this.currentInventoryLevel) {
        case 'factory':
          // 点击车间，显示车间产品分布
          this.currentFactory = params.name
          this.currentInventoryLevel = 'product'
          this.inventoryChartTitle = `${params.name} 产品分布`
          this.showBackButton = true
          this.initChart2()
          break
        case 'product':
          // 点击产品，显示产品颜色分布
          this.currentProduct = params.name
          this.currentInventoryLevel = 'color'
          this.inventoryChartTitle = `${params.name} 颜色分布`
          this.initChart2()
          break
        case 'color':
          // 点击颜色，显示颜色尺码分布
          this.currentColor = params.name
          this.currentInventoryLevel = 'size'
          this.inventoryChartTitle = `${params.name} 尺码分布`
          this.initChart2()
          break
        default:
          break
      }
    },
    
    initChart2() {
      const chartContainer2 = this.$refs.chartContainer2
      if (!chartContainer2) return
      
      try {
        // 先销毁现有实例，避免重复初始化
        if (this.chart2) {
          this.chart2.dispose()
        }
        
        this.chart2 = echarts.init(chartContainer2)
        const isDark = this.isDarkMode()
        
        // 根据当前层级获取数据
        let chartData = []
        let seriesName = '库存数量'
        
        // 定义颜色方案
        const colorScheme = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4']
        
        switch (this.currentInventoryLevel) {
          case 'factory':
            chartData = this.inventoryData
            seriesName = '库存数量'
            break
          case 'product': {
            const st = this.stocksFilteredByWarehouse(this.currentFactory)
            chartData = this.aggregateByProductName(st)
            seriesName = '产品库存'
            break
          }
          case 'color': {
            const st = this.stocksFilteredByWarehouse(this.currentFactory).filter(
              (r) => this.displayProductLabel(r.product) === this.currentProduct
            )
            chartData = this.aggregateByColor(st)
            seriesName = '颜色库存'
            break
          }
          case 'size': {
            const st = this.stocksFilteredByWarehouse(this.currentFactory)
              .filter((r) => this.displayProductLabel(r.product) === this.currentProduct)
              .filter((r) => (r.color || '—') === this.currentColor)
            chartData = this.aggregateBySize(st)
            seriesName = '尺码库存'
            break
          }
          default:
            chartData = this.inventoryData
            seriesName = '库存数量'
        }

        if (!chartData || chartData.length === 0) {
          chartData = [{ name: '暂无', value: 0 }]
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
                     params.marker + params.name + ': ' + params.value + ' (' + params.percent + '%)';
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
            top: '10%', // 调整图例位置
            bottom: '10%'
          },
          color: colorScheme,
          series: [
            {
              name: seriesName,
              type: 'pie',
              radius: ['40%', '70%'],
              center: ['60%', '50%'], // 调整饼图位置
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
        this.chart2.setOption(option)
        
        // 添加点击事件
        this.chart2.off('click')
        this.chart2.on('click', this.handlePieClick.bind(this))
      } catch (error) {
        console.error('Error initializing chart 2:', error)
      }
    },
    // 数据管理方法
    openDataManagement() {
      this.dataManagementVisible = true
    },
    async backupAllData() {
      this.backupProgress = 0
      this.backupSuccess = false
      this.backupError = ''

      try {
        // 获取所有数据
        const [fRes, pRes, wRes, tRes] = await Promise.all([
          api.get('/factories/'),
          api.get('/products/'),
          api.get('/warehouse/'),
          api.get('/transfer-orders/')
        ])
        const factories = this.extractList(fRes)
        const products = this.extractList(pRes)
        const warehouse = this.extractList(wRes)
        const transferOrders = this.extractList(tRes)

        this.backupProgress = 30

        // 创建Excel工作簿
        const workbook = new ExcelJS.Workbook()
        
        // 添加工厂数据
        const factoryWorksheet = workbook.addWorksheet('工厂数据')
        factoryWorksheet.columns = [
          { header: '地区', key: 'location', width: 20 },
          { header: '车间', key: 'workshop', width: 20 }
        ]
        factories.forEach(item => {
          factoryWorksheet.addRow({
            location: item.location,
            workshop: item.workshop
          })
        })

        this.backupProgress = 50

        // 添加产品数据
        const productWorksheet = workbook.addWorksheet('产品数据')
        productWorksheet.columns = [
          { header: '排产模板键', key: 'production_template_key', width: 14 },
          { header: '产品名称', key: 'name', width: 20 },
          { header: '颜色选项', key: 'colors', width: 30 },
          { header: '规格参数', key: 'specifications', width: 30 }
        ]
        products.forEach(item => {
          productWorksheet.addRow({
            production_template_key: item.production_template_key || '',
            name: item.name,
            colors: item.colors || '',
            specifications: item.specifications || ''
          })
        })

        this.backupProgress = 70

        // 添加仓库数据
        const warehouseWorksheet = workbook.addWorksheet('仓库数据')
        warehouseWorksheet.columns = [
          { header: '产品', key: 'product', width: 20 },
          { header: '颜色', key: 'color', width: 10 },
          { header: '尺码', key: 'size', width: 10 },
          { header: '数量', key: 'quantity', width: 10 },
          { header: '工厂', key: 'factory', width: 20 }
        ]
        warehouse.forEach(item => {
          warehouseWorksheet.addRow({
            product: this.displayProductLabel(item.product),
            color: item.color,
            size: item.size,
            quantity: item.quantity,
            factory: item.factory?.name || item.factory
          })
        })

        this.backupProgress = 90

        // 添加调拨记录
        const outboundWorksheet = workbook.addWorksheet('调拨记录')
        outboundWorksheet.columns = [
          { header: '编号', key: 'id', width: 10 },
          { header: '源仓', key: 'from_warehouse', width: 20 },
          { header: '目标仓', key: 'to_warehouse', width: 20 },
          { header: '状态', key: 'status', width: 12 },
          { header: '创建时间', key: 'created_at', width: 22 }
        ]
        transferOrders.forEach(item => {
          outboundWorksheet.addRow({
            id: item.id,
            from_warehouse: item.from_warehouse?.name || '',
            to_warehouse: item.to_warehouse?.name || '',
            status: item.status || '',
            created_at: item.created_at || ''
          })
        })

        this.backupProgress = 100

        // 生成Excel文件
        const buffer = await workbook.xlsx.writeBuffer()
        const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `生产管理系统备份_${new Date().toISOString().split('T')[0]}.xlsx`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)

        this.backupSuccess = true
      } catch (error) {
        console.error('Error backing up data:', error)
        this.backupError = error.message || '备份失败'
      }
    },
    handleFileUpload(event) {
      const file = event.target.files[0]
      if (file) {
        this.importAllData(file)
      }
    },
    async importAllData(file) {
      this.importProgress = 0
      this.importSuccess = false
      this.importError = ''

      try {
        // 这里需要实现Excel文件解析和数据导入
        // 由于时间限制，这里只做一个示例
        this.importProgress = 100
        this.importSuccess = true
        alert('数据导入功能开发中，敬请期待！')
      } catch (error) {
        console.error('Error importing data:', error)
        this.importError = error.message || '导入失败'
      }
    },
    initChart3() {
      const chartContainer3 = this.$refs.chartContainer3
      if (!chartContainer3) return
      
      try {
        // 先销毁现有实例，避免重复初始化
        if (this.chart3) {
          this.chart3.dispose()
        }
        
        this.outboundData = this.sanitizeOutboundChartData(this.outboundData)
        
        this.chart3 = echarts.init(chartContainer3)
        const isDark = this.isDarkMode()
        
        const validOutboundData = this.outboundData.filter((item) => {
          if (!item || item.month == null) return false
          const m = typeof item.month === 'string' ? item.month.trim() : String(item.month).trim()
          return m.length > 0
        })
        let months = validOutboundData.map((item) => item.month || '')
        let values = validOutboundData.map((item) => Number(item.value) || 0)
        if (!months.length) {
          months = ['暂无已完成调拨']
          values = [0]
        }

        // cross + smooth 时，类目轴上的指示值可能是 NaN（内部插值坐标），不能 String(NaN)；
        // 应用 seriesData[0].name 或按索引取 months。
        const formatCrossAxisPointerLabel = (p) => {
          const dim = p.axisDimension || p.axisDim
          const v = p.value
          const fromSeries = () => {
            const sd = p.seriesData && p.seriesData[0]
            if (!sd) return ''
            if (sd.name != null && String(sd.name).trim() !== '') return String(sd.name)
            const di = sd.dataIndex
            if (typeof di === 'number' && months[di] != null) return months[di]
            return ''
          }
          if (dim === 'x') {
            if (typeof v === 'string' && v.trim() !== '') return v
            if (typeof v === 'number' && Number.isFinite(v)) {
              const idx = Math.round(v)
              if (months[idx] !== undefined) return months[idx]
              return String(Math.round(v))
            }
            const fb = fromSeries()
            return fb || ''
          }
          if (v === undefined || v === null) return ''
          if (typeof v === 'number' && !Number.isFinite(v)) return fromSeries() || ''
          if (typeof v === 'string') return v
          const n = Number(v)
          return Number.isFinite(n) ? Math.round(n) : fromSeries() || ''
        }
        
        // 存储当前选中的数据点索引
        let selectedPointIndex = -1
        // 用于防抖的定时器
        let hoverTimer = null
        
        const option = {
          tooltip: {
            trigger: 'axis',
            triggerOn: 'mousemove',
            axisPointer: {
              type: 'cross',
              snap: true, // 吸附到数据点
              label: {
                show: true,
                position: 'left',
                formatter: formatCrossAxisPointerLabel,
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                borderColor: '#409EFF',
                borderWidth: 1,
                color: '#fff',
                fontSize: 12
              },
              axis: 'y' // 指示线仍以 y 为主；标签 formatter 需兼容类目轴上的字符串
            },
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            borderColor: '#409EFF',
            borderWidth: 1,
            color: '#fff',
            fontSize: 12,
            formatter: function(params) {
              return params[0].name + '<br/>' +
                     params[0].marker + '调拨数量: ' + params[0].value;
            },
            position: function(point, params, dom, rect, size) {
              // 确保提示框跟随鼠标位置，同时避免溢出
              const boxWidth = size.contentSize[0]
              const boxHeight = size.contentSize[1]
              
              // 计算位置，确保提示框在容器内
              let posX = point[0]
              let posY = point[1] - boxHeight - 10
              
              // 边界检查
              if (posY < rect.top + 10) {
                posY = point[1] + 10
              }
              if (posX + boxWidth > rect.right - 10) {
                posX = rect.right - boxWidth - 10
              }
              if (posX < rect.left + 10) {
                posX = rect.left + 10
              }
              if (posY + boxHeight > rect.bottom - 10) {
                posY = rect.bottom - boxHeight - 10
              }
              
              return [posX, posY]
            }
          },
          legend: {
            data: ['调拨数量'],
            textStyle: {
              color: isDark ? '#e0e0e0' : '#333'
            },
            top: 'bottom',
            bottom: '5%'
          },
          grid: {
            left: '3%',
            right: '4%',
            bottom: '15%',
            containLabel: true
          },
          xAxis: [
            {
              type: 'category',
              data: months,
              axisLabel: {
                color: isDark ? '#e0e0e0' : '#333'
              },
              axisLine: {
                lineStyle: {
                  color: isDark ? '#444' : '#ccc'
                }
              },
              axisTick: {
                lineStyle: {
                  color: isDark ? '#444' : '#ccc'
                }
              }
            }
          ],
          yAxis: [
            {
              type: 'value',
              axisLabel: {
                color: isDark ? '#e0e0e0' : '#333'
              },
              axisLine: {
                lineStyle: {
                  color: isDark ? '#444' : '#ccc'
                }
              },
              axisTick: {
                lineStyle: {
                  color: isDark ? '#444' : '#ccc'
                }
              },
              splitLine: {
                lineStyle: {
                  color: isDark ? '#333' : '#eee'
                }
              }
            }
          ],
          series: [
            {
              name: '调拨数量',
              data: values,
              type: 'line',
              smooth: true,
              symbol: 'circle',
              symbolSize: 8,
              lineStyle: {
                width: 3
              },
              label: {
                show: true,
                position: 'top',
                formatter: function(params) {
                  return params.value;
                },
                color: isDark ? '#e0e0e0' : '#333',
                fontSize: 12
              },
              emphasis: {
                itemStyle: {
                  shadowBlur: 10,
                  shadowOffsetX: 0,
                  shadowColor: 'rgba(0, 0, 0, 0.5)',
                  borderColor: '#fff',
                  borderWidth: 2
                },
                focus: 'series',
                scale: true
              }
            }
          ]
        }
        this.chart3.setOption(option)
        
        // 添加鼠标移动事件 - 优化性能，使用防抖
        this.chart3.on('mousemove', function(params) {
          if (params.componentType === 'series' && params.seriesType === 'line' && params.dataIndex !== undefined) {
            // 清除之前的定时器
            if (hoverTimer) {
              clearTimeout(hoverTimer)
            }
            
            // 设置新的定时器，防抖处理
            hoverTimer = setTimeout(() => {
              // 鼠标靠近数据点时，选中该点
              selectedPointIndex = params.dataIndex
              // 获取当前系列数据
              const seriesData = this.getOption().series[0].data
              // 更新图表，显示选中状态
              this.setOption({
                series: [
                  {
                    data: seriesData,
                    symbolSize: function(val, params) {
                      return selectedPointIndex === params.dataIndex ? 12 : 8;
                    },
                    itemStyle: function(params) {
                      return {
                        color: selectedPointIndex === params.dataIndex ? '#ff7875' : '#5470c6',
                        borderColor: selectedPointIndex === params.dataIndex ? '#fff' : '#5470c6',
                        borderWidth: selectedPointIndex === params.dataIndex ? 2 : 1
                      };
                    }
                  }
                ]
              })
              // 固定显示选中点的数值
              const selectedValue = seriesData[selectedPointIndex]
              this.setOption({
                axisPointer: {
                  label: {
                    formatter: formatCrossAxisPointerLabel
                  }
                }
              })
            }, 30) // 减少防抖延迟，提高响应速度
          }
        })
        
        // 添加鼠标离开事件
        this.chart3.on('mouseout', function() {
          // 清除定时器
          if (hoverTimer) {
            clearTimeout(hoverTimer)
            hoverTimer = null
          }
          // 鼠标离开时，取消选中状态
          selectedPointIndex = -1
          // 更新图表，取消选中状态
          this.setOption({
            series: [
              {
                data: this.getOption().series[0].data,
                symbolSize: 8,
                itemStyle: {
                  color: '#5470c6',
                  borderColor: '#5470c6',
                  borderWidth: 1
                }
              }
            ]
          })
          // 恢复显示鼠标当前位置对应的数值
          this.setOption({
            axisPointer: {
              label: {
                formatter: formatCrossAxisPointerLabel
              }
            }
          })
        })
      } catch (error) {
        console.error('Error initializing chart 3:', error)
      }
    }
  },
  mounted() {
    window.addEventListener('resize', this.handleResize)
    this.loadDashboardFromApi().then(() => {
      setTimeout(() => {
        this.initCharts()
      }, 300)
    })
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.handleResize)
    if (this.chart1) this.chart1.dispose()
    if (this.chart2) this.chart2.dispose()
    if (this.chart3) this.chart3.dispose()
  }
}
</script>

<style scoped>
.dashboard {
  padding: 40px 20px;
  width: 100%;
  min-height: 400px;
  box-sizing: border-box;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid #eaeaea;
}

.dashboard-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: bold;
  color: #333;
}

:deep(.dark-mode .dashboard-header) {
  border-bottom-color: var(--border-color) !important;
}

:deep(.dark-mode .dashboard-header h2) {
  color: #e8eaed !important;
  font-weight: bold !important;
  font-size: 24px !important;
  margin: 0 !important;
}

.chart-header {
  padding: 20px;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid #eaeaea;
  background: #f2f2f2;
  box-sizing: border-box;
  flex-shrink: 0;
}

:deep(.dark-mode .chart-header) {
  background: #2a2d33 !important;
  border-bottom-color: var(--border-color) !important;
  color: #f2f3f5 !important;
  font-weight: bold !important;
}

.chart-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 20px;
  width: 100%;
  box-sizing: border-box;
}

.chart-item {
  min-width: 350px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 16px 0 rgba(0, 0, 0, 0.1);
  overflow: visible;
  display: flex;
  flex-direction: column;
  height: 420px;
  box-sizing: border-box;
  position: relative;
  z-index: 10;
  transition: all 0.3s ease;
}

.chart-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 24px 0 rgba(0, 0, 0, 0.15);
}

.chart-header {
  padding: 20px;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid #eaeaea;
  background: #f2f2f2;
  box-sizing: border-box;
  flex-shrink: 0;
}

.chart-container {
  flex: 1;
  width: 100%;
  min-height: 320px;
  padding: 20px;
  overflow: hidden;
  box-sizing: border-box;
}

@media (max-width: 768px) {
  .chart-row {
    grid-template-columns: 1fr;
  }
  
  .chart-item {
    min-width: 100%;
    height: 380px;
  }
  
  .chart-container {
    min-height: 300px;
  }
}

/* 调整图表容器高度 */
.chart-container {
  flex: 1;
  width: 100%;
  min-height: 340px;
  padding: 20px;
  overflow: hidden;
  box-sizing: border-box;
}

/* 头部操作区域样式 */
.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

:deep(.dark-mode .chart-item) {
  background: var(--card-bg);
  box-shadow: 0 4px 16px 0 rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;
}

:deep(.dark-mode .chart-item:hover) {
  transform: translateY(-5px);
  box-shadow: 0 8px 24px 0 rgba(0, 0, 0, 0.4);
}


/* 数据管理弹窗样式 */
.data-management-content {
  padding: 20px 0;
}

.data-management-content h3 {
  margin: 0 0 15px 0;
  font-size: 16px;
  font-weight: bold;
  color: #333;
}

.data-management-content p {
  margin: 0 0 10px 0;
  color: #666;
  line-height: 1.5;
}

.data-management-content ul {
  margin: 0 0 20px 20px;
  color: #666;
}

.data-management-content li {
  margin: 5px 0;
}

.progress-container {
  margin: 15px 0;
}

.success-message {
  margin: 15px 0;
  padding: 10px;
  background-color: #f0f9eb;
  border: 1px solid #e1f3d8;
  border-radius: 4px;
  color: #67c23a;
  display: flex;
  align-items: center;
  gap: 8px;
}

.error-message {
  margin: 15px 0;
  padding: 10px;
  background-color: #fef0f0;
  border: 1px solid #fde2e2;
  border-radius: 4px;
  color: #f56c6c;
  display: flex;
  align-items: center;
  gap: 8px;
}

.divider {
  height: 1px;
  background-color: #eaeaea;
  margin: 30px 0;
}

.upload-demo {
  margin: 15px 0;
}

:deep(.dark-mode .data-management-content h3) {
  color: #e0e0e0;
}

:deep(.dark-mode .data-management-content p),
:deep(.dark-mode .data-management-content li) {
  color: #b0b0b0;
}

:deep(.dark-mode .divider) {
  background-color: #444;
}

:deep(.dark-mode .success-message) {
  background-color: rgba(103, 194, 58, 0.1);
  border-color: rgba(103, 194, 58, 0.3);
  color: #67c23a;
}

:deep(.dark-mode .error-message) {
  background-color: rgba(245, 108, 108, 0.1);
  border-color: rgba(245, 108, 108, 0.3);
  color: #f56c6c;
}
</style>

<style>
/* 暗黑模式兜底：确保首页图表标题可读 */
.dark-mode .dashboard .chart-header {
  background: #2a2d33 !important;
  color: #f2f3f5 !important;
  border-bottom-color: #4a4f58 !important;
}
</style>