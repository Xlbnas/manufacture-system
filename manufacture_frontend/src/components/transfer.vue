<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../utils/axios'

const orders = ref([])
const nodes = ref([])
const products = ref([])
const form = ref({
  from_warehouse_id: null,
  to_warehouse_id: null,
  note: '',
  items: [{ product_id: null, color: '', size: '', quantity: 0 }]
})

const load = async () => {
  const [o, n, p] = await Promise.all([
    api.get('/transfer-orders/'),
    api.get('/warehouse-nodes/'),
    api.get('/products/')
  ])
  orders.value = o.data
  nodes.value = n.data
  products.value = p.data
}

const addItem = () => form.value.items.push({ product_id: null, color: '', size: '', quantity: 0 })

const createOrder = async () => {
  await api.post('/transfer-orders/', form.value)
  await load()
  ElMessage.success('调拨单已创建')
}

const completeOrder = async (row) => {
  await api.post(`/transfer-orders/${row.id}/complete/`)
  await load()
  ElMessage.success('调拨已执行')
}

onMounted(load)
</script>

<template>
  <div class="transfer-page">
    <el-card>
      <template #header><span>工厂仓 -> 本地仓 调拨</span></template>
      <el-form :model="form" label-width="90px">
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="来源仓">
              <el-select v-model="form.from_warehouse_id" style="width: 100%">
                <el-option v-for="n in nodes.filter(x => x.warehouse_type === 'factory')" :key="n.id" :label="n.name" :value="n.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="目标仓">
              <el-select v-model="form.to_warehouse_id" style="width: 100%">
                <el-option v-for="n in nodes.filter(x => x.warehouse_type === 'local')" :key="n.id" :label="n.name" :value="n.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8"><el-form-item label="备注"><el-input v-model="form.note" /></el-form-item></el-col>
        </el-row>
        <div v-for="(item, idx) in form.items" :key="idx" class="line">
          <el-select v-model="item.product_id" placeholder="产品" style="width: 180px">
            <el-option v-for="p in products" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
          <el-input v-model="item.color" placeholder="颜色" style="width: 120px" />
          <el-input v-model="item.size" placeholder="尺码" style="width: 120px" />
          <el-input v-model.number="item.quantity" type="number" placeholder="数量" style="width: 120px" />
        </div>
        <el-button @click="addItem">新增明细</el-button>
        <el-button type="primary" @click="createOrder">创建调拨单</el-button>
      </el-form>
    </el-card>

    <el-card style="margin-top: 16px">
      <template #header><span>调拨单列表</span></template>
      <el-table :data="orders" size="small">
        <el-table-column prop="id" label="编号" width="80" />
        <el-table-column prop="from_warehouse.name" label="来源仓" />
        <el-table-column prop="to_warehouse.name" label="目标仓" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button v-if="row.status === 'draft'" type="success" link @click="completeOrder(row)">执行</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.transfer-page { padding: 16px 0; }
.line { display: flex; gap: 8px; margin-bottom: 8px; }
</style>
