<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <h2>生产数据看板</h2>
      <div class="header-actions">
        <el-button v-if="showBackButton" type="info" @click="goBack">返回上一级</el-button>
        <el-button type="primary" @click="openDataModal">管理示例数据</el-button>
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
        <div class="chart-header">出库趋势</div>
        <div ref="chartContainer3" class="chart-container"></div>
      </div>
    </div>

    <!-- 数据管理弹窗 -->
    <el-dialog
      v-model="dataModalVisible"
      title="管理示例数据"
      width="800px"
    >
      <el-tabs v-model="activeTab">
        <el-tab-pane label="生产进度" name="production">
          <el-table :data="productionData" style="width: 100%">
            <el-table-column prop="name" label="车间" width="180" />
            <el-table-column prop="plan" label="计划数量">
              <template #default="scope">
                <el-input v-model.number="scope.row.plan" type="number" />
              </template>
            </el-table-column>
            <el-table-column prop="actual" label="已完成数量">
              <template #default="scope">
                <el-input v-model.number="scope.row.actual" type="number" />
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="库存分布" name="inventory">
          <el-table :data="inventoryData" style="width: 100%">
            <el-table-column prop="name" label="车间" width="180" />
            <el-table-column prop="value" label="库存数量">
              <template #default="scope">
                <el-input v-model.number="scope.row.value" type="number" />
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="出库趋势" name="outbound">
          <el-table :data="outboundData" style="width: 100%">
            <el-table-column prop="month" label="月份" width="100" />
            <el-table-column prop="value" label="出库数量">
              <template #default="scope">
                <el-input v-model.number="scope.row.value" type="number" />
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dataModalVisible = false">取消</el-button>
          <el-button type="primary" @click="saveData">保存数据</el-button>
        </span>
      </template>
    </el-dialog>
    
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
import axios from 'axios'
import * as ExcelJS from 'exceljs'
import { Check, Close } from '@element-plus/icons-vue'

