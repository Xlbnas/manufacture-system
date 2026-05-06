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
          <el-radio-group
            v-model="currentTemplate"
            class="template-switch-radios"
            @change="onTemplateChoiceChange"
          >
            <el-radio-button
              v-for="k in TEMPLATE_KEYS"
              :key="k"
              :value="k"
            >
              {{ templateTypeNames[k] }}
            </el-radio-button>
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
          <h4 style="margin-top: 10px;">客户</h4>
          <div class="customer-line">
            <el-select
              v-model="selectedCustomer"
              filterable
              allow-create
              default-first-option
              clearable
              placeholder="选择或输入客户"
              style="width: 180px;"
            >
              <el-option
                v-for="customer in customerOptions"
                :key="customer"
                :label="customer"
                :value="customer"
              />
            </el-select>
            <el-button size="small" @click="openCustomerManager">客户管理</el-button>
          </div>
          <div class="accessories-row">
            <span class="acc-label">辅料已到齐</span>
            <el-switch v-model="saveFormAccessoriesDelivered" />
          </div>
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
                <div
                  class="fabric-picker-trigger fabric-select-wide"
                  @click.stop="openDyedFabricDrawer(index, model)"
                >
                  <span class="fabric-picker-text">{{ formatFabricPickLabel(model) }}</span>
                  <el-icon class="fabric-picker-caret"><ArrowDown /></el-icon>
                </div>
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
        <div class="plan-filter-bar">
          <el-select v-model="filterCustomer" clearable placeholder="筛选客户" style="width: 140px">
            <el-option v-for="customer in customerOptions" :key="customer" :label="customer" :value="customer" />
          </el-select>
          <el-select v-model="groupMode" style="width: 140px">
            <el-option label="按日期+类型" value="date_type" />
            <el-option label="按日期" value="date" />
            <el-option label="按客户" value="customer" />
          </el-select>
          <el-select v-model="sortMode" style="width: 140px">
            <el-option label="时间倒序" value="date_desc" />
            <el-option label="时间正序" value="date_asc" />
            <el-option label="客户 A-Z" value="customer_asc" />
            <el-option label="客户 Z-A" value="customer_desc" />
          </el-select>
          <el-button type="success" @click="exportFilteredPlans">导出筛选计划</el-button>
        </div>
      </div>
      
      <!-- 按日期分组显示 -->
      <div v-for="(dateGroup, date) in groupedPlans" :key="date" class="date-group">
        <div class="date-header">{{ date }}</div>
        
        <!-- 按类型分组 -->
        <div v-for="(typeGroup, type) in dateGroup" :key="type" class="type-group">
          <div class="type-header">{{ type }}</div>
          
          <!-- 计划卡片列表 -->
          <div class="plans-container">
            <div v-for="plan in typeGroup" :key="plan.id" class="plan-card">
              <el-tooltip placement="top" effect="dark">
                <template #content>
                  <div style="white-space: pre-wrap;">{{ getPlanSizeDetails(plan) }}</div>
                </template>
                <div class="plan-content">
                  <div class="plan-header">
                    <div class="plan-title">{{ plan.name }}</div>
                    <div class="plan-actions" @click.stop>
                      <el-button type="primary" size="small" @click="loadPlan(plan)">加载</el-button>
                      <el-button type="success" size="small" @click="openCompleteProductionDialog(plan)">完工入库</el-button>
                      <el-button type="danger" size="small" @click="deletePlanById(plan.id)">删除</el-button>
                    </div>
                  </div>
                  <div class="plan-summary">
                    <span class="plan-models">型号: {{ (plan.models_data || plan.models || []).length }} 个</span>
                    <span class="plan-total">总计: {{ calculatePlanTotalQuantity(plan) }} 套</span>
                    <span class="plan-customer">客户: {{ plan.customer || '未设置' }}</span>
                    <span class="plan-acc">
                      辅料
                      <el-switch
                        :model-value="!!plan.accessories_delivered"
                        size="small"
                        style="margin-left: 4px"
                        @change="(v) => patchPlanAccessories(plan, v)"
                      />
                    </span>
                  </div>
                </div>
              </el-tooltip>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 空状态 -->
      <el-empty v-if="displayedPlans.length === 0" description="暂无生产计划" />
    </div>
  </div>

  <el-dialog
    v-model="completeProductionVisible"
    title="完工入库"
    width="640px"
    destroy-on-close
    @closed="onCompleteProductionDialogClosed"
  >
    <div v-if="completePlanForCompletion">
      <p class="complete-hint">
        {{ completePlanForCompletion.name }} · {{ completePlanForCompletion.date }} ·
        成品按当前排产的模板键入账；入库仓与<strong>本排产已选目标工厂</strong>一致，由系统自动解析，无需再选。
      </p>
      <div class="inbound-warehouse-banner">
        <div v-if="completeInboundUi.status === 'ok'" class="inbound-ok">
          <span class="lbl">入库仓库</span>
          <strong>{{ completeInboundUi.warehouseName }}</strong>
          <span class="sub">（按目标工厂自动解析，无需再选）</span>
        </div>
        <el-alert v-else-if="completeInboundUi.status === 'no_factory'" type="warning" :closable="false" show-icon>
          {{ completeInboundUi.message }}
        </el-alert>
        <el-alert v-else-if="completeInboundUi.status === 'no_warehouse'" type="warning" :closable="false" show-icon>
          {{ completeInboundUi.message }}
        </el-alert>
      </div>
      <el-table :data="completeProductionRows" size="small" max-height="380" border>
        <el-table-column prop="size_name" label="尺码" width="72" />
        <el-table-column prop="modelLabel" label="型号列" width="96" />
        <el-table-column label="计划" width="72">
          <template #default="{ row }">{{ row.planned }}</template>
        </el-table-column>
        <el-table-column label="已累计完工" width="96">
          <template #default="{ row }">{{ row.done_accum }}</template>
        </el-table-column>
        <el-table-column label="本批入库" min-width="120">
          <template #default="{ row }">
            <el-input v-model.number="row.qty_this_batch" type="number" min="0" placeholder="0" />
          </template>
        </el-table-column>
      </el-table>
    </div>
    <template #footer>
      <el-button @click="completeProductionVisible = false">取消</el-button>
      <el-button
        type="primary"
        :disabled="!completePlanForCompletion || completeInboundUi.status !== 'ok'"
        @click="submitCompleteProduction"
      >
        确认入库
      </el-button>
    </template>
  </el-dialog>

  <el-drawer
    v-model="dyedFabricDrawerVisible"
    title="选择染色布"
    direction="rtl"
    size="440px"
    destroy-on-close
    @closed="dyedFabricDrawerTargetModel = null"
  >
    <el-input
      v-model="dyedFabricDrawerFilter"
      clearable
      placeholder="筛选：颜色 · 名称 · 备注 · 库存"
      size="small"
      class="fabric-drawer-filter"
    />
    <div v-if="dyedFabricOptions.length === 0" class="fabric-drawer-empty">暂无染色布库存，请到「材料溯源」维护。</div>
    <ul v-else class="fabric-drawer-list">
      <li
        v-for="opt in filteredDyedFabricOptions"
        :key="opt.id"
        class="fabric-drawer-item"
        :class="{
          active: dyedFabricDrawerTargetModel?.dyed_material_id === opt.id,
        }"
        @click="pickDyedFabricFromDrawer(opt)"
      >
        <div class="fabric-drawer-item-main">{{ opt.label }}</div>
      </li>
    </ul>
    <p v-if="filteredDyedFabricOptions.length === 0 && dyedFabricOptions.length" class="fabric-drawer-empty">无匹配项，尝试清空筛选</p>
    <template #footer>
      <el-button text type="danger" @click="clearDyedFabricInDrawer">清空本列选布</el-button>
      <el-button type="primary" @click="dyedFabricDrawerVisible = false">完成</el-button>
    </template>
  </el-drawer>

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
  <el-dialog v-model="customerManagerVisible" title="客户管理" width="520px">
    <div class="customer-manager">
      <div class="customer-add">
        <el-input v-model="newCustomerName" placeholder="输入客户名称" @keyup.enter="addCustomer" />
        <el-button type="primary" @click="addCustomer">添加</el-button>
      </div>
      <el-empty v-if="customerOptions.length === 0" description="暂无客户" />
      <el-table v-else :data="customerOptions.map((name) => ({ name }))" size="small" style="margin-top: 10px;">
        <el-table-column prop="name" label="客户名称" />
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-button type="danger" size="small" @click="removeCustomer(row.name)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Download, Plus, Delete, Edit, Setting, Upload, ArrowDown } from '@element-plus/icons-vue'
import * as ExcelJS from 'exceljs'
import api from '../utils/axios'
import { useRoute } from 'vue-router'
import ImportComponent from './ImportComponent.vue'
import { TEMPLATE_TYPE_LABELS as templateTypeNames, TEMPLATE_KEYS } from '../constants/productionTemplates.js'

