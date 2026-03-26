<template>
  <div class="production-container">
    <div class="production-header">
      <h2>生产计划管理</h2>
      <div class="header-actions">
        <el-button type="danger" @click="refreshData">
          <el-icon><Refresh /></el-icon>
          <span>刷新数据</span>
        </el-button>
        <el-button type="success" @click="exportTable">
          <el-icon><Download /></el-icon>
          <span>导出表格</span>
        </el-button>
        <el-button type="warning" @click="openImportDialog">
          <el-icon><Upload /></el-icon>
          <span>导入表格</span>
        </el-button>
        <el-button type="primary" @click="openTemplateManager">
          <el-icon><Setting /></el-icon>
          <span>模板管理</span>
        </el-button>
      </div>
    </div>

    <div class="color-control">
      <div class="template-options">
        <div class="template-left">
          <h4>模板切换</h4>
          <el-radio-group v-model="currentTemplate" @change="changeTemplate">
            <el-radio-button value="f116">F116</el-radio-button>
            <el-radio-button value="erDai">二代</el-radio-button>
            <el-radio-button value="728">728</el-radio-button>
            <el-radio-button value="danKu">单裤</el-radio-button>
            <el-radio-button value="g2WaKu">G2蛙裤</el-radio-button>
            <el-radio-button value="BDU">BDU</el-radio-button>
            <el-radio-button value="IX7danKu">IX7单裤</el-radio-button>
          </el-radio-group>
        </div>
        <div class="template-center">
          <h4>目标工厂</h4>
          <el-select
            v-model="selectedFactory"
            placeholder="选择工厂"
            style="width: 180px;"
            clearable
          >
            <el-option
              v-for="factory in factories"
              :key="factory.id"
              :label="factory.name"
              :value="factory.id"
            />
          </el-select>
        </div>
        <div class="template-right">
          <h4>计划日期</h4>
          <div class="date-input-group">
            <el-date-picker
              v-model="planDate"
              type="date"
              placeholder="选择日期"
              style="width: 150px;"
              value-format="YYYY-MM-DD"
            />
            <el-button type="primary" @click="saveCurrentPlan">
              <el-icon><Plus /></el-icon>
              <span>添加计划</span>
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <div class="table-container" @click="closeAllInputs">
      <table class="production-table" @click.stop>
        <thead>
          <!-- 工厂信息行 -->
          <tr v-if="selectedFactory" class="factory-row">
            <th :colspan="2 + models.length * 2" class="factory-header">
              <span class="factory-label">目标工厂：</span>
              <span class="factory-name">{{ getFactoryName(selectedFactory) }}</span>
            </th>
          </tr>
          <!-- 型号行 -->
          <tr>
            <th rowspan="2">尺码</th>
            <th rowspan="2">耗料/套</th>
            <th v-for="(model, index) in models" :key="index" colspan="2">
              <div class="model-header" @click.stop>
                <span class="model-name">{{ model.name }}</span>
                <el-select
                  v-model="model.color"
                  placeholder="选择颜色"
                  style="width: 120px; margin-left: 10px;"
                  @change="updateIncomingMaterials"
                >
                  <el-option
                    v-for="color in availableColors"
                    :key="color"
                    :label="color"
                    :value="color"
                  />
                </el-select>
              </div>
            </th>
          </tr>
          <!-- 表头行 -->
          <tr>
            <th v-for="(model, index) in models" :key="index">耗料/米</th>
            <th v-for="(model, index) in models" :key="index + 'qty'">数量/套</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(size, sizeIndex) in sizes" :key="sizeIndex">
            <td>{{ size.name }}</td>
            <td @click="size.editingMaterial = true">
              <template v-if="size.editingMaterial">
                <el-input
                  v-model="size.materialPerSet"
                  type="number"
                  step="0.001"
                  @change="calculateRow; size.editingMaterial = false"
                  @blur="size.editingMaterial = false"
                  @keyup.enter="size.editingMaterial = false"
                  class="material-input"
                  autofocus
                />
              </template>
              <template v-else>
                <div class="editable-cell">{{ Number(size.materialPerSet).toFixed(3) }}</div>
              </template>
            </td>
            <template v-for="(model, modelIndex) in models" :key="modelIndex">
              <td>
                <div class="total-meters">{{ calculateTotalMeters(sizeIndex, modelIndex) }}</div>
              </td>
              <td @click="handleQuantityCellClick(size, modelIndex)">
                <template v-if="size.editingQuantities && size.editingQuantities[modelIndex]">
                  <el-input
                    :ref="(el) => setQuantityInputRef(el, sizeIndex, modelIndex)"
                    v-model="size.quantities[modelIndex]"
                    type="number"
                    @change="calculateRow; size.editingQuantities[modelIndex] = false"
                    @blur="size.editingQuantities[modelIndex] = false"
                    @keyup.enter="size.editingQuantities[modelIndex] = false"
                    class="quantity-input"
                  />
                </template>
                <template v-else>
                  <div class="editable-cell">{{ size.quantities[modelIndex] }}</div>
                </template>
              </td>
            </template>
          </tr>
          <!-- 总计行 -->
          <tr class="total-row">
            <td>总计</td>
            <td id="totalMaterials">来料: {{ incomingMaterials }} | 用料: {{ totalMaterials }} | 余料: {{ remainingMaterials }}</td>
            <template v-for="(model, modelIndex) in models" :key="modelIndex">
              <td>{{ calculateTotalMetersForModel(modelIndex) }}</td>
              <td>{{ calculateTotalQuantityForModel(modelIndex) }}</td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 表格缩放控制 -->
    <div class="zoom-controls">
      <el-button @click="adjustTableZoom(-0.1)" size="small">-</el-button>
      <div id="zoomLevelText" class="zoom-level">{{ zoomLevel }}%</div>
      <el-button @click="adjustTableZoom(0.1)" size="small">+</el-button>
      <el-button @click="resetTableZoom" size="small">重置</el-button>
    </div>

    <!-- 生产计划列表 -->
    <div class="production-plans-section">
      <div class="section-header">
        <h3>生产计划列表</h3>
      </div>
      
      <!-- 按日期分组显示 -->
      <div v-for="(dateGroup, date) in groupedPlans" :key="date" class="date-group">
        <div class="date-header">{{ date }}</div>
        
        <!-- 按类型分组 -->
        <div v-for="(typeGroup, type) in dateGroup" :key="type" class="type-group">
          <div class="type-header">{{ type }}</div>
          
          <!-- 计划卡片列表 -->
          <div class="plans-container">
            <div v-for="plan in typeGroup" :key="plan.id" class="plan-card" @click="loadPlan(plan)">
              <el-tooltip placement="top" effect="dark">
                <template #content>
                  <div style="white-space: pre-wrap;">{{ getPlanSizeDetails(plan) }}</div>
                </template>
                <div class="plan-content">
                  <div class="plan-header">
                    <div class="plan-title">{{ plan.name }}</div>
                    <div class="plan-actions" @click.stop>
                      <el-button type="primary" size="small" @click="loadPlan(plan)">加载</el-button>
                      <el-button type="danger" size="small" @click="deletePlanById(plan.id)">删除</el-button>
                    </div>
                  </div>
                  <div class="plan-summary">
                    <span class="plan-models">型号: {{ (plan.models_data || plan.models || []).length }} 个</span>
                    <span class="plan-total">总计: {{ calculatePlanTotalQuantity(plan) }} 套</span>
                  </div>
                </div>
              </el-tooltip>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 空状态 -->
      <el-empty v-if="productionPlans.length === 0" description="暂无生产计划" />
    </div>
  </div>

  <!-- 模板管理模态窗口 -->
  <el-dialog
    v-model="templateManagerVisible"
    title="模板管理"
    width="800px"
  >
    <div class="template-manager-content">
      <!-- 模板列表 -->
      <div class="template-list-section">
        <div class="section-header">
          <h3>模板列表</h3>
          <el-button type="primary" @click="addTemplate">
            <el-icon><Plus /></el-icon>
            <span>新建模板</span>
          </el-button>
        </div>
        <el-table :data="templates" style="width: 100%">
          <el-table-column prop="name" label="模板名称" width="180" />
          <el-table-column prop="description" label="描述" />
          <el-table-column prop="createdAt" label="创建时间" width="180" />
          <el-table-column label="操作" width="200">
            <template #default="{ row }">
              <el-button size="small" @click="editTemplate(row)">
                <el-icon><Edit /></el-icon>
                <span>编辑</span>
              </el-button>
              <el-button size="small" type="danger" @click="deleteTemplate(row.id)">
                <el-icon><Delete /></el-icon>
                <span>删除</span>
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 耗料数据管理 -->
      <div class="material-section">
        <div class="section-header">
          <h3>耗料数据管理</h3>
          <div style="display: flex; align-items: center; gap: 10px;">
            <el-select v-model="selectedMaterialTemplate" placeholder="选择模板" style="width: 150px;">
              <el-option
                v-for="template in templates"
                :key="template.id"
                :label="template.name"
                :value="template.name"
              />
            </el-select>
            <el-button size="small" @click="importMaterials">
              <el-icon><Upload /></el-icon>
              <span>导入</span>
            </el-button>
            <el-button size="small" @click="exportMaterials">
              <el-icon><Download /></el-icon>
              <span>导出</span>
            </el-button>
          </div>
        </div>
        <el-table :data="filteredMaterials" style="width: 100%" height="400">
          <el-table-column prop="size" label="尺码" min-width="100" />
          <el-table-column label="耗料/套" min-width="150">
            <template #default="{ row }">
              <el-input-number
                v-model="row.materialPerSet"
                :precision="3"
                :step="0.001"
                :min="0"
                size="small"
                style="width: 120px"
                @change="updateMaterialData(row)"
              />
            </template>
          </el-table-column>
          <el-table-column prop="template" label="所属模板" min-width="120" />
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="danger" @click="deleteMaterial(row.id)">
                <el-icon><Delete /></el-icon>
                <span>删除</span>
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-button type="primary" @click="addMaterial" style="margin-top: 10px">
          <el-icon><Plus /></el-icon>
          <span>添加耗料数据</span>
        </el-button>
      </div>
    </div>
  </el-dialog>

  <!-- 模板编辑模态窗口 -->
  <el-dialog
    v-model="templateEditVisible"
    :title="editingTemplate.id ? '编辑模板' : '新建模板'"
    width="500px"
  >
    <el-form :model="editingTemplate" label-width="80px">
      <el-form-item label="模板名称">
        <el-input v-model="editingTemplate.name" placeholder="请输入模板名称" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input
          v-model="editingTemplate.description"
          type="textarea"
          placeholder="请输入模板描述"
          :rows="3"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="templateEditVisible = false">取消</el-button>
        <el-button type="primary" @click="saveTemplate">保存</el-button>
      </span>
    </template>
  </el-dialog>

  <!-- 耗料编辑模态窗口 -->
  <el-dialog
    v-model="materialEditVisible"
    :title="editingMaterial.id ? '编辑耗料' : '添加耗料'"
    width="500px"
  >
    <el-form :model="editingMaterial" label-width="80px">
      <el-form-item label="尺码">
        <el-input v-model="editingMaterial.size" placeholder="请输入尺码" />
      </el-form-item>
      <el-form-item label="耗料/套">
        <el-input
          v-model="editingMaterial.materialPerSet"
          type="number"
          placeholder="请输入耗料量"
          step="0.01"
        />
      </el-form-item>
      <el-form-item label="所属模板">
        <el-select v-model="editingMaterial.template" placeholder="选择模板">
          <el-option
            v-for="template in templates"
            :key="template.id"
            :label="template.name"
            :value="template.name"
          />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="materialEditVisible = false">取消</el-button>
        <el-button type="primary" @click="saveMaterial">保存</el-button>
      </span>
    </template>
  </el-dialog>

  <!-- 导入组件 -->
  <ImportComponent
    v-model:visible="importDialogVisible"
    title="导入生产计划数据"
    :validate="validateImportData"
    @success="handleImportSuccess"
  />
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Download, Plus, Delete, Edit, Setting, Upload } from '@element-plus/icons-vue'
import * as ExcelJS from 'exceljs'
import axios from 'axios'
import { useAuthStore } from '../stores/auth.js'
import ImportComponent from './ImportComponent.vue'

