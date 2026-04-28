<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../utils/axios'

const stocks = ref([])
const warehouses = ref([])

const load = async () => {
  const [s, w] = await Promise.all([api.get('/warehouse/'), api.get('/warehouse-nodes/')])
  stocks.value = s.data
  warehouses.value = w.data
}

const factoryStocks = computed(() => stocks.value.filter(x => x.warehouse?.warehouse_type === 'factory'))
const localStocks = computed(() => stocks.value.filter(x => x.warehouse?.warehouse_type === 'local'))

onMounted(load)
</script>

<template>
  <div class="warehouse-page">
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <template #header><span>工厂仓库存</span></template>
          <el-table :data="factoryStocks" size="small">
            <el-table-column prop="warehouse.name" label="仓库" />
            <el-table-column prop="product.name" label="产品" />
            <el-table-column prop="color" label="颜色" width="100" />
            <el-table-column prop="size" label="尺码" width="100" />
            <el-table-column prop="quantity" label="数量" width="100" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><span>本地仓库存</span></template>
          <el-table :data="localStocks" size="small">
            <el-table-column prop="warehouse.name" label="仓库" />
            <el-table-column prop="product.name" label="产品" />
            <el-table-column prop="color" label="颜色" width="100" />
            <el-table-column prop="size" label="尺码" width="100" />
            <el-table-column prop="quantity" label="数量" width="100" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.warehouse-page { padding: 16px 0; }
</style>
