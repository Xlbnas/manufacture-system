<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../utils/axios'
import { templateLabelForKey, isKnownTemplateKey } from '../constants/productionTemplates.js'

const orders = ref([])
const nodes = ref([])
const products = ref([])

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
const picks = reactive({})

const editDialogVisible = ref(false)
const editingOrderId = ref(null)
const editForm = reactive({
  from_warehouse_id: null,
  to_warehouse_id: null,
  note: '',
  items: [],
})

const SIZE_ORDER = ['XS', 'S', 'M', 'L', 'XL', 'XXL', '2XL', '3XL', '4XL']
const SIZE_INDEX = Object.freeze(
  SIZE_ORDER.reduce((m, x, i) => {
    m[x] = i
    return m
  }, {})
)

function normalizeSize(size) {
  return String(size || '').trim().toUpperCase().replace(/\s+/g, '')
}
function sizeSortIndex(size) {
  const n = normalizeSize(size)
  return Object.prototype.hasOwnProperty.call(SIZE_INDEX, n) ? SIZE_INDEX[n] : 999
}

function extractList(data) {
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.results)) return data.results
  return []
}

const load = async () => {
  const [o, n, p] = await Promise.all([api.get('/transfer-orders/'), api.get('/warehouse-nodes/'), api.get('/products/')])
  orders.value = extractList(o.data)
  nodes.value = extractList(n.data)
  products.value = extractList(p.data)
}

const transferProductOptions = computed(() =>
  products.value.filter((p) => p.production_template_key && isKnownTemplateKey(p.production_template_key))
)
function transferProductLabel(p) {
  const t = p.production_template_key ? templateLabelForKey(p.production_template_key) : ''
  if (t && p.name && String(p.name).trim() === t) return t
  if (t) return `${t} · ${p.name}`
  return p.name || ''
}

const factoryNodes = computed(() => nodes.value.filter((x) => x.warehouse_type === 'factory'))
const localNodes = computed(() => nodes.value.filter((x) => x.warehouse_type === 'local'))
const canLoadStock = computed(() => !!(form.from_warehouse_id && form.product_id))

const sortedFactoryStockRows = computed(() =>
  [...factoryStockRows.value].sort((a, b) => {
    const c = String(a.color || '').localeCompare(String(b.color || ''), 'zh-CN')
    if (c !== 0) return c
    const si = sizeSortIndex(a.size) - sizeSortIndex(b.size)
    if (si !== 0) return si
    return String(a.size || '').localeCompare(String(b.size || ''), 'zh-CN', { numeric: true })
  })
)

const colorRowspanMap = computed(() => {
  const rows = sortedFactoryStockRows.value
  const m = new Map()
  let i = 0
  while (i < rows.length) {
    let j = i + 1
    while (j < rows.length && String(rows[j].color || '') === String(rows[i].color || '')) j += 1
    m.set(rows[i].id, j - i)
    for (let k = i + 1; k < j; k += 1) m.set(rows[k].id, 0)
    i = j
  }
  return m
})
const stockSpanMethod = ({ row, column }) => {
  if (column.property !== 'color') return [1, 1]
  const n = colorRowspanMap.value.get(row.id) ?? 1
  return n > 0 ? [n, 1] : [0, 0]
}

const statusText = (s) =>
  s === 'draft'
    ? '草稿'
    : s === 'completed'
      ? '已执行'
      : s === 'cancelled'
        ? '已取消'
        : s === 'reversed'
          ? '已冲销'
          : s || '-'
const statusTagType = (s) =>
  s === 'draft' ? 'warning' : s === 'completed' ? 'success' : s === 'reversed' ? 'warning' : 'info'

const resetPicksForRows = (rows) => {
  for (const k of Object.keys(picks)) delete picks[k]
  for (const r of rows) picks[r.id] = { checked: false, qty: 0 }
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
      params: { warehouse_id: Number(wid), product_id: Number(pid), only_positive: 1 },
    })
    const rows = extractList(data)
    factoryStockRows.value = rows
    resetPicksForRows(rows)
  } catch (e) {
    factoryStockRows.value = []
    resetPicksForRows([])
    ElMessage.error('加载工厂仓库存失败')
  } finally {
    loadingStock.value = false
  }
}