const authStore = useAuthStore()

// 模板数据 - 严格按照用户提供的数据
const templatesData = {
  f116: {
    'XS': 2.820,
    'S': 2.930,
    'M': 3.040,
    'L': 3.150,
    'XL': 3.270,
    'XXL': 3.380,
    'XXXL': 3.490,
    'XXXXL': 3.640
  },
  erDai: {
    'XS': 3.07,
    'S': 3.175,
    'M': 3.29,
    'L': 3.405,
    'XL': 3.525,
    'XXL': 3.65,
    'XXXL': 3.78,
    'XXXXL': 0
  },
  728: {
    'XS': 2.875,
    'S': 2.96,
    'M': 3.07,
    'L': 3.17,
    'XL': 3.28,
    'XXL': 3.43,
    'XXXL': 3.55,
    'XXXXL': 0
  },
  danKu: {
    'XS': 1.66,
    'S': 1.71,
    'M': 1.765,
    'L': 1.820,
    'XL': 1.880,
    'XXL': 1.935,
    'XXXL': 2,
    'XXXXL': 0
  },
  g2WaKu: {
    'XS': 0,
    'S': 1.85,
    'M': 1.91,
    'L': 1.975,
    'XL': 2.04,
    'XXL': 2.115,
    'XXXL': 2.175,
    'XXXXL': 0
  },
  BDU: {
    'XS': 3.22,
    'S': 3.33,
    'M': 3.45,
    'L': 3.57,
    'XL': 3.69,
    'XXL': 3.8,
    'XXXL': 3.93,
    'XXXXL': 4.07
  },
  IX7danKu: {
    'XS': 1.55,
    'S': 1.61,
    'M': 1.67,
    'L': 1.73,
    'XL': 1.79,
    'XXL': 1.86,
    'XXXL': 1.92,
    'XXXXL': 0
  }
}