const route = useRoute()

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
const models = ref([{ name: 'F116', color: '', dyed_material_id: null }])
const sizes = ref([])
/** 与模板 radio 无关：整页只有一份 models/sizes；radio 只决定保存计划时的 template 字段 */
const PRODUCTION_FORM_STORAGE_KEY = 'manufacture_production_form_draft_v2'
const LEGACY_TEMPLATE_DRAFTS_KEY = 'manufacture_production_template_drafts_v1'

const persistProductionFormToStorage = () => {
  try {
    sessionStorage.setItem(
      PRODUCTION_FORM_STORAGE_KEY,
      JSON.stringify({
        v: 2,
        currentTemplate: currentTemplate.value,
        models: models.value,
        sizes: sizes.value,
      })
    )
  } catch (e) {
    console.warn('persist production form', e)
  }
}

const tryMigrateLegacyV1Drafts = () => {
  try {
    const raw = sessionStorage.getItem(LEGACY_TEMPLATE_DRAFTS_KEY)
    if (!raw) return false
    const data = JSON.parse(raw)
    const ct = data?.currentTemplate
    const d = ct && data.drafts ? data.drafts[ct] : null
    if (!d || !Array.isArray(d.models) || !Array.isArray(d.sizes)) return false
    models.value = JSON.parse(JSON.stringify(d.models))
    models.value.forEach((m) => {
      if (m.dyed_material_id === undefined) m.dyed_material_id = null
    })
    sizes.value = JSON.parse(JSON.stringify(d.sizes))
    normalizeSizesToModelColumns()
    if (TEMPLATE_KEYS.includes(ct)) currentTemplate.value = ct
    sessionStorage.removeItem(LEGACY_TEMPLATE_DRAFTS_KEY)
    persistProductionFormToStorage()
    return true
  } catch {
    return false
  }
}

const loadProductionFormFromStorage = () => {
  try {
    const raw = sessionStorage.getItem(PRODUCTION_FORM_STORAGE_KEY)
    if (!raw) return tryMigrateLegacyV1Drafts()
    const data = JSON.parse(raw)
    if (!data || data.v !== 2) return tryMigrateLegacyV1Drafts()
    if (Array.isArray(data.models) && Array.isArray(data.sizes)) {
      models.value = JSON.parse(JSON.stringify(data.models))
      models.value.forEach((m) => {
        if (m.dyed_material_id === undefined) m.dyed_material_id = null
      })
      sizes.value = JSON.parse(JSON.stringify(data.sizes))
      normalizeSizesToModelColumns()
    }
    if (data.currentTemplate && TEMPLATE_KEYS.includes(data.currentTemplate)) {
      currentTemplate.value = data.currentTemplate
    }
    return true
  } catch {
    return tryMigrateLegacyV1Drafts()
  }
}

