<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../utils/axios'

const materials = ref([])
const suppliers = ref([])
const warehouses = ref([])
const dyeingOrders = ref([])
const dialogVisible = ref(false)
const dyeDialogVisible = ref(false)
const getTodayChinaDate = () => {
  const now = new Date()
  const chinaNow = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Shanghai' }))
  const year = chinaNow.getFullYear()
  const month = `${chinaNow.getMonth() + 1}`.padStart(2, '0')
  const day = `${chinaNow.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

const createDefaultMaterialForm = () => ({
  type: 'raw_fabric',
  name: '',
  color: '',
  quantity: 0,
  unit: '米',
  supplier: null,
  warehouse: null,
  stock_date: getTodayChinaDate(),
})

const form = ref(createDefaultMaterialForm())
const dyeForm = ref({ raw_material_id: null, supplier_id: null, output_name: '', output_color: '', quantity: 0, output_warehouse_id: null })

const typeLabelMap = {
  raw_fabric: '坯布',
  dyed_fabric: '染色布',
  accessory: '辅料',
}

const supplierTypeMap = {
  raw_fabric: '坯布',
  dyed_fabric: '染厂',
  accessory: '辅料',
}

const filteredSuppliers = computed(() => {
  const expectedType = supplierTypeMap[form.value.type]
  return suppliers.value.filter((s) => s.type === expectedType)
})

const formatMaterialType = (row) => typeLabelMap[row.type] || row.type

watch(
  () => form.value.type,
  () => {
    if (!filteredSuppliers.value.some((s) => s.id === form.value.supplier)) {
      form.value.supplier = null
    }
  }
)

const load = async () => {
  const [m, s, w, d] = await Promise.all([
    api.get('/materials/'),
    api.get('/suppliers/'),
    api.get('/warehouse-nodes/'),
    api.get('/dyeing-orders/')
  ])
  materials.value = m.data
  suppliers.value = s.data
  warehouses.value = w.data
  dyeingOrders.value = d.data
}

const createMaterial = async () => {
  await api.post('/materials/', form.value)
  dialogVisible.value = false
  form.value = createDefaultMaterialForm()
  await load()
  ElMessage.success('物料已入库')
}

const openMaterialDialog = () => {
  form.value = createDefaultMaterialForm()
  dialogVisible.value = true
}

const createDyeingOrder = async () => {
  const { data } = await api.post('/dyeing-orders/', dyeForm.value)
  await api.post(`/dyeing-orders/${data.id}/complete/`)
  dyeDialogVisible.value = false
  await load()
  ElMessage.success('染色单已完成并入库')
}

onMounted(load)
</script>

<template>
  <div class="material-management">
    <el-card>
      <template #header>
        <div class="header-line">
          <span>物料与染色流转</span>
          <div>
            <el-button type="primary" @click="openMaterialDialog">物料入库</el-button>
            <el-button type="warning" @click="dyeDialogVisible = true">新建染色单</el-button>
          </div>
        </div>
      </template>
      <el-table :data="materials" size="small">
        <el-table-column prop="type" label="类型" width="110" :formatter="formatMaterialType" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="color" label="颜色" width="120" />
        <el-table-column prop="quantity" label="数量" width="120" />
        <el-table-column prop="unit" label="单位" width="90" />
      </el-table>
    </el-card>

    <el-card style="margin-top: 16px">
      <template #header><span>染色单</span></template>
      <el-table :data="dyeingOrders" size="small">
        <el-table-column prop="id" label="编号" width="90" />
        <el-table-column prop="output_name" label="染色布" />
        <el-table-column prop="output_color" label="颜色" width="120" />
        <el-table-column prop="quantity" label="数量" width="120" />
        <el-table-column prop="status" label="状态" width="120" />
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="物料入库">
      <el-form :model="form" label-width="90px">
        <el-form-item label="类型">
          <el-select v-model="form.type" style="width: 100%">
            <el-option label="坯布" value="raw_fabric" />
            <el-option label="染色布" value="dyed_fabric" />
            <el-option label="辅料" value="accessory" />
          </el-select>
        </el-form-item>
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="颜色"><el-input v-model="form.color" /></el-form-item>
        <el-form-item label="数量"><el-input v-model.number="form.quantity" type="number" /></el-form-item>
        <el-form-item label="单位"><el-input v-model="form.unit" /></el-form-item>
        <el-form-item label="供应商">
          <el-select v-model="form.supplier" clearable style="width: 100%">
            <el-option v-for="s in filteredSuppliers" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="仓库">
          <el-select v-model="form.warehouse" clearable style="width: 100%">
            <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker
            v-model="form.stock_date"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer><el-button type="primary" @click="createMaterial">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="dyeDialogVisible" title="新建染色单">
      <el-form :model="dyeForm" label-width="110px">
        <el-form-item label="坯布">
          <el-select v-model="dyeForm.raw_material_id" style="width: 100%">
            <el-option v-for="m in materials.filter(x => x.type === 'raw_fabric')" :key="m.id" :label="`${m.name}(${m.quantity})`" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="染厂">
          <el-select v-model="dyeForm.supplier_id" style="width: 100%">
            <el-option v-for="s in suppliers.filter(x => x.type === '染厂')" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="染色布名称"><el-input v-model="dyeForm.output_name" /></el-form-item>
        <el-form-item label="颜色"><el-input v-model="dyeForm.output_color" /></el-form-item>
        <el-form-item label="数量"><el-input v-model.number="dyeForm.quantity" type="number" /></el-form-item>
        <el-form-item label="入库仓">
          <el-select v-model="dyeForm.output_warehouse_id" style="width: 100%">
            <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer><el-button type="primary" @click="createDyeingOrder">创建并执行</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.material-management { padding: 16px 0; }
.header-line { display: flex; justify-content: space-between; align-items: center; }
</style>