// 响应式数据
const currentTemplate = ref('f116')
const models = ref([{ name: 'F116', color: '' }])
const sizes = ref([])
const zoomLevel = ref(100)
const factories = ref([])
const selectedFactory = ref(null)
const availableColors = ref(['黑色', '卡其', '军绿', '丛林', '三沙', '藏蓝', '数码丛林', '数码海洋', '数码沙漠', '黑蟒纹', '绿蟒纹', '绿废墟', '灰废墟', '小绿人', '黑cp', 'cp', '绿cp'])
const selectedMaterialTemplate = ref('')

// 模板管理相关状态
const templateManagerVisible = ref(false)
const templateEditVisible = ref(false)
const materialEditVisible = ref(false)

// 导入相关状态
const importDialogVisible = ref(false)

// 模板数据
const templates = ref([
  {
    id: 1,
    name: 'F116',
    description: 'F116 型号模板',
    createdAt: '2026-03-21 10:00:00'
  },
  {
    id: 2,
    name: '二代',
    description: '二代型号模板',
    createdAt: '2026-03-21 10:00:00'
  },
  {
    id: 3,
    name: '728',
    description: '728 型号模板',
    createdAt: '2026-03-21 10:00:00'
  },
  {
    id: 4,
    name: '单裤',
    description: '单裤型号模板',
    createdAt: '2026-03-21 10:00:00'
  },
  {
    id: 5,
    name: 'G2蛙裤',
    description: 'G2蛙裤型号模板',
    createdAt: '2026-03-21 10:00:00'
  },
  {
    id: 6,
    name: 'BDU',
    description: 'BDU 型号模板',
    createdAt: '2026-03-21 10:00:00'
  },
  {
    id: 7,
    name: 'IX7单裤',
    description: 'IX7单裤型号模板',
    createdAt: '2026-03-21 10:00:00'
  }
])

// 耗料数据
const materials = ref([
  { id: 1, size: 'S', materialPerSet: 2.5, template: 'F116' },
  { id: 2, size: 'M', materialPerSet: 2.8, template: 'F116' },
  { id: 3, size: 'L', materialPerSet: 3.1, template: 'F116' },
  { id: 4, size: 'XL', materialPerSet: 3.4, template: 'F116' },
  { id: 5, size: 'XXL', materialPerSet: 3.7, template: 'F116' },
  { id: 6, size: 'S', materialPerSet: 2.3, template: '二代' },
  { id: 7, size: 'M', materialPerSet: 2.6, template: '二代' },
  { id: 8, size: 'L', materialPerSet: 2.9, template: '二代' },
  { id: 9, size: 'XL', materialPerSet: 3.2, template: '二代' },
  { id: 10, size: 'XXL', materialPerSet: 3.5, template: '二代' }
])

// 编辑中的模板
const editingTemplate = ref({
  id: null,
  name: '',
  description: ''
})

// 编辑中的耗料
const editingMaterial = ref({
  id: null,
  size: '',
  materialPerSet: '',
  template: ''
})

// 计算属性
const totalMaterials = computed(() => {
  let total = 0
  sizes.value.forEach(size => {
    models.value.forEach((model, modelIndex) => {
      // 确保转换为数字
      const qty = Number(size.quantities[modelIndex]) || 0
      const materialPerSet = Number(size.materialPerSet) || 0
      total += materialPerSet * qty
    })
  })
  return total.toFixed(2)
})

// 筛选后的耗料数据
const filteredMaterials = computed(() => {
  // 当未选择模板时，默认选择第一个模板
  if (!selectedMaterialTemplate.value && templates.value.length > 0) {
    selectedMaterialTemplate.value = templates.value[0].name
  }
  
  // 当选择了模板时，返回该模板的耗料数据
  const templateKey = Object.keys(templateTypeNames).find(key => templateTypeNames[key] === selectedMaterialTemplate.value) || selectedMaterialTemplate.value
  const templateData = templatesData[templateKey]
  if (templateData) {
    const templateMaterials = []
    Object.entries(templateData).forEach(([size, materialPerSet]) => {
      templateMaterials.push({
        id: `${templateKey}-${size}`,
        size: size,
        materialPerSet: materialPerSet,
        template: selectedMaterialTemplate.value
      })
    })
    return templateMaterials
  }
  return []
})

// 更新耗料数据
const updateMaterialData = (row) => {
  const templateKey = Object.keys(templateTypeNames).find(key => templateTypeNames[key] === row.template) || row.template
  if (templatesData[templateKey]) {
    templatesData[templateKey][row.size] = parseFloat(row.materialPerSet)
    ElMessage.success('耗料数据已更新')
  }
}

// 布料库存数据
const clothInventory = ref({})

// 加载染色布库存
const loadClothInventory = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:9876/api/materials/')
    const materials = response.data
    const inventory = {}
    materials.forEach(material => {
      if (material.type === '面料') {
        inventory[material.name] = material.quantity || 0
      }
    })
    clothInventory.value = inventory
  } catch (error) {
    console.error('获取染色布库存失败:', error)
    // 处理认证错误
    if (error.response?.status === 401) {
      const refreshResult = await authStore.refreshToken()
      if (refreshResult.success) {
        // 刷新令牌成功后重试
        try {
          const response = await axios.get('http://127.0.0.1:9876/api/materials/')
          const materials = response.data
          const inventory = {}
          materials.forEach(material => {
            if (material.type === '面料') {
              inventory[material.name] = material.quantity || 0
            }
          })
          clothInventory.value = inventory
        } catch (retryError) {
          console.error('重试获取染色布库存失败:', retryError)
        }
      }
    }
  }
}

