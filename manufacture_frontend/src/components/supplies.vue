<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../utils/axios'

const suppliers = ref([])
const warehouses = ref([])
const dialogVisible = ref(false)
const warehouseDialogVisible = ref(false)
const supplierForm = ref({ name: '', type: '辅料' })
const warehouseForm = ref({ name: '', warehouse_type: 'factory', factory: null })
const factories = ref([])

const loadData = async () => {
  const [s, w, f] = await Promise.all([
    api.get('/suppliers/'),
    api.get('/warehouse-nodes/'),
    api.get('/factories/')
  ])
  suppliers.value = s.data
  warehouses.value = w.data
  factories.value = f.data
}

const saveSupplier = async () => {
  await api.post('/suppliers/', supplierForm.value)
  supplierForm.value = { name: '', type: '辅料' }
  dialogVisible.value = false
  await loadData()
  ElMessage.success('供应商已保存')
}

const saveWarehouse = async () => {
  await api.post('/warehouse-nodes/', warehouseForm.value)
  warehouseForm.value = { name: '', warehouse_type: 'factory', factory: null }
  warehouseDialogVisible.value = false
  await loadData()
  ElMessage.success('仓库已保存')
}

const removeSupplier = async (id) => {
  await api.delete(`/suppliers/${id}/`)
  await loadData()
}

onMounted(loadData)
</script>

<template>
  <div class="supplies-management">
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="header-line">
              <span>供应商主数据</span>
              <el-button type="primary" @click="dialogVisible = true">新增</el-button>
            </div>
          </template>
          <el-table :data="suppliers" size="small">
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="type" label="类型" width="120" />
            <el-table-column label="操作" width="90">
              <template #default="{ row }">
                <el-button type="danger" link @click="removeSupplier(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="header-line">
              <span>仓库主数据</span>
              <el-button type="primary" @click="warehouseDialogVisible = true">新增</el-button>
            </div>
          </template>
          <el-table :data="warehouses" size="small">
            <el-table-column prop="name" label="名称" />
            <el-table-column label="仓别" width="120">
              <template #default="{ row }">{{ row.warehouse_type === 'factory' ? '工厂仓' : '本地仓' }}</template>
            </el-table-column>
            <el-table-column prop="factory_name" label="所属工厂" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="dialogVisible" title="新增供应商">
      <el-form :model="supplierForm" label-width="90px">
        <el-form-item label="名称"><el-input v-model="supplierForm.name" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="supplierForm.type" style="width: 100%">
            <el-option label="辅料" value="辅料" />
            <el-option label="坯布" value="坯布" />
            <el-option label="染厂" value="染厂" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer><el-button type="primary" @click="saveSupplier">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="warehouseDialogVisible" title="新增仓库">
      <el-form :model="warehouseForm" label-width="90px">
        <el-form-item label="名称"><el-input v-model="warehouseForm.name" /></el-form-item>
        <el-form-item label="仓别">
          <el-select v-model="warehouseForm.warehouse_type" style="width: 100%">
            <el-option label="工厂仓" value="factory" />
            <el-option label="本地仓" value="local" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属工厂">
          <el-select v-model="warehouseForm.factory" clearable style="width: 100%">
            <el-option v-for="f in factories" :key="f.id" :value="f.id" :label="f.name" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer><el-button type="primary" @click="saveWarehouse">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.supplies-management { padding: 16px 0; }
.header-line { display: flex; justify-content: space-between; align-items: center; }
</style>