const clearProductionFormStorage = () => {
  try {
    sessionStorage.removeItem(PRODUCTION_FORM_STORAGE_KEY)
    sessionStorage.removeItem(LEGACY_TEMPLATE_DRAFTS_KEY)
  } catch (_) {}
}

let persistDraftTimer = null
const schedulePersistProductionForm = () => {
  if (persistDraftTimer) clearTimeout(persistDraftTimer)
  persistDraftTimer = setTimeout(() => {
    persistDraftTimer = null
    persistProductionFormToStorage()
  }, 400)
}

watch([models, sizes, currentTemplate], () => schedulePersistProductionForm(), { deep: true })
const zoomLevel = ref(100)
const factories = ref([])
const selectedFactory = ref(null)
/** 可选染色布库存行：下拉展示「颜色，名称，备注，数量+单位」 */
const dyedFabricOptions = ref([])
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

const extractMaterials = (payload) => {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.results)) return payload.results
  return []
}

const formatDyedFabricOptionLabel = (material) => {
  const color = (material.color || '').trim() || '—'
  const name = (material.name || '').trim() || '—'
  const unit = material.unit || '米'
  const qtyNum = Number(material.quantity)
  const qty = Number.isFinite(qtyNum) ? qtyNum.toFixed(2) : '0.00'
  const remark = (material.remark || '').trim()
  const tail = `${qty}${unit}`
  return remark ? `${color}，${name}，${remark}，${tail}` : `${color}，${name}，${tail}`
}

const normalizeModelsFabricIds = () => {
  for (const m of models.value) {
    if (
      m.dyed_material_id != null &&
      m.dyed_material_id !== '' &&
      !dyedFabricOptions.value.some((o) => o.id === m.dyed_material_id)
    ) {
      m.dyed_material_id = null
    }
    if (!m.dyed_material_id && (m.color || '').trim()) {
      const matches = dyedFabricOptions.value.filter((o) => (o.color || '').trim() === (m.color || '').trim())
      if (matches.length === 1) m.dyed_material_id = matches[0].id
    }
    if (m.dyed_material_id) {
      const opt = dyedFabricOptions.value.find((o) => o.id === m.dyed_material_id)
      if (opt) m.color = opt.color
    }
  }
}

const syncModelsWithFabricStock = () => {
  if (!dyedFabricOptions.value.length) return
  let adjusted = false
  for (const m of models.value) {
    if (m.dyed_material_id && !dyedFabricOptions.value.some((o) => o.id === m.dyed_material_id)) {
      m.dyed_material_id = null
      adjusted = true
    }
    if (m.dyed_material_id) continue
    const c = (m.color || '').trim()
    if (!c) continue
    const byColor = dyedFabricOptions.value.filter((o) => (o.color || '').trim() === c)
    if (!byColor.length) {
      m.color = ''
      adjusted = true
    } else if (byColor.length === 1) {
      m.dyed_material_id = byColor[0].id
      m.color = byColor[0].color
      adjusted = true
    }
  }
  if (adjusted) {
    ElMessage.warning('已按当前染色布库存校正所选布料')
  }
}

const refreshDyedFabricOptions = async () => {
  try {
    const response = await api.get('materials/')
    const materials = extractMaterials(response.data)
    const opts = []
    materials.forEach((material) => {
      if (material.type !== 'dyed_fabric') return
      const quantity = Number(material.quantity) || 0
      if (quantity <= 0) return
      opts.push({
        id: material.id,
        color: (material.color || '').trim(),
        name: material.name || '',
        quantity,
        unit: material.unit || '米',
        remark: (material.remark || '').trim(),
        label: formatDyedFabricOptionLabel(material),
      })
    })
    opts.sort((a, b) => a.label.localeCompare(b.label, 'zh-CN'))
    dyedFabricOptions.value = opts
    normalizeModelsFabricIds()
    syncModelsWithFabricStock()
  } catch (error) {
    console.error('获取染色布库存失败:', error)
    dyedFabricOptions.value = []
  }
}

const onDyedFabricChange = (model) => {
  const opt = dyedFabricOptions.value.find((o) => o.id === model.dyed_material_id)
  if (opt) {
    model.color = opt.color
  } else {
    model.color = ''
  }
}

// 来料数量：优先按所选库存行 id；旧数据仅颜色时按同色汇总
const incomingMaterials = computed(() => {
  if (!models.value.length) return '0.00'
  const m = models.value[0]
  if (m.dyed_material_id) {
    const opt = dyedFabricOptions.value.find((o) => o.id === m.dyed_material_id)
    if (opt) return Number(opt.quantity).toFixed(2)
  }
  const clothColor = (m.color || '').trim()
  if (!clothColor) return '0.00'
  let sum = 0
  dyedFabricOptions.value.forEach((o) => {
    if ((o.color || '').trim() === clothColor) sum += Number(o.quantity) || 0
  })
  return sum.toFixed(2)
})

// 余料数量
const remainingMaterials = computed(() => {
  const incoming = parseFloat(incomingMaterials.value) || 0
  const used = parseFloat(totalMaterials.value) || 0
  return (incoming - used).toFixed(2)
})

// 更新来料数量
const updateIncomingMaterials = () => {
  void refreshDyedFabricOptions()
}