// 来料数量（根据所选布料的库存）
const incomingMaterials = computed(() => {
  if (models.value.length === 0 || !models.value[0].color) {
    return '0.00'
  }
  const clothName = models.value[0].color
  const inventory = parseFloat(clothInventory.value[clothName] || 0)
  return inventory.toFixed(2)
})

// 余料数量
const remainingMaterials = computed(() => {
  const incoming = parseFloat(incomingMaterials.value) || 0
  const used = parseFloat(totalMaterials.value) || 0
  return (incoming - used).toFixed(2)
})

// 更新来料数量
const updateIncomingMaterials = () => {
  loadClothInventory()
}

// 更新布料库存
const updateClothInventory = async (clothName, quantity) => {
  try {
    // 查找对应的染色布材料
    const response = await axios.get('http://127.0.0.1:9876/api/materials/')
    const materials = response.data
    const clothMaterial = materials.find(m => m.type === '面料' && m.name === clothName)
    
    if (clothMaterial) {
      // 更新库存，确保quantity是数字类型
      // 确保supplier和factory字段是正确的格式
      const updatedMaterial = {
        ...clothMaterial,
        quantity: Number(quantity) || 0,
        supplier: clothMaterial.supplier?.id || clothMaterial.supplier || null,
        factory: clothMaterial.factory?.id || clothMaterial.factory || null
      }
      await axios.put(`http://127.0.0.1:9876/api/materials/${clothMaterial.id}/`, updatedMaterial)
      // 重新加载库存
      loadClothInventory()
      ElMessage.success('染色布库存已更新')
    }
  } catch (error) {
    console.error('更新染色布库存失败:', error)
    console.error('错误详情:', error.response?.data)
    // 处理认证错误
    if (error.response?.status === 401) {
      const refreshResult = await authStore.refreshToken()
      if (refreshResult.success) {
        // 刷新令牌成功后重试
        try {
          const response = await axios.get('http://127.0.0.1:9876/api/materials/')
          const materials = response.data
          const clothMaterial = materials.find(m => m.type === '面料' && m.name === clothName)
          
          if (clothMaterial) {
            // 更新库存，确保quantity是数字类型
            // 确保supplier和factory字段是正确的格式
            const updatedMaterial = {
              ...clothMaterial,
              quantity: Number(quantity) || 0,
              supplier: clothMaterial.supplier?.id || clothMaterial.supplier || null,
              factory: clothMaterial.factory?.id || clothMaterial.factory || null
            }
            await axios.put(`http://127.0.0.1:9876/api/materials/${clothMaterial.id}/`, updatedMaterial)
            // 重新加载库存
            loadClothInventory()
            ElMessage.success('染色布库存已更新')
          }
          return
        } catch (retryError) {
          console.error('重试更新染色布库存失败:', retryError)
          ElMessage.error('更新染色布库存失败')
        }
      }
    }
    ElMessage.error('更新染色布库存失败')
  }
}

// 方法
const calculateRow = () => {
  // 计算逻辑已在模板中通过计算属性实现
}

const calculateTotalMeters = (sizeIndex, modelIndex) => {
  const size = sizes.value[sizeIndex]
  if (!size) return '0.00'
  if (!size.quantities) size.quantities = []
  while (size.quantities.length <= modelIndex) {
    size.quantities.push(0)
  }
  // 确保转换为数字
  const quantity = Number(size.quantities[modelIndex]) || 0
  const materialPerSet = Number(size.materialPerSet) || 0
  const total = materialPerSet * quantity
  return total.toFixed(2)
}

const calculateTotalMetersForModel = (modelIndex) => {
  let total = 0
  sizes.value.forEach(size => {
    if (!size.quantities) size.quantities = []
    while (size.quantities.length <= modelIndex) {
      size.quantities.push(0)
    }
    // 确保转换为数字
    const quantity = Number(size.quantities[modelIndex]) || 0
    const materialPerSet = Number(size.materialPerSet) || 0
    total += materialPerSet * quantity
  })
  return total.toFixed(2)
}

const calculateTotalQuantityForModel = (modelIndex) => {
  let total = 0
  sizes.value.forEach(size => {
    if (!size.quantities) size.quantities = []
    while (size.quantities.length <= modelIndex) {
      size.quantities.push(0)
    }
    // 确保转换为数字
    const qty = Number(size.quantities[modelIndex]) || 0
    total += qty
  })
  return total
}



const changeTemplate = () => {
  const templateData = templatesData[currentTemplate.value]
  if (templateData) {
    // 将对象格式转换为数组格式
    const newSizes = []
    for (const [name, materialPerSet] of Object.entries(templateData)) {
      newSizes.push({
        name: name,
        materialPerSet: materialPerSet,
        quantities: models.value.map(() => 0)
      })
    }
    sizes.value = newSizes
    
    // 更新型号名称为模板名称
    const templateName = templateTypeNames[currentTemplate.value] || currentTemplate.value
    if (models.value.length > 0) {
      models.value[0].name = templateName
    } else {
      models.value.push({ name: templateName, color: '' })
    }
    
    // 从材料溯源获取颜色选项
    fetchAvailableColors()
  }
}

// 从材料溯源获取可用染色布
const fetchAvailableColors = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:9876/api/materials/')
    const materials = response.data
    // 提取所有染色布（面料）类型的名称
    const cloths = new Set()
    materials.forEach(material => {
      if (material.type === '面料') {
        if (material.name) {
          cloths.add(material.name)
        }
      }
    })
    availableColors.value = Array.from(cloths)
  } catch (error) {
    console.error('获取染色布选项失败:', error)
    // 处理认证错误
    if (error.response?.status === 401) {
      const refreshResult = await authStore.refreshToken()
      if (refreshResult.success) {
        // 刷新令牌成功后重试
        try {
          const response = await axios.get('http://127.0.0.1:9876/api/materials/')
          const materials = response.data
          // 提取所有染色布（面料）类型的名称
          const cloths = new Set()
          materials.forEach(material => {
            if (material.type === '面料') {
              if (material.name) {
                cloths.add(material.name)
              }
            }
          })
          availableColors.value = Array.from(cloths)
          return
        } catch (retryError) {
          console.error('重试获取染色布选项失败:', retryError)
          // 如果重试失败，使用默认布料选项
          availableColors.value = ['80/20布']
        }
      } else {
        // 如果刷新令牌失败，使用默认布料选项
        availableColors.value = ['80/20布']
      }
    } else {
      // 如果其他错误，使用默认布料选项
      availableColors.value = ['80/20布']
    }
  }
}

