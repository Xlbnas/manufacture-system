<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import api from '../utils/axios'
import { deleteWithUndo } from '../composables/deleteWithUndo.js'

const materials = ref([])
const suppliers = ref([])
const warehouses = ref([])
const dyeingOrders = ref([])
const dialogVisible = ref(false)
const editVisible = ref(false)
const previewVisible = ref(false)
const previewUrl = ref('')
const previewTitle = ref('')
const attachmentFile = ref(null)
const editAttachmentFile = ref(null)
const planDetails = ref([])
const router = useRouter()

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
const editForm = ref({})
const dyeDialogVisible = ref(false)
const dyeForm = ref({
  raw_material_id: null,
  supplier_id: null,
  output_name: '',
  output_color: '',
  quantity: 0,
  output_warehouse_id: null,
})

const onAttachmentPick = (f) => {
  attachmentFile.value = f.raw
}
const onAttachmentClear = () => {
  attachmentFile.value = null
}
const onEditAttachmentPick = (f) => {
  editAttachmentFile.value = f.raw
}
const onEditAttachmentClear = () => {
  editAttachmentFile.value = null
}

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

const mediaBase = () => {
  const b = api.defaults.baseURL || ''
  return b.replace(/\/api\/?$/, '') || 'http://127.0.0.1:9876'
}

const attachmentPublicUrl = (row) => {
  if (!row?.attachment) return ''
  const u = row.attachment
  if (typeof u !== 'string') return ''
  if (u.startsWith('http')) return u
  return `${mediaBase()}${u.startsWith('/') ? u : `/${u}`}`
}

const extractMaterials = (payload) => {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.results)) return payload.results
  return []
}

const formatMaterialType = (row) => typeLabelMap[row.type] || row.type

watch(
  () => form.value.type,
  () => {
    if (!filteredSuppliers.value.some((s) => s.id === form.value.supplier)) {
      form.value.supplier = null
    }
    if (form.value.type === 'accessory') {
      form.value.unit = form.value.unit || '批'
    } else if (form.value.type === 'raw_fabric' || form.value.type === 'dyed_fabric') {
      if (form.value.unit === '批') form.value.unit = '米'
    }
    attachmentFile.value = null
  }
)

const load = async () => {
  const [m, s, w, d, p] = await Promise.all([
    api.get('/materials/'),
    api.get('/suppliers/'),
    api.get('/warehouse-nodes/'),
    api.get('/dyeing-orders/'),
    api.get('/production-plan-details/'),
  ])
  materials.value = extractMaterials(m.data)
  suppliers.value = s.data
  warehouses.value = w.data
  dyeingOrders.value = d.data
  planDetails.value = Array.isArray(p.data) ? p.data : []
}

const plansByColor = (color) => {
  const key = (color || '').trim()
  if (!key) return []
  return planDetails.value
    .filter((p) => (p.cloth_color || '').trim() === key)
    .sort((a, b) => String(b.date || '').localeCompare(String(a.date || '')))
}

const openPlan = (planId) => {
  router.push({ path: '/production', query: { planId } })
}

const buildMaterialFormData = (data, file) => {
  const fd = new FormData()
  fd.append('type', data.type)
  fd.append('name', data.name)
  fd.append('color', data.color || '')
  fd.append('quantity', String(data.quantity ?? 0))
  fd.append('unit', data.unit || '')
  fd.append('stock_date', data.stock_date)
  if (data.supplier != null) fd.append('supplier', String(data.supplier))
  if (data.warehouse != null) fd.append('warehouse', String(data.warehouse))
  if (data.remark != null) fd.append('remark', data.remark || '')
  if (data.source_material != null) fd.append('source_material', String(data.source_material))
  if (file) fd.append('attachment', file)
  return fd
}

const createMaterial = async () => {
  try {
    if (form.value.type === 'accessory') {
      if (!attachmentFile.value) {
        ElMessage.warning('辅料请上传附件')
        return
      }
      const fd = buildMaterialFormData(form.value, attachmentFile.value)
      await api.post('/materials/', fd)
    } else {
      await api.post('/materials/', { ...form.value })
    }
    dialogVisible.value = false
    form.value = createDefaultMaterialForm()
    attachmentFile.value = null
    await load()
    ElMessage.success('物料已入库')
  } catch (e) {
    const msg = e?.response?.data ? JSON.stringify(e.response.data) : e?.message
    ElMessage.error(msg || '入库失败')
  }
}

const openMaterialDialog = () => {
  form.value = createDefaultMaterialForm()
  attachmentFile.value = null
  dialogVisible.value = true
}

