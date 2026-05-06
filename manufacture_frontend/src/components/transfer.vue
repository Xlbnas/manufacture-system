<script setup>
import { onMounted, ref, watch, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../utils/axios'
import { templateLabelForKey, isKnownTemplateKey } from '../constants/productionTemplates.js'

const orders = ref([])
const nodes = ref([])
const products = ref([])

/** 使用 reactive，避免 el-form + el-select 与 ref 嵌套时偶发不同步，导致仓库/成品 id 未写入、库存请求无参数 */
const form = reactive({
  from_warehouse_id: null,
  to_warehouse_id: null,
  note: '',
  product_id: null,
})

const transferFormRef = ref(null)
const transferRules = {
  from_warehouse_id: [{ required: true, message: '请选择来源工厂仓', trigger: 'change' }],
  to_warehouse_id: [{ required: true, message: '请选择目标本地仓', trigger: 'change' }],
  product_id: [{ required: true, message: '请选择模板成品', trigger: 'change' }],
}

const factoryStockRows = ref([])
const loadingStock = ref(false)
/** 每行成品库存 id -> { checked, qty } */
const picks = reactive({})

function extractList(data) {
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.results)) return data.results
  return []
}

const load = async () => {
  const [o, n, p] = await Promise.all([
    api.get('/transfer-orders/'),
    api.get('/warehouse-nodes/'),
    api.get('/products/'),
  ])
  orders.value = extractList(o.data)
  nodes.value = extractList(n.data)
  products.value = extractList(p.data)
}

const transferProductOptions = computed(() =>
  products.value.filter(
    (p) => p.production_template_key && isKnownTemplateKey(p.production_template_key)
  )
)

function transferProductLabel(p) {
  const k = p.production_template_key
  const t = k && isKnownTemplateKey(k) ? templateLabelForKey(k) : ''
  if (t && p.name && String(p.name).trim() === t) return t
  if (t) return `${t} · ${p.name}`
  return p.name || ''
}

const factoryNodes = computed(() => nodes.value.filter((x) => x.warehouse_type === 'factory'))
const localNodes = computed(() => nodes.value.filter((x) => x.warehouse_type === 'local'))

const canLoadStock = computed(() => !!(form.from_warehouse_id && form.product_id))

const resetPicksForRows = (rows) => {
  for (const k of Object.keys(picks)) delete picks[k]
  for (const r of rows) {
    picks[r.id] = { checked: false, qty: 0 }
  }
}

const fetchFactoryStock = async () => {
  const wid = form.from_warehouse_id
  const pid = form.product_id
  if (wid == null || wid === '' || pid == null || pid === '') {
    factoryStockRows.value = []
    resetPicksForRows([])
    return
  }
  loadingStock.value = true
  try {
    const { data } = await api.get('/warehouse/', {
      params: {
        warehouse_id: Number(wid),
        product_id: Number(pid),
        only_positive: 1,
      },
    })
    const rows = extractList(data)
    factoryStockRows.value = rows
    resetPicksForRows(rows)
  } catch (e) {
    console.error(e)
    factoryStockRows.value = []
    resetPicksForRows([])
    ElMessage.error('加载工厂仓库存失败')
  } finally {
    loadingStock.value = false
  }
}

watch(
  () => [form.from_warehouse_id, form.product_id],
  () => {
    void fetchFactoryStock()
  }
)

const maxPickQty = (row) => Math.max(0, Number(row.quantity) || 0)

const onPickQtyChange = (row) => {
  const st = picks[row.id]
  if (!st) return
  const max = maxPickQty(row)
  let q = Math.floor(Number(st.qty) || 0)
  if (q < 0) q = 0
  if (q > max) q = max
  st.qty = q
  if (q > 0) st.checked = true
}

const buildItemsFromPicks = () => {
  const pid = form.product_id
  if (!pid) return []
  const items = []
  for (const row of factoryStockRows.value) {
    const st = picks[row.id]
    if (!st?.checked) continue
    const max = maxPickQty(row)
    let q = Math.floor(Number(st.qty) || 0)
    if (q <= 0) continue
    if (q > max) q = max
    items.push({
      product_id: pid,
      color: row.color,
      size: row.size,
      quantity: q,
    })
  }
  return items
}