const refreshData = () => {
  // 重新加载当前模板数据
  changeTemplate()
  // 显示刷新成功提示
  ElMessage.success('数据已刷新')
}

const exportTable = async () => {
  try {
    // 创建工作簿
    const workbook = new ExcelJS.Workbook()
    const worksheet = workbook.addWorksheet('生产计划')
    
    // 设置列宽
    const columnCount = 2 + models.value.length * 2
    const columns = []
    
    // 添加基础列
    columns.push({ header: '尺码', key: 'size', width: 10 })
    columns.push({ header: '耗料/套', key: 'materialPerSet', width: 12 })
    
    // 添加型号列
    models.value.forEach(model => {
      columns.push({ header: '耗料/米', key: `material_${model.name}`, width: 15 })
      columns.push({ header: '数量/套', key: `quantity_${model.name}`, width: 15 })
    })
    
    worksheet.columns = columns
    
    // 设置第一行的值（表头）
    const headerRow = worksheet.getRow(1)
    headerRow.getCell(1).value = '尺码'
    headerRow.getCell(2).value = '耗料/套'
    
    let currentCol = 3
    models.value.forEach(model => {
      headerRow.getCell(currentCol).value = `${model.name} - 耗料/米`
      headerRow.getCell(currentCol + 1).value = `${model.name} - 数量/套`
      currentCol += 2
    })
    
    // 添加数据行，从第二行开始
    let rowIndex = 2
    sizes.value.forEach(size => {
      const row = worksheet.getRow(rowIndex)
      row.getCell(1).value = size.name
      row.getCell(2).value = size.materialPerSet
      
      currentCol = 3
      models.value.forEach((model, index) => {
        row.getCell(currentCol).value = calculateTotalMeters(sizes.value.indexOf(size), index)
        row.getCell(currentCol + 1).value = size.quantities[index]
        currentCol += 2
      })
      
      rowIndex++
    })
    
    // 添加总计行
    const totalRow = worksheet.getRow(rowIndex)
    totalRow.getCell(1).value = '总计'
    totalRow.getCell(2).value = `来料: ${incomingMaterials.value} | 用料: ${totalMaterials.value} | 余料: ${remainingMaterials.value}`
    totalRow.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FFFF00' }
    }
    
    currentCol = 3
    models.value.forEach((model, index) => {
      totalRow.getCell(currentCol).value = calculateTotalMetersForModel(index)
      totalRow.getCell(currentCol + 1).value = calculateTotalQuantityForModel(index)
      totalRow.getCell(currentCol).fill = {
        type: 'pattern',
        pattern: 'solid',
        fgColor: { argb: 'FFFF00' }
      }
      totalRow.getCell(currentCol + 1).fill = {
        type: 'pattern',
        pattern: 'solid',
        fgColor: { argb: 'FFFF00' }
      }
      currentCol += 2
    })
    
    // 生成文件
    const buffer = await workbook.xlsx.writeBuffer()
    const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    
    // 下载文件
    const link = document.createElement('a')
    link.href = url
    link.download = `生产计划_${new Date().toISOString().split('T')[0]}.xlsx`
    link.click()
    
    // 清理
    URL.revokeObjectURL(url)
    
    ElMessage.success('表格导出成功')
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('表格导出失败')
  }
}

const adjustTableZoom = (delta) => {
  zoomLevel.value = Math.max(50, Math.min(200, zoomLevel.value + delta * 100))
  const table = document.querySelector('.production-table')
  if (table) {
    table.style.transform = `scale(${zoomLevel.value / 100})`
    table.style.transformOrigin = 'top left'
  }
}

const resetTableZoom = () => {
  zoomLevel.value = 100
  const table = document.querySelector('.production-table')
  if (table) {
    table.style.transform = 'scale(1)'
  }
}

const closeAllInputs = () => {
  sizes.value.forEach(size => {
    size.editingMaterial = false
    if (size.editingQuantities) {
      Object.keys(size.editingQuantities).forEach(key => {
        size.editingQuantities[key] = false
      })
    }
  })
}

// 输入框引用存储
const quantityInputRefs = ref({})

// 设置输入框引用
const setQuantityInputRef = (el, sizeIndex, modelIndex) => {
  if (el) {
    const key = `${sizeIndex}-${modelIndex}`
    quantityInputRefs.value[key] = el
    // 自动聚焦
    nextTick(() => {
      const input = el.$el?.querySelector('input')
      if (input) {
        input.focus()
      }
    })
  }
}

// 处理数量单元格点击 - 点击时清除默认值0
const handleQuantityCellClick = (size, modelIndex) => {
  // 初始化编辑状态
  size.editingQuantities = size.editingQuantities || {}
  size.editingQuantities[modelIndex] = true

  // 如果当前值为0，则清空，方便用户直接输入
  if (size.quantities[modelIndex] === 0 || size.quantities[modelIndex] === '0') {
    size.quantities[modelIndex] = ''
  }
}

// 生产计划相关数据
const productionPlans = ref([])
const planDate = ref(new Date().toISOString().split('T')[0])
const planName = ref('')

// 模板类型名称映射
const templateTypeNames = {
  f116: 'F116',
  erDai: '二代',
  728: '728',
  danKu: '单裤',
  g2WaKu: 'G2蛙裤',
  BDU: 'BDU',
  IX7danKu: 'IX7单裤'
}

// 获取工厂列表
const fetchFactories = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:9876/api/factories/')
    factories.value = response.data
  } catch (error) {
    console.error('Error fetching factories:', error)
    // 处理认证错误
    if (error.response?.status === 401) {
      const refreshResult = await authStore.refreshToken()
      if (refreshResult.success) {
        // 刷新令牌成功后重试
        const response = await axios.get('http://127.0.0.1:9876/api/factories/')
        factories.value = response.data
        return
      }
    }
    ElMessage.error('获取工厂列表失败')
  }
}

// 获取工厂名称
const getFactoryName = (factoryId) => {
  const factory = factories.value.find(f => f.id === factoryId)
  return factory ? factory.name : '未知工厂'
}

// 按日期和类型分组计算属性
const groupedPlans = computed(() => {
  const grouped = {}
  productionPlans.value.forEach(plan => {
    const date = plan.date
    const type = plan.plan_type || plan.type
    if (!grouped[date]) {
      grouped[date] = {}
    }
    if (!grouped[date][type]) {
      grouped[date][type] = []
    }
    grouped[date][type].push(plan)
  })
  return grouped
})

// 计算计划总数量
const calculatePlanTotalQuantity = (plan) => {
  let total = 0
  const sizes = plan.sizes_data || plan.sizes || []
  sizes.forEach(size => {
    const quantities = size.quantities || []
    quantities.forEach(qty => {
      total += Number(qty) || 0
    })
  })
  return total
}