watch(() => [form.from_warehouse_id, form.product_id], () => void fetchFactoryStock())

const maxPickQty = (row) => Math.max(0, Number(row.quantity) || 0)
const onPickQtyChange = (row) => {
  const st = picks[row.id]
  if (!st) return
  let q = Math.floor(Number(st.qty) || 0)
  q = Math.max(0, Math.min(q, maxPickQty(row)))
  st.qty = q
  if (q > 0) st.checked = true
}

const buildItemsFromPicks = () => {
  if (!form.product_id) return []
  const items = []
  for (const row of sortedFactoryStockRows.value) {
    const st = picks[row.id]
    if (!st?.checked) continue
    const q = Math.max(0, Math.min(Math.floor(Number(st.qty) || 0), maxPickQty(row)))
    if (!q) continue
    items.push({ product_id: form.product_id, color: row.color, size: row.size, quantity: q })
  }
  return items
}

const createOrder = async () => {
  const formInst = transferFormRef.value
  if (formInst) {
    try {
      await formInst.validate()
    } catch {
      return
    }
  }
  const items = buildItemsFromPicks()
  if (!items.length) {
    ElMessage.warning('请勾选库存行并填写大于 0 的调拨数量')
    return
  }
  await api.post('/transfer-orders/', {
    from_warehouse_id: form.from_warehouse_id,
    to_warehouse_id: form.to_warehouse_id,
    note: form.note || '',
    items,
  })
  await load()
  ElMessage.success('调拨单已创建')
  void fetchFactoryStock()
}

const completeOrder = async (row) => {
  await api.post(`/transfer-orders/${row.id}/complete/`)
  await load()
  void fetchFactoryStock()
  ElMessage.success('调拨已执行')
}

const cancelOrder = async (row) => {
  await ElMessageBox.confirm(`确认取消调拨单 #${row.id}？`, '取消调拨', {
    confirmButtonText: '确认取消',
    cancelButtonText: '返回',
    type: 'warning',
  })
  await api.post(`/transfer-orders/${row.id}/cancel/`)
  await load()
  ElMessage.success('调拨单已取消')
}

const reverseOrder = async (row) => {
  await ElMessageBox.confirm(
    `冲销调拨单 #${row.id}：将把本单数量从「${row.to_warehouse?.name || '本地仓'}」退回「${row.from_warehouse?.name || '工厂仓'}」。`,
    '库存冲销',
    {
      confirmButtonText: '确认冲销',
      cancelButtonText: '返回',
      type: 'warning',
    }
  )
  try {
    await api.post(`/transfer-orders/${row.id}/reverse/`)
    await load()
    void fetchFactoryStock()
    ElMessage.success('调拨已冲销，库存已退回工厂仓')
  } catch (e) {
    const msg = e?.response?.data?.error || e?.response?.data?.detail || e?.message || '冲销失败'
    ElMessage.error(String(msg))
  }
}

const openEditDialog = (row) => {
  editingOrderId.value = row.id
  editForm.from_warehouse_id = row.from_warehouse?.id ?? null
  editForm.to_warehouse_id = row.to_warehouse?.id ?? null
  editForm.note = row.note || ''
  editForm.items = (row.items || []).map((it) => ({
    product_id: it.product?.id,
    product_name: it.product?.name || '-',
    color: it.color,
    size: it.size,
    quantity: Math.max(1, Math.floor(Number(it.quantity) || 1)),
  }))
  editDialogVisible.value = true
}

const removeEditItem = (idx) => {
  editForm.items.splice(idx, 1)
}

