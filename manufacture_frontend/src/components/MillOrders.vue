<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../utils/axios'

const router = useRouter()
const activeTab = ref('dyeing')
const dyeingList = ref([])
const weavingList = ref([])
const suppliers = ref([])
const warehouses = ref([])

const detailVisible = ref(false)
const detailType = ref('dyeing')
const detailOrder = ref(null)
const receiptForm = ref({ quantity: null, receipt_date: '', note: '' })

const weaveDialogVisible = ref(false)
const weaveForm = ref({
  supplier_id: null,
  fabric_name: '',
  fabric_color: '',
  quantity: null,
  unit: '米',
  inbound_warehouse_id: null,
  expected_delivery: '',
  note: '',
})

const getTodayChinaDate = () => {
  const now = new Date()
  const chinaNow = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Shanghai' }))
  const y = chinaNow.getFullYear()
  const m = `${chinaNow.getMonth() + 1}`.padStart(2, '0')
  const d = `${chinaNow.getDate()}`.padStart(2, '0')
  return `${y}-${m}-${d}`
}

const statusLabel = (s) =>
  ({
    draft: '草稿',
    receiving: '到货中',
    completed: '已完成',
    cancelled: '已取消',
  }[s] || s)

const weavingSuppliers = computed(() => suppliers.value.filter((x) => x.type === '布厂'))