// 获取计划的尺码详情，用于悬停提示
const getPlanSizeDetails = (plan) => {
  const sizes = plan.sizes_data || plan.sizes || []
  if (sizes.length === 0) {
    return '暂无尺码数据'
  }
  
  const details = sizes.map(size => {
    const quantity = size.quantities && size.quantities.length > 0 ? size.quantities[0] : 0
    return `${size.name}: ${quantity}`
  }).join('\n')
  
  return details
}

// 保存当前表格为计划
const saveCurrentPlan = async () => {
  if (!planDate.value) {
    ElMessage.warning('请选择日期')
    return
  }
  if (models.value.length === 0) {
    ElMessage.warning('请至少添加一个型号')
    return
  }
  if (!models.value[0].color) {
    ElMessage.warning('请选择布料')
    return
  }
  
  // 获取当前模板类型名称
  const typeName = templateTypeNames[currentTemplate.value] || currentTemplate.value
  // 生成计划名称，格式为：F116 军绿 xxx布
  const model = models.value[0]
  const clothName = model.color || '未知布料'
  const modelName = model.name || typeName
  const planName = `${modelName} ${clothName}`
  
  const planData = {
    date: planDate.value,
    plan_type: typeName,
    name: planName,
    factory_id: selectedFactory.value,
    template: currentTemplate.value,
    models_data: JSON.parse(JSON.stringify(models.value)),
    sizes_data: JSON.parse(JSON.stringify(sizes.value))
  }
  
  try {
    const response = await axios.post('http://127.0.0.1:9876/api/production-plan-details/', planData)
    productionPlans.value.push(response.data)
    
    // 更新布料库存，将余料返回库存
    const clothName = models.value[0].color
    const remainingQty = parseFloat(remainingMaterials.value)
    if (clothName && !isNaN(remainingQty)) {
      await updateClothInventory(clothName, remainingQty)
    }
    
    ElMessage.success('计划保存成功')
  } catch (error) {
    console.error('保存计划失败:', error)
    // 处理认证错误
    if (error.response?.status === 401) {
      const refreshResult = await authStore.refreshToken()
      if (refreshResult.success) {
        // 刷新令牌成功后重试
        const response = await axios.post('http://127.0.0.1:9876/api/production-plan-details/', planData)
        productionPlans.value.push(response.data)
        
        // 更新布料库存，将余料返回库存
        const clothName = models.value[0].color
        const remainingQty = parseFloat(remainingMaterials.value)
        if (clothName && !isNaN(remainingQty)) {
          await updateClothInventory(clothName, remainingQty)
        }
        
        ElMessage.success('计划保存成功')
        return
      }
    }
    ElMessage.error('保存计划失败：' + (error.response?.data?.detail || error.message))
  }
}

// 加载计划到表格
const loadPlan = (plan) => {
  models.value = JSON.parse(JSON.stringify(plan.models_data || plan.models || []))
  sizes.value = JSON.parse(JSON.stringify(plan.sizes_data || plan.sizes || []))
  currentTemplate.value = plan.template
  planDate.value = plan.date
  selectedFactory.value = plan.factory?.id || plan.factory_id || null
  ElMessage.success('计划已加载')
}

// 删除计划
const deletePlanById = async (id) => {
  ElMessageBox.confirm('确定要删除这个生产计划吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await axios.delete(`http://127.0.0.1:9876/api/production-plan-details/${id}/`)
      const index = productionPlans.value.findIndex(p => p.id === id)
      if (index > -1) {
        productionPlans.value.splice(index, 1)
        ElMessage.success('删除成功')
      }
    } catch (error) {
      console.error('删除计划失败:', error)
      // 处理认证错误
      if (error.response?.status === 401) {
        const refreshResult = await authStore.refreshToken()
        if (refreshResult.success) {
          // 刷新令牌成功后重试
          await axios.delete(`http://127.0.0.1:9876/api/production-plan-details/${id}/`)
          const index = productionPlans.value.findIndex(p => p.id === id)
          if (index > -1) {
            productionPlans.value.splice(index, 1)
            ElMessage.success('删除成功')
          }
          return
        }
      }
      ElMessage.error('删除失败：' + (error.response?.data?.detail || error.message))
    }
  }).catch(() => {})  
}

// 从后端加载生产计划列表
const fetchProductionPlans = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:9876/api/production-plan-details/')
    productionPlans.value = response.data
  } catch (error) {
    console.error('获取生产计划列表失败:', error)
    // 处理认证错误
    if (error.response?.status === 401) {
      const refreshResult = await authStore.refreshToken()
      if (refreshResult.success) {
        // 刷新令牌成功后重试
        const response = await axios.get('http://127.0.0.1:9876/api/production-plan-details/')
        productionPlans.value = response.data
        return
      }
    }
    ElMessage.error('获取生产计划列表失败')
  }
}

// 打开模板管理器
const openTemplateManager = () => {
  templateManagerVisible.value = true
}

// 打开导入对话框
const openImportDialog = () => {
  importDialogVisible.value = true
}

// 验证导入数据
const validateImportData = (item, rowIndex) => {
  if (!item.尺码) {
    return '尺码不能为空'
  }
  if (!item.耗料/套) {
    return '耗料/套不能为空'
  }
  if (isNaN(item.耗料/套)) {
    return '耗料/套必须是数字'
  }
  return null
}

// 处理导入成功
const handleImportSuccess = (data) => {
  // 处理导入的数据
  console.log('导入的数据:', data)
  
  // 这里可以根据需要处理导入的数据
  // 例如更新生产计划数据
  
  ElMessage.success('生产计划数据导入成功')
}

// 添加模板
const addTemplate = () => {
  editingTemplate.value = {
    id: null,
    name: '',
    description: ''
  }
  templateEditVisible.value = true
}

// 编辑模板
const editTemplate = (template) => {
  editingTemplate.value = { ...template }
  templateEditVisible.value = true
}

// 保存模板
const saveTemplate = () => {
  if (!editingTemplate.value.name) {
    ElMessage.error('请输入模板名称')
    return
  }

  if (editingTemplate.value.id) {
    // 编辑现有模板
    const index = templates.value.findIndex(t => t.id === editingTemplate.value.id)
    if (index !== -1) {
      templates.value[index] = { ...editingTemplate.value }
      ElMessage.success('模板更新成功')
    }
  } else {
    // 添加新模板
    const newTemplate = {
      id: Date.now(),
      ...editingTemplate.value,
      createdAt: new Date().toLocaleString()
    }
    templates.value.push(newTemplate)
    ElMessage.success('模板创建成功')
  }

  templateEditVisible.value = false
}