const createOrder = async () => {
  const el = transferFormRef.value
  if (el) {
    try {
      await el.validate()
    } catch {
      return
    }
  }
  const items = buildItemsFromPicks()
  if (!items.length) {
    ElMessage.warning('请勾选库存行并填写大于 0 的调拨数量')
    return
  }
  try {
    await api.post('/transfer-orders/', {
      from_warehouse_id: form.from_warehouse_id,
      to_warehouse_id: form.to_warehouse_id,
      note: form.note || '',
      items,
    })
    await load()
    ElMessage.success('调拨单已创建')
    for (const r of factoryStockRows.value) {
      const st = picks[r.id]
      if (st) {
        st.checked = false
        st.qty = 0
      }
    }
    void fetchFactoryStock()
  } catch (e) {
    const d = e?.response?.data
    const msg =
      typeof d === 'string'
        ? d
        : d?.detail || (d && JSON.stringify(d)) || e?.message || '创建失败'
    ElMessage.error(String(msg))
  }
}

const completeOrder = async (row) => {
  await api.post(`/transfer-orders/${row.id}/complete/`)
  await load()
  void fetchFactoryStock()
  ElMessage.success('调拨已执行')
}

onMounted(load)
</script>

<template>
  <div class="transfer-page">
    <el-card>
      <template #header>
        <span>工厂仓 → 本地仓 调拨</span>
      </template>
      <p class="hint">
        先选<strong>来源工厂仓</strong>与<strong>模板成品</strong>，表格仅展示该仓、该成品下<strong>有库存</strong>的颜色与尺码；勾选并填写数量后一次生成多条明细，避免手工逐行录入。
      </p>
      <el-form ref="transferFormRef" :model="form" :rules="transferRules" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="来源仓" prop="from_warehouse_id">
              <el-select
                v-model="form.from_warehouse_id"
                placeholder="工厂仓（成品库存来源）"
                style="width: 100%"
                clearable
                @change="fetchFactoryStock"
              >
                <el-option
                  v-for="n in factoryNodes"
                  :key="n.id"
                  :label="n.name"
                  :value="n.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="目标仓" prop="to_warehouse_id">
              <el-select
                v-model="form.to_warehouse_id"
                placeholder="本地仓"
                style="width: 100%"
                clearable
              >
                <el-option
                  v-for="n in localNodes"
                  :key="n.id"
                  :label="n.name"
                  :value="n.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="备注" prop="note">
              <el-input v-model="form.note" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="模板成品" prop="product_id">
          <el-select
            v-model="form.product_id"
            placeholder="选择成品（仅展示系统模板线）"
            style="width: 100%; max-width: 420px"
            clearable
            filterable
            @change="fetchFactoryStock"
          >
            <el-option
              v-for="p in transferProductOptions"
              :key="p.id"
              :label="transferProductLabel(p)"
              :value="p.id"
            />
          </el-select>
        </el-form-item>

        <div v-if="!canLoadStock" class="stock-placeholder">
          请选择来源工厂仓与模板成品后，将加载该仓库存行。
        </div>
        <div v-else>
          <div class="stock-toolbar">
            <span>可调库存（仅当前工厂仓 × 当前成品）</span>
            <el-button size="small" :loading="loadingStock" @click="fetchFactoryStock">刷新库存</el-button>
          </div>
          <el-table
            v-loading="loadingStock"
            :data="factoryStockRows"
            size="small"
            border
            max-height="400"
            empty-text="该仓该成品暂无可用库存（或数量均为 0）"
          >
            <el-table-column label="调拨" width="64" align="center">
              <template #default="{ row }">
                <el-checkbox v-model="picks[row.id].checked" />
              </template>
            </el-table-column>
            <el-table-column prop="color" label="颜色" width="120" />
            <el-table-column prop="size" label="尺码" width="90" />
            <el-table-column label="工厂仓库存" width="120" align="right">
              <template #default="{ row }">{{ row.quantity }}</template>
            </el-table-column>
            <el-table-column label="调拨数量" width="140" align="center">
              <template #default="{ row }">
                <el-input-number
                  v-model="picks[row.id].qty"
                  :min="0"
                  :max="maxPickQty(row)"
                  :disabled="maxPickQty(row) <= 0"
                  size="small"
                  controls-position="right"
                  @change="onPickQtyChange(row)"
                />
              </template>
            </el-table-column>
          </el-table>
        </div>

        <el-form-item style="margin-top: 16px">
          <el-button type="primary" @click="createOrder">创建调拨单</el-button>
        </el-form-item>
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
.transfer-page {
  padding: 16px 0;
}
.hint {
  margin: 0 0 14px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  line-height: 1.55;
}
.stock-placeholder {
  padding: 16px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.stock-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--el-text-color-regular);
}
</style>