const openEdit = (row) => {
  editForm.value = {
    id: row.id,
    type: row.type,
    name: row.name,
    color: row.color || '',
    quantity: Number(row.quantity) || 0,
    unit: row.unit,
    supplier: row.supplier?.id ?? row.supplier ?? null,
    warehouse: row.warehouse?.id ?? row.warehouse ?? null,
    stock_date: row.stock_date,
    remark: row.remark || '',
    _attachmentUrl: row.attachment,
  }
  editAttachmentFile.value = null
  editVisible.value = true
}

const saveEdit = async () => {
  try {
    const id = editForm.value.id
    if (editForm.value.type === 'accessory' && editAttachmentFile.value) {
      const fd = buildMaterialFormData(editForm.value, editAttachmentFile.value)
      await api.put(`/materials/${id}/`, fd)
    } else if (editForm.value.type === 'accessory') {
      await api.patch(`/materials/${id}/`, {
        name: editForm.value.name,
        color: editForm.value.color,
        quantity: editForm.value.quantity,
        unit: editForm.value.unit,
        supplier: editForm.value.supplier,
        warehouse: editForm.value.warehouse,
        stock_date: editForm.value.stock_date,
        remark: editForm.value.remark,
      })
    } else {
      await api.put(`/materials/${id}/`, {
        type: editForm.value.type,
        name: editForm.value.name,
        color: editForm.value.color,
        quantity: editForm.value.quantity,
        unit: editForm.value.unit,
        supplier: editForm.value.supplier,
        warehouse: editForm.value.warehouse,
        stock_date: editForm.value.stock_date,
        remark: editForm.value.remark,
      })
    }
    editVisible.value = false
    await load()
    ElMessage.success('已保存')
  } catch (e) {
    const msg = e?.response?.data ? JSON.stringify(e.response.data) : e?.message
    ElMessage.error(msg || '保存失败')
  }
}

const removeMaterial = async (row) => {
  try {
    await deleteWithUndo({
      confirmMessage: `确定删除物料「${row.name}」？`,
      deleteFn: () => api.delete(`/materials/${row.id}/`),
      undo: null,
      onSuccess: load,
      successMessage: '物料已删除',
    })
  } catch (e) {
    console.error(e)
  }
}