const asList = (data) => {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

const loadAll = async () => {
  const [d, w, s, wh] = await Promise.all([
    api.get('/dyeing-orders/'),
    api.get('/weaving-orders/'),
    api.get('/suppliers/'),
    api.get('/warehouse-nodes/'),
  ])
  dyeingList.value = asList(d.data)
  weavingList.value = asList(w.data)
  suppliers.value = s.data
  warehouses.value = wh.data
}

const openDetail = async (row, type) => {
  detailType.value = type
  const path = type === 'dyeing' ? `/dyeing-orders/${row.id}/` : `/weaving-orders/${row.id}/`
  const { data } = await api.get(path)
  detailOrder.value = data
  receiptForm.value = { quantity: null, receipt_date: getTodayChinaDate(), note: '' }
  detailVisible.value = true
}

const remaining = (order) => {
  if (!order) return 0
  const q = Number(order.quantity) || 0
  const r = Number(order.received_quantity) || 0
  return Math.max(0, q - r)
}

const canReceive = (order) => order && ['draft', 'receiving'].includes(order.status) && remaining(order) > 0

const submitReceipt = async () => {
  const id = detailOrder.value?.id
  if (!id) return
  const qty = Number(receiptForm.value.quantity)
  if (!qty || qty <= 0) {
    ElMessage.warning('请输入大于 0 的到货数量')
    return
  }
  const base = detailType.value === 'dyeing' ? '/dyeing-orders' : '/weaving-orders'
  try {
    await api.post(`${base}/${id}/receipts/`, {
      quantity: qty,
      receipt_date: receiptForm.value.receipt_date || undefined,
      note: receiptForm.value.note || '',
    })
    ElMessage.success('已登记到货')
    detailVisible.value = false
    await loadAll()
  } catch (e) {
    const msg = e?.response?.data?.error || e?.response?.data ? JSON.stringify(e.response.data) : e?.message
    ElMessage.error(msg || '登记失败')
  }
}

const completeAll = async (row, type) => {
  const base = type === 'dyeing' ? '/dyeing-orders' : '/weaving-orders'
  try {
    await api.post(`${base}/${row.id}/complete/`)
    ElMessage.success('已按剩余数量整单收货')
    await loadAll()
  } catch (e) {
    const msg = e?.response?.data?.error || (e?.response?.data ? JSON.stringify(e.response.data) : e?.message)
    ElMessage.error(msg || '操作失败')
  }
}

const openWeaveDialog = () => {
  weaveForm.value = {
    supplier_id: null,
    fabric_name: '',
    fabric_color: '',
    quantity: null,
    unit: '米',
    inbound_warehouse_id: null,
    expected_delivery: '',
    note: '',
  }
  weaveDialogVisible.value = true
}

const createWeavingOrder = async () => {
  if (!weaveForm.value.supplier_id || !weaveForm.value.fabric_name || !weaveForm.value.inbound_warehouse_id) {
    ElMessage.warning('请填写布厂、布料名称与入库仓')
    return
  }
  const q = Number(weaveForm.value.quantity)
  if (!q || q <= 0) {
    ElMessage.warning('请填写约定产量')
    return
  }
  const body = {
    supplier_id: weaveForm.value.supplier_id,
    fabric_name: weaveForm.value.fabric_name,
    fabric_color: weaveForm.value.fabric_color || '',
    quantity: q,
    unit: weaveForm.value.unit || '米',
    inbound_warehouse_id: weaveForm.value.inbound_warehouse_id,
    note: weaveForm.value.note || '',
  }
  if (weaveForm.value.expected_delivery) {
    body.expected_delivery = weaveForm.value.expected_delivery
  }
  try {
    await api.post('/weaving-orders/', body)
    ElMessage.success('布厂外协单已创建')
    weaveDialogVisible.value = false
    await loadAll()
  } catch (e) {
    const msg = e?.response?.data ? JSON.stringify(e.response.data) : e?.message
    ElMessage.error(msg || '创建失败')
  }
}

const goMaterial = () => {
  router.push('/material')
}

onMounted(loadAll)
</script>

<template>
  <div class="mill-orders">
    <el-card>
      <template #header>
        <div class="header-line">
          <span>染厂 / 布厂外协</span>
          <div>
            <el-button type="primary" plain @click="goMaterial">去材料页新建染色单</el-button>
            <el-button type="success" @click="openWeaveDialog">新建布厂单</el-button>
          </div>
        </div>
      </template>

      <el-alert type="info" show-icon :closable="false" class="hint">
        登记到货后写入「材料溯源」中的坯布 / 染色布库存；染色按每批米数 1:1 扣减所选坯布行。
      </el-alert>

      <el-tabs v-model="activeTab" class="tabs">
        <el-tab-pane label="染厂外协（染色单）" name="dyeing">
          <el-table :data="dyeingList" size="small" stripe>
            <el-table-column prop="id" label="编号" width="72" />
            <el-table-column label="染厂" min-width="120">
              <template #default="{ row }">{{ row.supplier?.name || '—' }}</template>
            </el-table-column>
            <el-table-column prop="output_name" label="染色布名称" min-width="120" />
            <el-table-column prop="output_color" label="颜色" width="90" />
            <el-table-column prop="quantity" label="约定" width="88" />
            <el-table-column prop="received_quantity" label="已到货" width="88" />
            <el-table-column label="剩余" width="88">
              <template #default="{ row }">{{ remaining(row).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="96">
              <template #default="{ row }">{{ statusLabel(row.status) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="openDetail(row, 'dyeing')">详情 / 到货</el-button>
                <el-button
                  v-if="canReceive(row)"
                  type="success"
                  link
                  size="small"
                  @click="completeAll(row, 'dyeing')"
                >
                  整单收齐
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="布厂外协" name="weaving">
          <el-table :data="weavingList" size="small" stripe>
            <el-table-column prop="id" label="编号" width="72" />
            <el-table-column label="布厂" min-width="120">
              <template #default="{ row }">{{ row.supplier?.name || '—' }}</template>
            </el-table-column>
            <el-table-column prop="fabric_name" label="布料名称" min-width="120" />
            <el-table-column prop="fabric_color" label="颜色" width="90" />
            <el-table-column prop="quantity" label="约定" width="88" />
            <el-table-column prop="received_quantity" label="已到货" width="88" />
            <el-table-column label="剩余" width="88">
              <template #default="{ row }">{{ remaining(row).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="96">
              <template #default="{ row }">{{ statusLabel(row.status) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="openDetail(row, 'weaving')">详情 / 到货</el-button>
                <el-button
                  v-if="canReceive(row)"
                  type="success"
                  link
                  size="small"
                  @click="completeAll(row, 'weaving')"
                >
                  整单收齐
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-drawer v-model="detailVisible" :title="detailType === 'dyeing' ? '染色单详情' : '布厂单详情'" size="480px">
      <template v-if="detailOrder">
        <el-descriptions :column="1" border size="small" class="desc">
          <el-descriptions-item label="编号">{{ detailOrder.id }}</el-descriptions-item>
          <el-descriptions-item v-if="detailType === 'dyeing'" label="坯布">
            {{ detailOrder.raw_material?.name }}（余量 {{ detailOrder.raw_material?.quantity }}）
          </el-descriptions-item>
          <el-descriptions-item v-if="detailType === 'dyeing'" label="染色布">
            {{ detailOrder.output_name }} / {{ detailOrder.output_color }}
          </el-descriptions-item>
          <el-descriptions-item v-if="detailType === 'weaving'" label="布料">
            {{ detailOrder.fabric_name }} / {{ detailOrder.fabric_color }}
          </el-descriptions-item>
          <el-descriptions-item label="约定 / 已收 / 剩余">
            {{ detailOrder.quantity }} / {{ detailOrder.received_quantity }} / {{ remaining(detailOrder).toFixed(2) }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">{{ statusLabel(detailOrder.status) }}</el-descriptions-item>
        </el-descriptions>

        <h4 class="sub">到货记录</h4>
        <el-table :data="detailOrder.receipts || []" size="small" max-height="220">
          <el-table-column prop="receipt_date" label="日期" width="110" />
          <el-table-column prop="quantity" label="米数" width="88" />
          <el-table-column prop="note" label="备注" show-overflow-tooltip />
        </el-table>

        <template v-if="canReceive(detailOrder)">
          <h4 class="sub">登记本批到货</h4>
          <el-form label-width="88px" size="small">
            <el-form-item label="本批米数">
              <el-input v-model.number="receiptForm.quantity" type="number" placeholder="大于 0" />
            </el-form-item>
            <el-form-item label="到货日期">
              <el-date-picker
                v-model="receiptForm.receipt_date"
                type="date"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="备注">
              <el-input v-model="receiptForm.note" type="textarea" rows="2" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="submitReceipt">提交到货</el-button>
              <el-button @click="goMaterial">打开材料溯源</el-button>
            </el-form-item>
          </el-form>
        </template>
        <el-alert v-else type="success" :closable="false">该单已收齐或不可再收货。</el-alert>
      </template>
    </el-drawer>

    <el-dialog v-model="weaveDialogVisible" title="新建布厂外协单" width="520px">
      <el-form :model="weaveForm" label-width="100px" size="small">
        <el-form-item label="布厂" required>
          <el-select v-model="weaveForm.supplier_id" placeholder="选布厂类型供应商" style="width: 100%">
            <el-option v-for="s in weavingSuppliers" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="布料名称" required>
          <el-input v-model="weaveForm.fabric_name" />
        </el-form-item>
        <el-form-item label="颜色">
          <el-input v-model="weaveForm.fabric_color" />
        </el-form-item>
        <el-form-item label="约定产量" required>
          <el-input v-model.number="weaveForm.quantity" type="number" />
        </el-form-item>
        <el-form-item label="单位">
          <el-input v-model="weaveForm.unit" />
        </el-form-item>
        <el-form-item label="入库仓" required>
          <el-select v-model="weaveForm.inbound_warehouse_id" style="width: 100%">
            <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="预计交期">
          <el-date-picker
            v-model="weaveForm.expected_delivery"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 100%"
            clearable
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="weaveForm.note" type="textarea" rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="weaveDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createWeavingOrder">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.mill-orders {
  padding: 16px 0;
}
.header-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.hint {
  margin-bottom: 16px;
}
.tabs {
  margin-top: 8px;
}
.sub {
  margin: 16px 0 8px;
  font-size: 14px;
  font-weight: 600;
}
.desc {
  margin-bottom: 8px;
}
</style>