// 删除模板
const deleteTemplate = (templateId) => {
  ElMessageBox.confirm(
    '确定要删除这个模板吗？',
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    const templateToDelete = templates.value.find(t => t.id === templateId)
    templates.value = templates.value.filter(t => t.id !== templateId)
    // 同时删除关联的耗料数据
    if (templateToDelete) {
      materials.value = materials.value.filter(m => m.template !== templateToDelete.name)
    }
    ElMessage.success('模板删除成功')
  }).catch(() => {
    // 取消删除
  })
}

// 添加耗料数据
const addMaterial = () => {
  editingMaterial.value = {
    id: null,
    size: '',
    materialPerSet: '',
    template: templates.value[0]?.name || ''
  }
  materialEditVisible.value = true
}

// 编辑耗料数据
const editMaterial = (material) => {
  editingMaterial.value = { ...material }
  materialEditVisible.value = true
}

// 保存耗料数据
const saveMaterial = () => {
  if (!editingMaterial.value.size) {
    ElMessage.error('请输入尺码')
    return
  }
  if (!editingMaterial.value.materialPerSet) {
    ElMessage.error('请输入耗料量')
    return
  }
  if (!editingMaterial.value.template) {
    ElMessage.error('请选择所属模板')
    return
  }

  // 找到对应的模板键
  const templateKey = Object.keys(templateTypeNames).find(key => templateTypeNames[key] === editingMaterial.value.template) || editingMaterial.value.template
  
  // 确保模板数据存在
  if (!templatesData[templateKey]) {
    templatesData[templateKey] = {}
  }
  
  // 更新模板数据
  templatesData[templateKey][editingMaterial.value.size] = parseFloat(editingMaterial.value.materialPerSet)
  
  ElMessage.success('耗料数据更新成功')
  materialEditVisible.value = false
}

// 删除耗料数据
const deleteMaterial = (materialId) => {
  ElMessageBox.confirm(
    '确定要删除这个耗料数据吗？',
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    // 从materialId中提取模板键和尺码
    const [templateKey, size] = materialId.split('-')
    if (templatesData[templateKey]) {
      delete templatesData[templateKey][size]
    }
    ElMessage.success('耗料数据删除成功')
  }).catch(() => {
    // 取消删除
  })
}

// 导入耗料数据
const importMaterials = () => {
  ElMessage.info('导入功能开发中')
}

// 导出耗料数据
const exportMaterials = () => {
  ElMessage.info('导出功能开发中')
}

// 生命周期
onMounted(() => {
  // 初始化数据
  changeTemplate()
  // 获取工厂列表
  fetchFactories()
  // 获取生产计划列表
  fetchProductionPlans()
  // 获取可用布料
  fetchAvailableColors()
  // 加载布料库存
  loadClothInventory()
})
</script>

<style scoped>
.production-container {
  padding: 20px;
  width: 100%;
  box-sizing: border-box;
}

.production-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eaeaea;
}

.production-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: bold;
  color: #333;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.input-group {
  margin: 15px 0;
  display: flex;
  align-items: center;
}

.color-control {
  margin: 15px 0;
  padding: 15px;
  background-color: #e3f2fd;
  border-radius: 5px;
}

.color-control h4 {
  margin-top: 0;
  margin-bottom: 10px;
}

.template-options {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
}

.template-left {
  flex: 1;
}