const saveEdit = async () => {
  if (!editingOrderId.value) return
  const items = editForm.items
    .map((x) => ({
      product_id: x.product_id,
      color: String(x.color || '').trim(),
      size: String(x.size || '').trim(),
      quantity: Math.max(0, Math.floor(Number(x.quantity) || 0)),
    }))
    .filter((x) => x.product_id && x.color && x.size && x.quantity > 0)
  if (!items.length) {
    ElMessage.warning('至少保留 1 条有效明细（数量需大于 0）')
    return
  }
  await api.post(`/transfer-orders/${editingOrderId.value}/revise/`, {
    from_warehouse_id: editForm.from_warehouse_id,
    to_warehouse_id: editForm.to_warehouse_id,
    note: editForm.note || '',
    items,
  })
  editDialogVisible.value = false
  await load()
  ElMessage.success('草稿调拨单已更新')
}

onMounted(load)
</script>

<template>
  <div class="transfer-page">
    <el-card>
      <template #header><span>工厂仓 → 本地仓 调拨</span></template>
      <p class="hint">按仓+成品筛选后，库存按颜色分组、尺码从小到大展示，勾选行并填写数量创建调拨草稿。</p>
      <el-form ref="transferFormRef" :model="form" :rules="transferRules" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="来源仓" prop="from_warehouse_id">
              <el-select v-model="form.from_warehouse_id" placeholder="工厂仓（成品库存来源）" clearable @change="fetchFactoryStock">
                <el-option v-for="n in factoryNodes" :key="n.id" :label="n.name" :value="n.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="目标仓" prop="to_warehouse_id">
              <el-select v-model="form.to_warehouse_id" placeholder="本地仓" clearable>
                <el-option v-for="n in localNodes" :key="n.id" :label="n.name" :value="n.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="备注" prop="note"><el-input v-model="form.note" /></el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="模板成品" prop="product_id">
          <el-select v-model="form.product_id" placeholder="选择成品（仅模板线）" clearable filterable @change="fetchFactoryStock">
            <el-option v-for="p in transferProductOptions" :key="p.id" :label="transferProductLabel(p)" :value="p.id" />
          </el-select>
        </el-form-item>

        <div v-if="!canLoadStock" class="stock-placeholder">请选择来源工厂仓与模板成品后，将加载该仓库存行。</div>
        <div v-else>
          <div class="stock-toolbar">
            <span>可调库存（仅当前工厂仓 × 当前成品）</span>
            <el-button size="small" :loading="loadingStock" @click="fetchFactoryStock">刷新库存</el-button>
          </div>
          <el-table
            v-loading="loadingStock"
            :data="sortedFactoryStockRows"
            :span-method="stockSpanMethod"
            class="transfer-stock-table transfer-el-table-unified"
            size="small"
            border
            max-height="420"
            empty-text="该仓该成品暂无可用库存（或数量均为 0）"
          >
            <el-table-column label="调拨" width="72" align="center">
              <template #default="{ row }"><el-checkbox v-model="picks[row.id].checked" /></template>
            </el-table-column>
            <el-table-column prop="color" label="颜色" min-width="140" />
            <el-table-column prop="size" label="尺码" min-width="110" />
            <el-table-column label="工厂仓库存" min-width="140" align="right">
              <template #default="{ row }">{{ row.quantity }}</template>
            </el-table-column>
            <el-table-column label="调拨数量" min-width="220" align="center">
              <template #default="{ row }">
                <el-input-number
                  v-model="picks[row.id].qty"
                  :min="0"
                  :max="maxPickQty(row)"
                  :disabled="maxPickQty(row) <= 0"
                  controls-position="right"
                  @change="onPickQtyChange(row)"
                />
              </template>
            </el-table-column>
          </el-table>
        </div>

        <el-form-item style="margin-top: 16px"><el-button type="primary" @click="createOrder">创建调拨单</el-button></el-form-item>
      </el-form>
    </el-card>

    <el-card class="transfer-orders-card" style="margin-top: 16px">
      <template #header><span>调拨单列表</span></template>
      <div class="orders-table-scroll">
      <el-table :data="orders" class="transfer-orders-table transfer-el-table-unified" size="small" border>
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="transfer-expand-panel">
              <!-- 不使用内嵌 el-table，避免边框/宽度计算与外层表格冲突导致白边与整卡横向溢出 -->
              <template v-if="(row.items || []).length">
                <table class="transfer-expand-native" aria-label="调拨明细">
                  <thead>
                    <tr>
                      <th>产品</th>
                      <th>颜色</th>
                      <th>尺码</th>
                      <th class="num-col">数量</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(it, idx) in row.items" :key="it.id || idx">
                      <td>{{ it.product?.name || '—' }}</td>
                      <td>{{ it.color }}</td>
                      <td>{{ it.size }}</td>
                      <td class="num-col">{{ it.quantity }}</td>
                    </tr>
                  </tbody>
                </table>
              </template>
              <div v-else class="transfer-expand-empty">无明细</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="id" label="编号" width="80" />
        <el-table-column prop="from_warehouse.name" label="来源仓" min-width="120" show-overflow-tooltip />
        <el-table-column prop="to_warehouse.name" label="目标仓" min-width="120" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><el-tag :type="statusTagType(row.status)" effect="plain">{{ statusText(row.status) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="note" label="备注" min-width="140" show-overflow-tooltip />
        <el-table-column label="操作" min-width="170">
          <template #default="{ row }">
            <el-space wrap>
              <template v-if="row.status === 'draft'">
                <el-button type="primary" link @click="openEditDialog(row)">编辑</el-button>
                <el-button type="success" link @click="completeOrder(row)">执行</el-button>
                <el-button type="danger" link @click="cancelOrder(row)">取消</el-button>
              </template>
              <template v-else-if="row.status === 'completed'">
                <el-button type="warning" link @click="reverseOrder(row)">冲销</el-button>
              </template>
              <span v-else class="ops-placeholder">—</span>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
      </div>
    </el-card>

    <el-dialog v-model="editDialogVisible" title="编辑调拨草稿" width="760px" destroy-on-close>
      <el-form label-width="86px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="来源仓">
              <el-select v-model="editForm.from_warehouse_id">
                <el-option v-for="n in factoryNodes" :key="n.id" :label="n.name" :value="n.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标仓">
              <el-select v-model="editForm.to_warehouse_id">
                <el-option v-for="n in localNodes" :key="n.id" :label="n.name" :value="n.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注"><el-input v-model="editForm.note" /></el-form-item>
      </el-form>
      <el-table :data="editForm.items" class="transfer-el-table-unified" size="small" border>
        <el-table-column prop="product_name" label="产品" min-width="120" />
        <el-table-column prop="color" label="颜色" min-width="100" />
        <el-table-column prop="size" label="尺码" min-width="100" />
        <el-table-column label="数量" min-width="130">
          <template #default="{ row }"><el-input-number v-model="row.quantity" :min="1" controls-position="right" /></template>
        </el-table-column>
        <el-table-column label="操作" width="90">
          <template #default="{ $index }"><el-button type="danger" link @click="removeEditItem($index)">删除</el-button></template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.transfer-page { padding: 16px 0; }
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
}
.ops-placeholder { color: var(--el-text-color-placeholder); }
/* 可调库存表与下方统一表格类共用边框变量 */

/* 调拨单卡片：防止展开区把整卡撑出横向滚动（子表用固定布局 + 不外溢） */
.transfer-orders-card {
  min-width: 0;
}

:deep(.transfer-orders-card .el-card__body) {
  min-width: 0;
  overflow-x: hidden;
  padding: var(--el-card-padding);
}

.orders-table-scroll {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow-x: auto;
  overflow-y: hidden;
}

/* 展开明细区：与主表同色系，不用内嵌 EP 表格 */
.transfer-expand-panel {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  padding: 10px 12px 12px;
  margin: 0;
  box-sizing: border-box;
  /* 与外层 el-table 行色一致（黑夜下由父级 --el-table-tr-bg-color 继承） */
  background: var(--el-table-tr-bg-color, var(--card-bg, var(--el-bg-color)));
  border-top: 1px solid var(--el-border-color);
}

.transfer-expand-empty {
  padding: 8px 0;
  font-size: 13px;
  color: var(--el-text-color-placeholder);
}

.transfer-expand-native {
  width: 100%;
  max-width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  font-size: 13px;
  line-height: 1.45;
  color: var(--text-color, var(--el-text-color-regular));
  border: 1px solid var(--border-color, var(--el-border-color));
  background: var(--el-table-tr-bg-color, var(--card-bg, var(--el-bg-color)));
}

.transfer-expand-native th,
.transfer-expand-native td {
  padding: 8px 10px;
  border: 1px solid var(--border-color, var(--el-border-color));
  text-align: left;
  vertical-align: middle;
  word-break: break-word;
}

.transfer-expand-native thead th {
  background: var(--header-bg, var(--el-table-header-bg-color, var(--el-fill-color)));
  color: var(--text-color, var(--el-text-color-regular));
  font-weight: 600;
}

.transfer-expand-native tbody td {
  background: var(--el-table-tr-bg-color, var(--card-bg, var(--el-bg-color)));
  color: var(--text-color, var(--el-text-color-regular));
}

.transfer-expand-native .num-col {
  width: 4.5rem;
  text-align: right;
  white-space: nowrap;
}

:deep(.transfer-el-table-unified.el-table) {
  --el-table-border-color: var(--el-border-color);
  --el-table-text-color: var(--el-text-color-regular);
  --el-table-header-text-color: var(--el-text-color-regular);
  /* 勿覆盖 --el-table-tr-bg-color / --el-table-bg-color：App.vue 的 .dark-mode .el-table 已设为深色 */
  --el-table-expanded-cell-bg-color: var(--el-table-tr-bg-color);
  /* 与 App.vue 自定义黑夜表头一致；勿用 el-bg-color-page（在自定义暗色下常为浅色） */
  --el-table-header-bg-color: var(--header-bg, var(--el-fill-color-light));
}

:deep(.transfer-el-table-unified.el-table--border),
:deep(.transfer-el-table-unified.el-table--border .el-table__footer-wrapper),
:deep(.transfer-el-table-unified.el-table--border .el-table__inner-wrapper),
:deep(.transfer-el-table-unified.el-table--border .el-table__border-left-patch) {
  border-color: var(--el-border-color) !important;
}

:deep(.transfer-el-table-unified.el-table--border)::after {
  border-color: var(--el-border-color) !important;
}

/* 单元格分割线（tbody / header）；!important 压过暗色主题下残留的浅色边框 token */
:deep(.transfer-el-table-unified .el-table__cell) {
  border-color: var(--el-border-color) !important;
}

/* 表头与其它装饰线（不同版本 pseudo 不一致，多兜底） */
:deep(.transfer-el-table-unified .el-table__inner-wrapper::before),
:deep(.transfer-el-table-unified .el-table__inner-wrapper::after) {
  background-color: var(--el-border-color);
}

/* 展开格：与主表同色，避免浅色底/白边残留；限制子内容不撑破列宽 */
:deep(.transfer-orders-table .el-table__expanded-cell) {
  padding: 0 !important;
  background: var(--el-table-tr-bg-color, var(--card-bg, var(--el-bg-color))) !important;
  border-bottom: 1px solid var(--el-border-color);
}

:deep(.transfer-orders-table .el-table__expanded-cell .cell) {
  padding: 0 !important;
  max-width: 100%;
  overflow: hidden;
}

:deep(.transfer-orders-table.el-table) {
  width: 100%;
  max-width: 100%;
  min-width: 680px;
}

:deep(.transfer-orders-table .el-table__expand-icon) {
  color: var(--el-text-color-regular);
  outline: none;
}

:deep(.transfer-orders-table .el-table__expand-icon:focus-visible) {
  outline: 2px solid var(--el-border-color);
  outline-offset: 1px;
  border-radius: 2px;
}

</style>