const openPreview = (row) => {
  const url = attachmentPublicUrl(row)
  if (!url) {
    ElMessage.info('无附件')
    return
  }
  previewTitle.value = row.name
  previewUrl.value = url
  const lower = url.split('?')[0].toLowerCase()
  if (/\.(png|jpg|jpeg|gif|webp)$/i.test(lower)) {
    previewVisible.value = true
    return
  }
  if (/\.pdf$/i.test(lower)) {
    window.open(url, '_blank', 'noopener')
    return
  }
  ElMessageBox.confirm('该格式将在新窗口打开或下载后查看。', '预览', {
    confirmButtonText: '打开',
    cancelButtonText: '取消',
    type: 'info',
  })
    .then(() => window.open(url, '_blank', 'noopener'))
    .catch(() => {})
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
        <el-table-column prop="color" label="颜色" width="100" />
        <el-table-column label="数量" width="100">
          <template #default="{ row }">
            <span v-if="row.type === 'accessory' && row.attachment">—</span>
            <span v-else>{{ row.quantity }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="70" />
        <el-table-column label="用布记录" min-width="260">
          <template #default="{ row }">
            <div v-if="row.type === 'dyed_fabric' && plansByColor(row.color).length" class="usage-list">
              <el-button
                v-for="plan in plansByColor(row.color).slice(0, 3)"
                :key="plan.id"
                link
                type="primary"
                size="small"
                @click="openPlan(plan.id)"
              >
                {{ plan.date }} · {{ plan.name }} · 用布{{ Number(plan.cloth_used || 0).toFixed(2) }}
              </el-button>
            </div>
            <span v-else class="muted">暂无</span>
          </template>
        </el-table-column>
        <el-table-column label="附件" width="120" align="center">
          <template #default="{ row }">
            <el-button
              v-if="row.attachment"
              type="primary"
              size="small"
              @click="openPreview(row)"
            >
              预览
            </el-button>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" align="center">
          <template #default="{ row }">
            <el-space :size="8" wrap>
              <el-button type="primary" size="small" @click="openEdit(row)">编辑</el-button>
              <el-button type="danger" size="small" @click="removeMaterial(row)">删除</el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card style="margin-top: 16px">
      <template #header><span>染色单</span></template>
      <el-table :data="dyeingOrders" size="small">
        <el-table-column prop="id" label="编号" width="90" />
        <el-table-column prop="output_name" label="染色布" />
        <el-table-column label="计划输出色" width="120">
          <template #default="{ row }">{{ row.output_color }}</template>
        </el-table-column>
        <el-table-column prop="quantity" label="数量" width="120" />
        <el-table-column prop="status" label="状态" width="120" />
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="物料入库" width="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="类型">
          <el-select v-model="form.type" style="width: 100%">
            <el-option label="坯布" value="raw_fabric" />
            <el-option label="染色布" value="dyed_fabric" />
            <el-option label="辅料" value="accessory" />
          </el-select>
        </el-form-item>
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item v-if="form.type !== 'accessory'" label="颜色"><el-input v-model="form.color" /></el-form-item>
        <el-form-item v-else label="颜色"><el-input v-model="form.color" placeholder="可选" /></el-form-item>
        <el-form-item v-if="form.type !== 'accessory'" label="数量">
          <el-input v-model.number="form.quantity" type="number" />
        </el-form-item>
        <el-form-item v-else label="数量">
          <el-input v-model.number="form.quantity" type="number" placeholder="登记用，可与附件并用" />
        </el-form-item>
        <el-form-item v-if="form.type === 'accessory'" label="附件" required>
          <el-upload
            :auto-upload="false"
            :limit="1"
            :on-change="onAttachmentPick"
            :on-remove="onAttachmentClear"
            accept=".pdf,.doc,.docx,.xlsx,.xls,image/*"
          >
            <el-button type="primary">选择文件</el-button>
            <template #tip>
              <div class="el-upload__tip">支持 PDF、Word、Excel、图片</div>
            </template>
          </el-upload>
        </el-form-item>
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

    <el-dialog v-model="editVisible" title="编辑物料" width="520px">
      <el-form v-if="editForm.id" :model="editForm" label-width="90px">
        <el-form-item label="类型">
          <el-tag>{{ typeLabelMap[editForm.type] || editForm.type }}</el-tag>
        </el-form-item>
        <el-form-item label="名称"><el-input v-model="editForm.name" /></el-form-item>
        <el-form-item label="颜色"><el-input v-model="editForm.color" /></el-form-item>
        <el-form-item label="数量"><el-input v-model.number="editForm.quantity" type="number" /></el-form-item>
        <el-form-item v-if="editForm.type === 'accessory'" label="新附件">
          <el-upload
            :auto-upload="false"
            :limit="1"
            :on-change="onEditAttachmentPick"
            :on-remove="onEditAttachmentClear"
            accept=".pdf,.doc,.docx,.xlsx,.xls,image/*"
          >
            <el-button>更换文件</el-button>
          </el-upload>
          <div v-if="editForm._attachmentUrl" class="muted small">当前有附件，可上传新文件覆盖</div>
        </el-form-item>
        <el-form-item label="单位"><el-input v-model="editForm.unit" /></el-form-item>
        <el-form-item label="供应商">
          <el-select v-model="editForm.supplier" clearable style="width: 100%">
            <el-option
              v-for="s in suppliers.filter((x) => x.type === supplierTypeMap[editForm.type])"
              :key="s.id"
              :label="s.name"
              :value="s.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="仓库">
          <el-select v-model="editForm.warehouse" clearable style="width: 100%">
            <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker
            v-model="editForm.stock_date"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="editForm.remark" type="textarea" rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="previewVisible" :title="previewTitle" width="720px" @closed="previewUrl = ''">
      <el-image v-if="previewUrl" :src="previewUrl" fit="contain" style="max-height: 70vh; width: 100%" />
    </el-dialog>

    <el-dialog v-model="dyeDialogVisible" title="新建染色单">
      <el-form :model="dyeForm" label-width="110px">
        <el-form-item label="坯布">
          <el-select v-model="dyeForm.raw_material_id" style="width: 100%">
            <el-option
              v-for="m in materials.filter((x) => x.type === 'raw_fabric')"
              :key="m.id"
              :label="`${m.name}(${m.quantity})`"
              :value="m.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="染厂">
          <el-select v-model="dyeForm.supplier_id" style="width: 100%">
            <el-option v-for="s in suppliers.filter((x) => x.type === '染厂')" :key="s.id" :label="s.name" :value="s.id" />
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
.material-management {
  padding: 16px 0;
}
.header-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.muted {
  color: var(--el-text-color-secondary);
}
.small {
  font-size: 12px;
  margin-top: 6px;
}
.usage-list {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}
</style>