.template-center {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.template-center h4 {
  margin-top: 0;
  margin-bottom: 10px;
}

.template-right {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.template-right h4 {
  margin-top: 0;
  margin-bottom: 10px;
}

.date-input-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 工厂信息行样式 */
.factory-row {
  background-color: #e3f2fd;
}

.factory-header {
  background-color: #1976d2 !important;
  color: white !important;
  font-size: 16px;
  padding: 10px;
}

.factory-label {
  font-weight: bold;
  margin-right: 5px;
}

.factory-name {
  font-weight: normal;
}

.table-container {
  overflow-x: auto;
  margin: 10px 0;
  border-radius: 4px;
  min-height: 400px;
}

.production-table {
  width: 100%;
  border-collapse: collapse;
  transition: transform 0.3s ease;
}

.production-table th,
.production-table td {
  border: 1px solid #ddd;
  padding: 12px;
  text-align: center;
}

.production-table th {
  background-color: #4CAF50;
  color: white;
  font-weight: bold;
  position: sticky;
  top: 0;
  z-index: 10;
}

.production-table tr:nth-child(even) {
  background-color: #f9f9f9;
}

.total-row {
  background-color: #ffd700 !important;
  font-weight: bold;
  color: #333;
}

.total-meters {
  text-align: center;
}

.material-input,
.quantity-input {
  width: 100%;
  text-align: center;
}

.model-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.model-name {
  font-weight: bold;
  font-size: 14px;
}

.model-name-input {
  text-align: center;
}

.editable-cell {
  padding: 4px 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.editable-cell:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

body.dark-mode .editable-cell:hover {
  background-color: rgba(255, 255, 255, 0.05);
}

.zoom-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 20px 0;
  padding: 10px;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #dee2e6;
  gap: 10px;
}

.zoom-level {
  font-weight: bold;
  min-width: 50px;
  text-align: center;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .production-container {
    padding: 10px;
  }
  
  .production-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .header-actions {
    width: 100%;
    justify-content: space-between;
  }
  
  .input-group {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .input-group input {
    width: 100%;
  }
  
  .template-options {
    flex-direction: column;
  }
  
  .table-container {
    font-size: 12px;
  }
  
  .production-table th,
  .production-table td {
    padding: 8px 4px;
  }
}

/* 生产计划列表样式 */
.production-plans-section {
  margin-top: 30px;
  padding: 20px;
  background-color: #f5f5f5;
  border-radius: 8px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h3 {
  margin: 0;
  font-size: 20px;
  color: #333;
}

.plans-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

.plan-card {
  background-color: white;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.plan-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.plan-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.plan-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.plan-color {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  border: 2px solid #ddd;
}

.plan-color-name {
  font-weight: bold;
  font-size: 16px;
  color: #333;
}

.plan-total {
  font-size: 14px;
  color: #666;
  background-color: #f0f0f0;
  padding: 2px 8px;
  border-radius: 4px;
}

.plan-actions {
  display: flex;
  gap: 8px;
}

.plan-sizes {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.size-item {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  background-color: #f8f8f8;
  border-radius: 4px;
  font-size: 14px;
}

.size-name {
  font-weight: bold;
  color: #555;
}

.size-quantity {
  color: #666;
}

.size-inputs {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.size-input-row {
  display: flex;
  align-items: center;
}

/* 计划信息输入区域 */
.plan-info-section {
  margin: 15px 0;
  padding: 15px;
  background-color: #e8f4f8;
  border-radius: 8px;
  border: 1px solid #b8d4e3;
}

.plan-info-section h4 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #2c5f7c;
}

.plan-inputs {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

/* 日期分组样式 */
.date-group {
  margin-bottom: 20px;
}

.date-header {
  font-size: 18px;
  font-weight: bold;
  color: #333;
  padding: 10px 15px;
  background-color: #f0f0f0;
  border-radius: 8px;
  margin-bottom: 15px;
  border-left: 4px solid #409EFF;
}

.type-group {
  margin-left: 20px;
  margin-bottom: 15px;
}

.type-header {
  font-size: 16px;
  font-weight: bold;
  color: #555;
  padding: 8px 12px;
  background-color: #f8f8f8;
  border-radius: 6px;
  margin-bottom: 10px;
  border-left: 3px solid #67C23A;
}

.plan-title {
  font-size: 16px;
  font-weight: bold;
  color: #333;
}

.plan-summary {
  display: flex;
  gap: 15px;
  margin-top: 8px;
  font-size: 14px;
  color: #666;
}

.plan-models {
  background-color: #f0f0f0;
  padding: 2px 8px;
  border-radius: 4px;
}

/* 深色模式 - 使用更高优先级选择器 */
html body.dark-mode .production-container {
  color: #e0e0e0;
}

html body.dark-mode .production-header h2 {
  color: #e0e0e0 !important;
}

html body.dark-mode .production-header {
  border-bottom-color: #444 !important;
}

html body.dark-mode .input-group {
  color: #e0e0e0 !important;
}

html body.dark-mode .input-group label {
  color: #e0e0e0 !important;
}

html body.dark-mode .color-control {
  background-color: #2d2d2d !important;
  border: 1px solid #444 !important;
}

html body.dark-mode .color-control h4 {
  color: #e0e0e0 !important;
}

html body.dark-mode .template-options {
  color: #e0e0e0 !important;
}

html body.dark-mode .production-table th {
  background-color: #4CAF50 !important;
  color: white !important;
}

html body.dark-mode .production-table td {
  border-color: #444 !important;
  color: #e0e0e0 !important;
}

html body.dark-mode .production-table tr:nth-child(even) {
  background-color: #2d2d2d !important;
}

html body.dark-mode .production-table tr:nth-child(odd):not(.total-row) {
  background-color: #1a1a1a !important;
}

html body.dark-mode .total-row {
  background-color: #ffb300 !important;
  color: #111 !important;
}

html body.dark-mode .total-row td {
  color: #111 !important;
}

/* 生产计划列表深色模式 */
html body.dark-mode .production-plans-section {
  background-color: #1a1a1a !important;
}

html body.dark-mode .section-header h3 {
  color: #e0e0e0 !important;
}

html body.dark-mode .plan-card {
  background-color: #2d2d2d !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
}

html body.dark-mode .plan-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5) !important;
}

html body.dark-mode .plan-header {
  border-bottom-color: #444 !important;
}

html body.dark-mode .plan-color {
  border-color: #555 !important;
}

html body.dark-mode .plan-color-name {
  color: #e0e0e0 !important;
}

html body.dark-mode .plan-total {
  color: #aaa !important;
  background-color: #3d3d3d !important;
}

html body.dark-mode .size-item {
  background-color: #3d3d3d !important;
}

html body.dark-mode .size-name {
  color: #ccc !important;
}

html body.dark-mode .size-quantity {
  color: #aaa !important;
}

/* 工厂信息行深色模式 */
html body.dark-mode .factory-row {
  background-color: #1a3a5c !important;
}

html body.dark-mode .factory-header {
  background-color: #1565c0 !important;
  color: white !important;
}

/* 日期分组深色模式 */
html body.dark-mode .date-header {
  color: #e0e0e0 !important;
  background-color: #2d2d2d !important;
  border-left-color: #409EFF !important;
}

html body.dark-mode .type-header {
  color: #ccc !important;
  background-color: #3d3d3d !important;
  border-left-color: #67C23A !important;
}

html body.dark-mode .plan-title {
  color: #e0e0e0 !important;
}

html body.dark-mode .plan-summary {
  color: #aaa !important;
}

html body.dark-mode .plan-models {
  background-color: #3d3d3d !important;
  color: #ccc !important;
}

html body.dark-mode .zoom-controls {
  background-color: #2d2d2d !important;
  border-color: #444 !important;
}

html body.dark-mode .zoom-level {
  color: #e0e0e0 !important;
}

html body.dark-mode .model-header {
  color: #e0e0e0 !important;
}

html body.dark-mode .model-name {
  color: #e0e0e0 !important;
}

html body.dark-mode .model-name-input {
  background-color: #2d2d2d !important;
  border-color: #444 !important;
  color: #e0e0e0 !important;
}

html body.dark-mode .el-input__wrapper {
  background-color: #2d2d2d !important;
  border-color: #444 !important;
  box-shadow: 0 0 0 1px #444 inset !important;
}

html body.dark-mode .el-input__inner {
  color: #e0e0e0 !important;
  background-color: transparent !important;
}

html body.dark-mode .el-button:not(.el-button--primary):not(.el-button--danger) {
  background-color: #2d2d2d !important;
  color: #e0e0e0 !important;
  border-color: #444 !important;
}

html body.dark-mode .el-button:not(.el-button--primary):not(.el-button--danger):hover {
  background-color: #3d3d3d !important;
  border-color: #555 !important;
  color: #fff !important;
}

html body.dark-mode .el-button--primary {
  background-color: #409EFF !important;
  border-color: #409EFF !important;
  color: #fff !important;
}

html body.dark-mode .el-button--primary:hover {
  background-color: #66b1ff !important;
  border-color: #66b1ff !important;
  color: #fff !important;
}

html body.dark-mode .el-button--danger {
  background-color: #f56c6c !important;
  border-color: #f56c6c !important;
  color: #fff !important;
}

html body.dark-mode .el-button--danger:hover {
  background-color: #f78989 !important;
  border-color: #f78989 !important;
  color: #fff !important;
}

/* 针对 scoped 样式，使用深度选择器 */
html body.dark-mode .production-table :deep(tr):nth-child(even) {
  background-color: #2d2d2d !important;
}

html body.dark-mode .production-table :deep(tr):nth-child(odd):not(.total-row) {
  background-color: #1a1a1a !important;
}

/* 模板管理样式 */
.template-manager-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.template-list-section,
.material-section {
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 15px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>