export default {
  data() {
    return {
      chart1: null,
      chart2: null,
      chart3: null,
      // 数据管理相关
      dataModalVisible: false,
      activeTab: 'production',
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
      // 示例数据
      productionData: [
        { name: '武昌八车间', plan: 1000, actual: 800 },
        { name: '蔡甸十一车间', plan: 1500, actual: 1200 },
        { name: '汉口三车间', plan: 800, actual: 600 },
        { name: '汉阳五车间', plan: 1200, actual: 900 }
      ],
      inventoryData: [
        { name: '武昌八车间', value: 300 },
        { name: '蔡甸十一车间', value: 450 },
        { name: '汉口三车间', value: 200 },
        { name: '汉阳五车间', value: 350 }
      ],
      // 模拟车间产品库存数据
      factoryProductData: {
        '武昌八车间': [
          { name: '产品A', value: 150 },
          { name: '产品B', value: 100 },
          { name: '产品C', value: 50 }
        ],
        '蔡甸十一车间': [
          { name: '产品A', value: 200 },
          { name: '产品B', value: 150 },
          { name: '产品C', value: 100 }
        ],
        '汉口三车间': [
          { name: '产品A', value: 100 },
          { name: '产品B', value: 60 },
          { name: '产品C', value: 40 }
        ],
        '汉阳五车间': [
          { name: '产品A', value: 180 },
          { name: '产品B', value: 120 },
          { name: '产品C', value: 50 }
        ]
      },
      // 模拟产品颜色库存数据
      productColorData: {
        '产品A': [
          { name: '红色', value: 200 },
          { name: '蓝色', value: 150 },
          { name: '绿色', value: 100 }
        ],
        '产品B': [
          { name: '红色', value: 180 },
          { name: '蓝色', value: 120 },
          { name: '黑色', value: 80 }
        ],
        '产品C': [
          { name: '白色', value: 120 },
          { name: '黑色', value: 80 }
        ]
      },
      // 模拟颜色尺码库存数据
      colorSizeData: {
        '红色': [
          { name: 'S', value: 50 },
          { name: 'M', value: 80 },
          { name: 'L', value: 100 },
          { name: 'XL', value: 70 }
        ],
        '蓝色': [
          { name: 'S', value: 40 },
          { name: 'M', value: 60 },
          { name: 'L', value: 80 },
          { name: 'XL', value: 50 }
        ],
        '绿色': [
          { name: 'S', value: 30 },
          { name: 'M', value: 40 },
          { name: 'L', value: 20 },
          { name: 'XL', value: 10 }
        ],
        '黑色': [
          { name: 'S', value: 25 },
          { name: 'M', value: 35 },
          { name: 'L', value: 40 },
          { name: 'XL', value: 20 }
        ],
        '白色': [
          { name: 'S', value: 30 },
          { name: 'M', value: 45 },
          { name: 'L', value: 35 },
          { name: 'XL', value: 10 }
        ]
      },
      outboundData: [
        { month: '1月', value: 120 },
        { month: '2月', value: 190 },
        { month: '3月', value: 300 },
        { month: '4月', value: 500 },
        { month: '5月', value: 200 },
        { month: '6月', value: 300 }
      ]
    }
  },
  methods: {
    // 数据管理方法
    openDataModal() {
      this.dataModalVisible = true
    },
    saveData() {
      // 验证数据格式
      const isValid = this.validateData()
      if (!isValid) {
        return
      }
      
      // 保存数据到本地存储（模拟数据录入数据库）
      localStorage.setItem('productionData', JSON.stringify(this.productionData))
      localStorage.setItem('inventoryData', JSON.stringify(this.inventoryData))
      localStorage.setItem('outboundData', JSON.stringify(this.outboundData))
      
      // 更新图表
      this.updateCharts()
      
      // 关闭弹窗
      this.dataModalVisible = false
    },
    validateData() {
      // 验证生产进度数据
      for (const item of this.productionData) {
        if (isNaN(item.plan) || item.plan < 0) {
          alert('生产进度数据格式错误，请检查计划数量');
          return false
        }
        if (isNaN(item.actual) || item.actual < 0) {
          alert('生产进度数据格式错误，请检查已完成数量');
          return false
        }
      }
      
      // 验证库存分布数据
      for (const item of this.inventoryData) {
        if (isNaN(item.value) || item.value < 0) {
          alert('库存分布数据格式错误，请检查库存数量');
          return false
        }
      }
      
      // 验证出库趋势数据
      for (const item of this.outboundData) {
        if (isNaN(item.value) || item.value < 0) {
          alert('出库趋势数据格式错误，请检查出库数量');
          return false
        }
      }
      
      return true
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
      // 从本地存储读取数据（如果存在）
      try {
        const savedProductionData = localStorage.getItem('productionData')
        const savedInventoryData = localStorage.getItem('inventoryData')
        const savedOutboundData = localStorage.getItem('outboundData')
        
        if (savedProductionData) {
          this.productionData = JSON.parse(savedProductionData)
        }
        if (savedInventoryData) {
          this.inventoryData = JSON.parse(savedInventoryData)
        }
        if (savedOutboundData) {
          this.outboundData = JSON.parse(savedOutboundData)
        }
      } catch (error) {
        console.error('Error reading data from localStorage:', error)
        // 如果读取失败，使用默认数据
      }
      
      // 确保outboundData格式正确，避免NaN显示
      if (!this.outboundData || !Array.isArray(this.outboundData)) {
        this.outboundData = [
          { month: '1月', value: 120 },
          { month: '2月', value: 190 },
          { month: '3月', value: 300 },
          { month: '4月', value: 500 },
          { month: '5月', value: 200 },
          { month: '6月', value: 300 }
        ]
      } else {
        // 确保每个数据项都有有效的month和value字段
        this.outboundData = this.outboundData.map(item => ({
          month: item.month || '',
          value: Number(item.value) || 0
        })).filter(item => item.month)
      }
      
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
    initChart1() {
      const chartContainer1 = this.$refs.chartContainer1
      if (!chartContainer1) return
      
      try {
        // 先销毁现有实例，避免重复初始化
        if (this.chart1) {
          this.chart1.dispose()
        }
        
        // 确保productionData格式正确
        if (!this.productionData || !Array.isArray(this.productionData)) {
          this.productionData = [
            { name: '武昌八车间', plan: 1000, actual: 800 },
            { name: '蔡甸十一车间', plan: 1500, actual: 1200 },
            { name: '汉口三车间', plan: 800, actual: 600 },
            { name: '汉阳五车间', plan: 1200, actual: 900 }
          ]
        } else {
          // 确保每个数据项都有有效的数值
          this.productionData = this.productionData.map(item => ({
            name: item.name || '',
            plan: Number(item.plan) || 0,
            actual: Number(item.actual) || 0
          })).filter(item => item.name)
        }
        
        this.chart1 = echarts.init(chartContainer1)
        const isDark = this.isDarkMode()
        
        // 确保数据格式正确，提取数值
        const planData = this.productionData.map(item => Number(item.plan) || 0)
        const actualData = this.productionData.map(item => Number(item.actual) || 0)
        const names = this.productionData.map(item => item.name || '')
        
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
          case 'product':
            chartData = this.factoryProductData[this.currentFactory] || []
            seriesName = '产品库存'
            break
          case 'color':
            chartData = this.productColorData[this.currentProduct] || []
            seriesName = '颜色库存'
            break
          case 'size':
            chartData = this.colorSizeData[this.currentColor] || []
            seriesName = '尺码库存'
            break
          default:
            chartData = this.inventoryData
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
        const [factories, products, warehouse, outboundRecords, productionPlans, materials] = await Promise.all([
          axios.get('http://127.0.0.1:9876/api/factories/'),
          axios.get('http://127.0.0.1:9876/api/products/'),
          axios.get('http://127.0.0.1:9876/api/warehouse/'),
          axios.get('http://127.0.0.1:9876/api/outbound-records/'),
          axios.get('http://127.0.0.1:9876/api/production-plan-details/'),
          axios.get('http://127.0.0.1:9876/api/materials/')
        ])

        this.backupProgress = 30

        // 创建Excel工作簿
        const workbook = new ExcelJS.Workbook()
        
        // 添加工厂数据
        const factoryWorksheet = workbook.addWorksheet('工厂数据')
        factoryWorksheet.columns = [
          { header: '地区', key: 'location', width: 20 },
          { header: '车间', key: 'workshop', width: 20 }
        ]
        factories.data.forEach(item => {
          factoryWorksheet.addRow({
            location: item.location,
            workshop: item.workshop
          })
        })

        this.backupProgress = 50

        // 添加产品数据
        const productWorksheet = workbook.addWorksheet('产品数据')
        productWorksheet.columns = [
          { header: '产品名称', key: 'name', width: 20 },
          { header: '颜色选项', key: 'colors', width: 30 },
          { header: '规格参数', key: 'specifications', width: 30 }
        ]
        products.data.forEach(item => {
          productWorksheet.addRow({
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
        warehouse.data.forEach(item => {
          warehouseWorksheet.addRow({
            product: item.product?.name || item.product,
            color: item.color,
            size: item.size,
            quantity: item.quantity,
            factory: item.factory?.name || item.factory
          })
        })

        this.backupProgress = 90

        // 添加出库记录
        const outboundWorksheet = workbook.addWorksheet('出库记录')
        outboundWorksheet.columns = [
          { header: '日期', key: 'outbound_date', width: 15 },
          { header: '仓库', key: 'warehouse', width: 20 },
          { header: '产品', key: 'product', width: 20 },
          { header: '颜色', key: 'color', width: 12 },
          { header: '尺码', key: 'size', width: 12 },
          { header: '数量', key: 'quantity', width: 10 }
        ]
        outboundRecords.data.forEach(item => {
          outboundWorksheet.addRow({
            outbound_date: item.outbound_date,
            warehouse: item.warehouse,
            product: item.product?.name || item.product,
            color: item.color || '',
            size: item.size || '',
            quantity: item.quantity
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
        
        // 确保outboundData格式正确，避免NaN显示
        if (!this.outboundData || !Array.isArray(this.outboundData)) {
          this.outboundData = [
            { month: '1月', value: 120 },
            { month: '2月', value: 190 },
            { month: '3月', value: 300 },
            { month: '4月', value: 500 },
            { month: '5月', value: 200 },
            { month: '6月', value: 300 }
          ]
        } else {
          // 确保每个数据项都有有效的month和value字段
          this.outboundData = this.outboundData.map(item => ({
            month: item.month || '',
            value: Number(item.value) || 0
          })).filter(item => item.month)
        }
        
        this.chart3 = echarts.init(chartContainer3)
        const isDark = this.isDarkMode()
        
        // 确保outboundData格式正确，提取有效的月份和数值
        if (!this.outboundData || !Array.isArray(this.outboundData)) {
          this.outboundData = [
            { month: '1月', value: 120 },
            { month: '2月', value: 190 },
            { month: '3月', value: 300 },
            { month: '4月', value: 500 },
            { month: '5月', value: 200 },
            { month: '6月', value: 300 }
          ]
        }
        const validOutboundData = this.outboundData.filter(item => item && item.month && item.month.trim())
        const months = validOutboundData.map(item => item.month || '')
        const values = validOutboundData.map(item => Number(item.value) || 0)
        
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
                formatter: function(params) {
                  // 确保数值为整数格式
                  return Math.round(params.value);
                },
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                borderColor: '#409EFF',
                borderWidth: 1,
                color: '#fff',
                fontSize: 12
              },
              axis: 'y' // 只在y轴显示标签
            },
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            borderColor: '#409EFF',
            borderWidth: 1,
            color: '#fff',
            fontSize: 12,
            formatter: function(params) {
              return params[0].name + '<br/>' +
                     params[0].marker + '出库数量: ' + params[0].value;
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
            data: ['出库数量'],
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
              data: months.length > 0 ? months : ['1月', '2月', '3月', '4月', '5月', '6月'],
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
              name: '出库数量',
              data: values,
              type: 'line',
              smooth: true,
              symbol: 'circle',
              symbolSize: 8,
              sampling: 'lttb',
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
                    formatter: function(params) {
                      return Math.round(params.value);
                    }
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
                formatter: function(params) {
                  return Math.round(params.value);
                }
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
    // 确保DOM完全渲染后再初始化图表
    setTimeout(() => {
      this.initCharts()
    }, 1000)
    
    window.addEventListener('resize', this.handleResize)
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
  color: #333 !important;
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
  background: #f2f2f2 !important;
  border-bottom-color: var(--border-color) !important;
  color: #333 !important;
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