// 更新布料库存（优先按物料 id，兼容旧数据仅颜色）
const updateClothInventory = async (materialId, colorFallback, quantity) => {
  try {
    const response = await api.get('materials/')
    const materials = extractMaterials(response.data)
    let clothMaterial
    if (materialId != null && materialId !== '') {
      clothMaterial = materials.find((m) => m.id === materialId)
    }
    if (!clothMaterial && colorFallback) {
      clothMaterial = materials.find((m) => m.type === 'dyed_fabric' && m.color === colorFallback)
    }

    if (clothMaterial) {
      await api.patch(`materials/${clothMaterial.id}/`, {
        quantity: Number(quantity) || 0,
      })
      await refreshDyedFabricOptions()
      ElMessage.success('染色布库存已更新')
    }
  } catch (error) {
    console.error('更新染色布库存失败:', error)
    console.error('错误详情:', error.response?.data)
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

const normalizeSizesToModelColumns = () => {
  const colCount = Math.max(1, models.value.length)
  for (const row of sizes.value) {
    if (!row.quantities) row.quantities = []
    while (row.quantities.length < colCount) row.quantities.push(0)
    if (row.quantities.length > colCount) row.quantities.length = colCount
  }
}

/**
 * 切换模板 radio 时：保留各尺码数量、染色布等已填数据；
 * 仅把表头首型号名称、各尺码「耗料/套」对齐到当前 templatesData（与系统原模板耗料表一致）。
 */
const syncFormWithTemplateSelection = (templateKey) => {
  const td = templatesData[templateKey]
  if (!td) return
  const label = templateTypeNames[templateKey] || templateKey
  if (models.value.length > 0) {
    models.value[0].name = label
  }
  const modelCount = Math.max(1, models.value.length)
  const seen = new Set(sizes.value.map((r) => r.name))
  for (const row of sizes.value) {
    if (Object.prototype.hasOwnProperty.call(td, row.name)) {
      row.materialPerSet = td[row.name]
    }
    if (!row.quantities) row.quantities = []
    while (row.quantities.length < modelCount) row.quantities.push(0)
    if (row.quantities.length > modelCount) row.quantities.length = modelCount
  }
  for (const [name, mps] of Object.entries(td)) {
    if (seen.has(name)) continue
    sizes.value.push({
      name,
      materialPerSet: mps,
      quantities: Array.from({ length: modelCount }, () => 0),
      editingMaterial: false,
      editingQuantities: {},
    })
    seen.add(name)
  }
}

/** 将当前模板重置为耗料表默认行 + 数量清零（不改变型号列数习惯） */
const applyDefaultTemplateForm = (templateKey) => {
  const templateData = templatesData[templateKey]
  if (!templateData) return
  const modelCount = Math.max(1, models.value.length)
  const newSizes = []
  for (const [name, materialPerSet] of Object.entries(templateData)) {
    newSizes.push({
      name,
      materialPerSet,
      quantities: Array.from({ length: modelCount }, () => 0),
    })
  }
  sizes.value = newSizes
  const templateName = templateTypeNames[templateKey] || templateKey
  if (models.value.length > 0) {
    models.value[0].name = templateName
  } else {
    models.value.push({ name: templateName, color: '', dyed_material_id: null })
  }
  void refreshDyedFabricOptions()
}

/** 切换模板：保留数量/布料等；表头型号名与耗料/套随当前模板更新 */
const onTemplateChoiceChange = () => {
  syncFormWithTemplateSelection(currentTemplate.value)
  void refreshDyedFabricOptions()
  persistProductionFormToStorage()
}

const refreshData = () => {
  clearProductionFormStorage()
  applyDefaultTemplateForm(currentTemplate.value)
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

const buildPlanWorksheet = (workbook, plan) => {
  const safeSheetName = `${plan.date || '无日期'}-${plan.name || '计划'}`.slice(0, 31)
  const worksheet = workbook.addWorksheet(safeSheetName)
  const modelsData = plan.models_data || plan.models || []
  const sizesData = plan.sizes_data || plan.sizes || []
  const columns = [
    { header: '尺码', key: 'size', width: 10 },
    { header: '耗料/套', key: 'materialPerSet', width: 12 },
  ]
  modelsData.forEach((model) => {
    columns.push({ header: `${model.name} - 耗料/米`, key: `material_${model.name}`, width: 16 })
    columns.push({ header: `${model.name} - 数量/套`, key: `quantity_${model.name}`, width: 12 })
  })
  worksheet.columns = columns
  worksheet.getRow(1).font = { bold: true }

  let rowIndex = 2
  sizesData.forEach((size) => {
    const row = worksheet.getRow(rowIndex)
    row.getCell(1).value = size.name || ''
    row.getCell(2).value = Number(size.materialPerSet) || 0
    let currentCol = 3
    modelsData.forEach((_, modelIndex) => {
      const qty = Number((size.quantities || [])[modelIndex]) || 0
      const materialPerSet = Number(size.materialPerSet) || 0
      row.getCell(currentCol).value = Number((materialPerSet * qty).toFixed(2))
      row.getCell(currentCol + 1).value = qty
      currentCol += 2
    })
    rowIndex++
  })

  const total = calculatePlanTotalQuantity(plan)
  worksheet.getRow(rowIndex).getCell(1).value = '总计'
  worksheet.getRow(rowIndex).getCell(2).value = `${total} 套`
  worksheet.getRow(rowIndex).font = { bold: true }
  worksheet.getCell('A1').note = `客户: ${plan.customer || '未设置'}`
}

const exportFilteredPlans = async () => {
  if (displayedPlans.value.length === 0) {
    ElMessage.warning('当前筛选条件下没有可导出的计划')
    return
  }
  try {
    const workbook = new ExcelJS.Workbook()
    displayedPlans.value.forEach((plan) => buildPlanWorksheet(workbook, plan))
    const summary = workbook.addWorksheet('导出说明')
    summary.columns = [{ header: '字段', key: 'k', width: 20 }, { header: '值', key: 'v', width: 60 }]
    summary.addRow({ k: '筛选客户', v: filterCustomer.value || '全部' })
    summary.addRow({ k: '分组方式', v: groupMode.value })
    summary.addRow({ k: '排序方式', v: sortMode.value })
    summary.addRow({ k: '导出计划数', v: displayedPlans.value.length })
    const buffer = await workbook.xlsx.writeBuffer()
    const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `生产计划_筛选导出_${new Date().toISOString().split('T')[0]}.xlsx`
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('筛选计划导出成功')
  } catch (e) {
    console.error('筛选计划导出失败', e)
    ElMessage.error('筛选计划导出失败')
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
const selectedCustomer = ref('')
const customerOptions = ref([])
const customerManagerVisible = ref(false)
const newCustomerName = ref('')
const filterCustomer = ref('')
const groupMode = ref('date_type')
const sortMode = ref('date_desc')
const CUSTOMER_STORAGE_KEY = 'production_customers_v1'

/** 仓库节点（完工入库选仓用） */
const warehouseNodes = ref([])
const saveFormAccessoriesDelivered = ref(false)

const dyedFabricDrawerVisible = ref(false)
const dyedFabricDrawerFilter = ref('')
const dyedFabricDrawerTargetModel = ref(null)

const filteredDyedFabricOptions = computed(() => {
  const q = (dyedFabricDrawerFilter.value || '').trim().toLowerCase()
  const opts = dyedFabricOptions.value || []
  if (!q) return opts
  return opts.filter((o) => (o.label || '').toLowerCase().includes(q))
})

const completeProductionVisible = ref(false)
const completePlanForCompletion = ref(null)
const completeProductionRows = ref([])

function planFactoryId(plan) {
  if (!plan) return null
  const nested = plan.factory
  if (nested && typeof nested === 'object' && nested.id != null) return Number(nested.id)
  if (plan.factory_id != null) return Number(plan.factory_id)
  return null
}

function warehouseNodeFactoryId(w) {
  const v = w?.factory
  if (v == null) return null
  return typeof v === 'object' && v.id != null ? Number(v.id) : Number(v)
}

const warehousesForComplete = computed(() => {
  const plan = completePlanForCompletion.value
  const fid = planFactoryId(plan)
  const list = warehouseNodes.value.filter((w) => w.warehouse_type === 'factory' && w.is_active !== false)
  if (fid == null) return list
  return list.filter((w) => warehouseNodeFactoryId(w) === fid)
})

/** 完工入库弹窗：展示系统将要使用的工厂仓（与后端不传 warehouse_id 时的解析一致） */
const completeInboundUi = computed(() => {
  const plan = completePlanForCompletion.value
  if (!plan) {
    return { status: 'idle', message: '' }
  }
  const fid = planFactoryId(plan)
  if (fid == null) {
    return {
      status: 'no_factory',
      message: '当前排产未设置目标工厂，无法自动确定入库仓。请先在排产表单中为该计划选择目标工厂后再完工入库。',
    }
  }
  const w = warehousesForComplete.value[0]
  if (!w) {
    return {
      status: 'no_warehouse',
      message:
        '未找到该目标工厂下已启用的工厂仓。请在「仓库主数据」中维护绑定该工厂的工厂仓，或在「工厂」中新建该工厂（保存时会自动创建对应工厂仓）。',
    }
  }
  return { status: 'ok', warehouseName: w.name }
})

const fetchWarehouseNodesOnly = async () => {
  try {
    const wh = await api.get('/warehouse-nodes/')
    const wl = wh.data
    warehouseNodes.value = Array.isArray(wl) ? wl : wl?.results || []
  } catch (e) {
    console.error('加载仓库失败', e)
  }
}

const buildCompletionRows = (plan) => {
  const sizesPlan = plan.sizes_data || plan.sizes || []
  const modelsData = plan.models_data || plan.models || []
  const comp = plan.size_completion || []
  const rows = []
  sizesPlan.forEach((sz, si) => {
    if (!sz || typeof sz !== 'object') return
    const qs = sz.quantities || []
    const compRow = si < comp.length && comp[si]?.completed_quantities ? comp[si].completed_quantities : []
    ;(qs || []).forEach((pq, mi) => {
      const planned = Number(pq) || 0
      if (planned <= 0) return
      const done = mi < compRow.length ? Number(compRow[mi]) || 0 : 0
      const modelLabel = modelsData[mi]?.name || `型号${mi + 1}`
      rows.push({
        size_name: sz.name,
        model_index: mi,
        modelLabel,
        planned,
        done_accum: done,
        qty_this_batch: 0,
      })
    })
  })
  return rows
}

const onCompleteProductionDialogClosed = () => {
  completePlanForCompletion.value = null
}

const formatFabricPickLabel = (model) => {
  const id = model?.dyed_material_id
  if (id == null) return '点击选择染色布（颜色·名称·库存）'
  const opt = dyedFabricOptions.value.find((o) => o.id === id)
  return opt?.label || `染色布 #${id}`
}

const openDyedFabricDrawer = (_modelIndex, model) => {
  dyedFabricDrawerTargetModel.value = model
  dyedFabricDrawerFilter.value = ''
  dyedFabricDrawerVisible.value = true
}

const pickDyedFabricFromDrawer = (opt) => {
  const model = dyedFabricDrawerTargetModel.value
  if (!model || !opt) return
  model.dyed_material_id = opt.id
  onDyedFabricChange(model)
  updateIncomingMaterials()
  dyedFabricDrawerVisible.value = false
}

const clearDyedFabricInDrawer = () => {
  const model = dyedFabricDrawerTargetModel.value
  if (!model) return
  model.dyed_material_id = null
  onDyedFabricChange(model)
  updateIncomingMaterials()
  dyedFabricDrawerVisible.value = false
}

const openCompleteProductionDialog = async (plan) => {
  await fetchWarehouseNodesOnly()
  completePlanForCompletion.value = plan
  completeProductionRows.value = buildCompletionRows(plan)
  completeProductionVisible.value = true
}

const submitCompleteProduction = async () => {
  const plan = completePlanForCompletion.value
  if (!plan) return
  const lines = []
  for (const row of completeProductionRows.value) {
    const n = Math.floor(Number(row.qty_this_batch) || 0)
    if (n > 0) {
      lines.push({
        size_name: row.size_name,
        model_index: row.model_index,
        qty_this_batch: n,
      })
    }
  }
  if (lines.length === 0) {
    ElMessage.warning('请填写至少一行本批入库数量')
    return
  }
  if (completeInboundUi.value.status !== 'ok') {
    ElMessage.warning(
      completeInboundUi.value.status === 'no_factory'
        ? '请先为排产选择目标工厂'
        : '未找到该工厂的工厂仓，请先维护仓库或工厂后再试'
    )
    return
  }
  const body = { lines }
  try {
    const { data } = await api.post(`production-plan-details/${plan.id}/complete-production/`, body)
    const idx = productionPlans.value.findIndex((p) => p.id === plan.id)
    if (idx !== -1) productionPlans.value[idx] = data
    Object.assign(plan, data)
    ElMessage.success('完工入库已记账')
    completeProductionVisible.value = false
  } catch (e) {
    const msg = e?.response?.data?.error || e?.response?.data?.detail || e?.message
    ElMessage.error(msg || JSON.stringify(e?.response?.data || {}))
  }
}

const patchPlanAccessories = async (plan, val) => {
  try {
    const { data } = await api.patch(`production-plan-details/${plan.id}/`, {
      accessories_delivered: val,
    })
    const idx = productionPlans.value.findIndex((p) => p.id === plan.id)
    if (idx !== -1) {
      productionPlans.value[idx] = { ...productionPlans.value[idx], ...data }
    }
    Object.assign(plan, data)
    ElMessage.success('辅料状态已更新')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || e?.response?.data || e?.message || '更新失败')
  }
}

// 获取工厂列表
const fetchFactories = async () => {
  try {
    const response = await api.get('factories/')
    factories.value = response.data
  } catch (error) {
    console.error('Error fetching factories:', error)
    ElMessage.error('获取工厂列表失败')
  }
}

// 获取工厂名称
const getFactoryName = (factoryId) => {
  const factory = factories.value.find(f => f.id === factoryId)
  return factory ? factory.name : '未知工厂'
}

const persistCustomers = () => {
  try {
    localStorage.setItem(CUSTOMER_STORAGE_KEY, JSON.stringify(customerOptions.value))
  } catch (e) {
    console.warn('保存客户列表失败', e)
  }
}

const loadCustomers = () => {
  try {
    const raw = localStorage.getItem(CUSTOMER_STORAGE_KEY)
    if (!raw) return
    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed)) {
      customerOptions.value = parsed.filter(Boolean)
    }
  } catch (e) {
    console.warn('读取客户列表失败', e)
  }
}

const addCustomerToOptions = (name) => {
  const normalized = (name || '').trim()
  if (!normalized) return
  if (!customerOptions.value.includes(normalized)) {
    customerOptions.value.push(normalized)
    persistCustomers()
  }
}

const openCustomerManager = () => {
  customerManagerVisible.value = true
}

const addCustomer = () => {
  const name = (newCustomerName.value || '').trim()
  if (!name) return
  addCustomerToOptions(name)
  selectedCustomer.value = name
  newCustomerName.value = ''
  ElMessage.success('客户已添加')
}

const removeCustomer = (name) => {
  ElMessageBox.confirm(`确定删除客户「${name}」？`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    customerOptions.value = customerOptions.value.filter(c => c !== name)
    if (selectedCustomer.value === name) selectedCustomer.value = ''
    if (filterCustomer.value === name) filterCustomer.value = ''
    persistCustomers()
    ElMessage.success('客户已删除')
  }).catch(() => {})
}

// 按日期和类型分组计算属性
const displayedPlans = computed(() => {
  let rows = [...productionPlans.value]
  if (filterCustomer.value) {
    rows = rows.filter((p) => (p.customer || '') === filterCustomer.value)
  }
  rows.sort((a, b) => {
    const ad = a.date || ''
    const bd = b.date || ''
    const ac = (a.customer || '').toLowerCase()
    const bc = (b.customer || '').toLowerCase()
    switch (sortMode.value) {
      case 'date_asc':
        return ad.localeCompare(bd)
      case 'customer_asc':
        return ac.localeCompare(bc) || ad.localeCompare(bd)
      case 'customer_desc':
        return bc.localeCompare(ac) || bd.localeCompare(ad)
      case 'date_desc':
      default:
        return bd.localeCompare(ad)
    }
  })
  return rows
})

const groupedPlans = computed(() => {
  const grouped = {}
  displayedPlans.value.forEach(plan => {
    const date = plan.date || '未设置日期'
    const type = plan.plan_type || plan.type || '未分类'
    const customer = plan.customer || '未设置客户'
    let level1 = date
    let level2 = type
    if (groupMode.value === 'date') {
      level1 = date
      level2 = customer
    } else if (groupMode.value === 'customer') {
      level1 = customer
      level2 = type
    }
    if (!grouped[level1]) {
      grouped[level1] = {}
    }
    if (!grouped[level1][level2]) {
      grouped[level1][level2] = []
    }
    grouped[level1][level2].push(plan)
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
  await refreshDyedFabricOptions()
  if (dyedFabricOptions.value.length > 0 && !models.value[0].dyed_material_id) {
    ElMessage.warning('请从下拉框选择具体染色布（含颜色、名称、备注与库存米数）')
    return
  }
  if (!models.value[0].color && !models.value[0].dyed_material_id) {
    ElMessage.warning('请选择布料或先维护染色布库存')
    return
  }

  // 获取当前模板类型名称
  const typeName = templateTypeNames[currentTemplate.value] || currentTemplate.value
  const model = models.value[0]
  const opt = dyedFabricOptions.value.find((o) => o.id === model.dyed_material_id)
  const clothLabel = opt ? opt.label : model.color || '未知布料'
  const modelName = model.name || typeName
  const planName = `${modelName} ${clothLabel}`

  const planData = {
    date: planDate.value,
    plan_type: typeName,
    name: planName.length > 200 ? `${planName.slice(0, 197)}…` : planName,
    customer: (selectedCustomer.value || '').trim(),
    cloth_color: model.color || '',
    cloth_used: Number(totalMaterials.value) || 0,
    cloth_remaining: Number(remainingMaterials.value) || 0,
    factory_id: selectedFactory.value,
    template: currentTemplate.value,
    models_data: JSON.parse(JSON.stringify(models.value)),
    sizes_data: JSON.parse(JSON.stringify(sizes.value)),
    accessories_delivered: saveFormAccessoriesDelivered.value,
  }

  try {
    const response = await api.post('production-plan-details/', planData)
    productionPlans.value.push(response.data)
    addCustomerToOptions(planData.customer)

    const remainingQty = parseFloat(remainingMaterials.value)
    if (!isNaN(remainingQty)) {
      await updateClothInventory(model.dyed_material_id, model.color, remainingQty)
    }

    clearProductionFormStorage()
    applyDefaultTemplateForm(currentTemplate.value)

    ElMessage.success('计划保存成功')
  } catch (error) {
    console.error('保存计划失败:', error)
    ElMessage.error('保存计划失败：' + (error.response?.data?.detail || error.message))
  }
}

// 加载计划到表格
const loadPlan = async (plan) => {
  models.value = JSON.parse(JSON.stringify(plan.models_data || plan.models || []))
  models.value.forEach((m) => {
    if (m.dyed_material_id === undefined) m.dyed_material_id = null
  })
  sizes.value = JSON.parse(JSON.stringify(plan.sizes_data || plan.sizes || []))
  currentTemplate.value = plan.template
  planDate.value = plan.date
  selectedCustomer.value = plan.customer || ''
  selectedFactory.value = plan.factory?.id || plan.factory_id || null
  saveFormAccessoriesDelivered.value = !!plan.accessories_delivered
  await refreshDyedFabricOptions()
  persistProductionFormToStorage()
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
      await api.delete(`production-plan-details/${id}/`)
      const index = productionPlans.value.findIndex(p => p.id === id)
      if (index > -1) {
        productionPlans.value.splice(index, 1)
        ElMessage.success('删除成功')
      }
    } catch (error) {
      console.error('删除计划失败:', error)
      ElMessage.error('删除失败：' + (error.response?.data?.detail || error.message))
    }
  }).catch(() => {})  
}

// 从后端加载生产计划列表
const fetchProductionPlans = async () => {
  try {
    const response = await api.get('production-plan-details/')
    productionPlans.value = response.data
    productionPlans.value.forEach((p) => addCustomerToOptions(p.customer))
    const queryPlanId = Number(route.query.planId)
    if (queryPlanId) {
      const target = productionPlans.value.find((p) => p.id === queryPlanId)
      if (target) loadPlan(target)
    }
  } catch (error) {
    console.error('获取生产计划列表失败:', error)
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
onMounted(async () => {
  loadCustomers()
  const restored = loadProductionFormFromStorage()
  if (!restored) {
    applyDefaultTemplateForm(currentTemplate.value)
  } else {
    syncFormWithTemplateSelection(currentTemplate.value)
    void refreshDyedFabricOptions()
  }
  fetchFactories()
  await fetchWarehouseNodesOnly()
  fetchProductionPlans()
})

onBeforeUnmount(() => {
  if (persistDraftTimer) {
    clearTimeout(persistDraftTimer)
    persistDraftTimer = null
  }
  persistProductionFormToStorage()
})
</script>

<style scoped>
.production-container {
  padding: 20px;
  width: 100%;
  box-sizing: border-box;
}

.fabric-select-wide {
  min-width: 200px;
  max-width: min(100%, 440px);
  width: min(100%, 440px);
  margin-left: 10px;
  vertical-align: middle;
}

.production-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eaeaea;
}

.customer-line {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.plan-filter-bar {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.plan-customer {
  color: #606266;
}

.customer-manager .customer-add {
  display: flex;
  gap: 10px;
  align-items: center;
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
  min-width: 0;
}

/* 模板 radio 换行：独立圆角与间距，避免 Element 中间项去左边框导致第二行错位、白线穿模 */
.template-left .template-switch-radios {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: flex-start;
  width: 100%;
  max-width: 100%;
  overflow: visible;
  row-gap: 8px;
}

.template-left .template-switch-radios :deep(.el-radio-button) {
  margin-right: 0 !important;
  margin-inline-end: 0 !important;
}

.template-left .template-switch-radios :deep(.el-radio-button__inner) {
  border-radius: 4px !important;
  border: 1px solid var(--el-border-color) !important;
  border-left-width: 1px !important;
  box-shadow: none !important;
}

.template-left .template-switch-radios :deep(.el-radio-button:first-child .el-radio-button__inner) {
  border-radius: 4px !important;
}

.template-left .template-switch-radios :deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-radius: 4px !important;
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
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 15px;
  margin-top: 8px;
  font-size: 14px;
  color: #666;
}

.plan-summary .plan-acc {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.accessories-row {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.accessories-row .acc-label {
  font-size: 13px;
  color: #555;
}

html body.dark-mode .fabric-picker-trigger {
  border-color: #4a4f58 !important;
  background-color: #30343d !important;
}

html body.dark-mode .fabric-picker-text {
  color: #e8eaed !important;
}

html body.dark-mode .fabric-drawer-item {
  border-color: #4a4f58 !important;
  background-color: #282c34;
  color: #e8eaed !important;
}

html body.dark-mode .fabric-drawer-item .fabric-drawer-item-main {
  color: #e8eaed !important;
}

html body.dark-mode .fabric-drawer-item:hover {
  background-color: #323842 !important;
}

html body.dark-mode .fabric-drawer-item.active {
  border-color: #79bbff !important;
  background-color: #1a3d5c !important;
  box-shadow: inset 0 0 0 1px rgba(121, 187, 255, 0.35);
  color: #f0f7ff !important;
}

html body.dark-mode .fabric-drawer-item.active .fabric-drawer-item-main {
  color: #f0f7ff !important;
}

.complete-hint {
  font-size: 13px;
  color: #666;
  margin: 0 0 12px;
  line-height: 1.5;
}

.inbound-warehouse-banner {
  margin-bottom: 14px;
}

.inbound-ok {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px;
  font-size: 13px;
  line-height: 1.55;
}

.inbound-ok .lbl {
  color: var(--el-text-color-secondary);
}

.inbound-ok .sub {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.fabric-picker-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 32px;
  padding: 5px 11px;
  border-radius: var(--el-border-radius-base);
  cursor: pointer;
  border: 1px solid var(--el-border-color);
  background: var(--el-fill-color-blank);
  box-sizing: border-box;
  transition: border-color 0.15s;
}

.fabric-picker-trigger:hover {
  border-color: var(--el-color-primary-light-5);
}

.fabric-picker-text {
  flex: 1;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.fabric-picker-caret {
  flex-shrink: 0;
  color: var(--el-text-color-placeholder);
  font-size: 12px;
}

.fabric-drawer-filter {
  margin-bottom: 12px;
}

.fabric-drawer-empty {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  padding: 12px 0;
}

.fabric-drawer-list {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: calc(70vh - 100px);
  overflow-y: auto;
}

.fabric-drawer-item {
  padding: 12px 14px;
  margin-bottom: 8px;
  border-radius: 8px;
  border: 1px solid var(--el-border-color-lighter);
  cursor: pointer;
  font-size: 13px;
  line-height: 1.45;
  transition: border-color 0.15s, background 0.15s;
}

.fabric-drawer-item:hover {
  border-color: var(--el-color-primary-light-5);
}

.fabric-drawer-item.active {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary-dark-2);
}

.fabric-drawer-item.active .fabric-drawer-item-main {
  color: var(--el-color-primary-dark-2);
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

html body.dark-mode .template-left .template-switch-radios :deep(.el-radio-button__inner) {
  border-color: #5a5f6a !important;
  background-color: #2d2d2d !important;
  color: #e0e0e0 !important;
}

html body.dark-mode .template-left .template-switch-radios :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background-color: var(--el-color-primary) !important;
  border-color: var(--el-color-primary) !important;
  color: #fff !important;
  box-shadow: none !important;
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

<style>
/* 生产页暗黑模式全局兜底（旧 scoped 选择器失效时生效） */
.dark-mode .production-container {
  color: #e0e0e0;
}

.dark-mode .production-header {
  border-bottom-color: #444 !important;
}

.dark-mode .production-header h2,
.dark-mode .section-header h3,
.dark-mode .template-left h4,
.dark-mode .template-center h4,
.dark-mode .template-right h4,
.dark-mode .model-name {
  color: #f2f3f5 !important;
}

.dark-mode .color-control {
  background-color: #2d2d2d !important;
  border: 1px solid #444 !important;
}

.dark-mode .production-table th {
  background-color: #4caf50 !important;
  color: #fff !important;
}

.dark-mode .production-table td {
  border-color: #444 !important;
  color: #e0e0e0 !important;
}

.dark-mode .production-table tbody tr:nth-child(even) {
  background-color: #2d2d2d !important;
}

.dark-mode .production-table tbody tr:nth-child(odd):not(.total-row) {
  background-color: #1a1a1a !important;
}

.dark-mode .total-row {
  background-color: #ffb300 !important;
}

.dark-mode .total-row td,
.dark-mode .total-row td * {
  color: #111 !important;
  font-weight: 700 !important;
}

.dark-mode .zoom-controls {
  background-color: #2a2d33 !important;
  border-color: #4a4f58 !important;
}

.dark-mode .zoom-level {
  color: #f2f3f5 !important;
}

.dark-mode .production-plans-section {
  background-color: #1a1a1a !important;
}

.dark-mode .plan-card {
  background-color: #2d2d2d !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
}

.dark-mode .plan-header {
  border-bottom-color: #444 !important;
}

.dark-mode .plan-title,
.dark-mode .date-header,
.dark-mode .type-header,
.dark-mode .plan-summary {
  color: #e0e0e0 !important;
}

.dark-mode .date-header {
  background-color: #2d2d2d !important;
  border-left-color: #409eff !important;
}

.dark-mode .type-header {
  background-color: #3d3d3d !important;
  border-left-color: #67c23a !important;
}

.dark-mode .plan-models,
.dark-mode .plan-total {
  background-color: #3d3d3d !important;
  color: #ccc !important;
}

.dark-mode .production-container .el-select__wrapper {
  background-color: #30343d !important;
  box-shadow: 0 0 0 1px #4a4f58 inset !important;
}

.dark-mode .production-container .el-select__selected-item,
.dark-mode .production-container .el-select__placeholder,
.dark-mode .production-container .el-select__input-wrapper,
.dark-mode .production-container .el-select__input,
.dark-mode .production-container .el-input__inner {
  color: #f2f3f5 !important;
}

.dark-mode .production-container .el-input__wrapper {
  background-color: #30343d !important;
  box-shadow: 0 0 0 1px #4a4f58 inset !important;
}

.dark-mode .production-container .el-radio-button__inner {
  background-color: #353a44 !important;
  border-color: #4a4f58 !important;
  color: #f2f3f5 !important;
}

.dark-mode .production-container .el-radio-button__original-radio:checked + .el-radio-button__inner {
  background-color: #409eff !important;
  border-color: #409eff !important;
  color: #fff !important;
}
</style>