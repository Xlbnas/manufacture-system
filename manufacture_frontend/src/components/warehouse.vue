<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import api from '../utils/axios'

const stocks = ref([])

function extractList(data) {
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.results)) return data.results
  return []
}

const load = async () => {
  const s = await api.get('/warehouse/')
  stocks.value = extractList(s.data)
}

/** 仅工厂仓 | 全部（工厂仓 + 本地仓） */
const inventoryScope = ref('factory')
/** 合并连续相同列（仓库 / 产品 / 颜色） */
const mergeCells = ref(true)

const factoryStocks = computed(() =>
  stocks.value.filter((x) => x.warehouse?.warehouse_type === 'factory')
)
const localStocks = computed(() =>
  stocks.value.filter((x) => x.warehouse?.warehouse_type === 'local')
)

const displayStocks = computed(() => {
  if (inventoryScope.value === 'all') return stocks.value
  return factoryStocks.value
})

function sortForMerge(rows) {
  return [...rows].sort((a, b) => {
    const wa = a.warehouse?.name ?? ''
    const wb = b.warehouse?.name ?? ''
    if (wa !== wb) return wa.localeCompare(wb, 'zh-CN')
    const ta = a.warehouse?.warehouse_type ?? ''
    const tb = b.warehouse?.warehouse_type ?? ''
    if (ta !== tb) return ta.localeCompare(tb)
    const pa = a.product?.name ?? ''
    const pb = b.product?.name ?? ''
    if (pa !== pb) return pa.localeCompare(pb, 'zh-CN')
    const ca = a.color ?? ''
    const cb = b.color ?? ''
    if (ca !== cb) return ca.localeCompare(cb, 'zh-CN')
    const sa = a.size ?? ''
    const sb = b.size ?? ''
    return sa.localeCompare(sb, 'zh-CN', { numeric: true })
  })
}

/** 表体行：带展示用扁平字段，便于 span-method */
const tableRows = computed(() =>
  sortForMerge(displayStocks.value).map((r) => ({
    ...r,
    _wh: r.warehouse?.name ?? '—',
    _tp: r.warehouse?.warehouse_type === 'local' ? '本地仓' : '工厂仓',
    _pr: r.product?.name ?? '—',
  }))
)

function computeStockSpans(rows) {
  const len = rows.length
  const wh = Array(len).fill(1)
  const pr = Array(len).fill(1)
  const co = Array(len).fill(1)
  if (!len) return { wh, pr, co }

  let i = 0
  while (i < len) {
    let j = i + 1
    while (j < len && rows[j]._wh === rows[i]._wh) j++
    wh[i] = j - i
    for (let k = i + 1; k < j; k++) wh[k] = 0

    let p = i
    while (p < j) {
      let q = p + 1
      while (q < j && rows[q]._pr === rows[p]._pr) q++
      pr[p] = q - p
      for (let k = p + 1; k < q; k++) pr[k] = 0

      let c = p
      while (c < q) {
        let d = c + 1
        while (d < q && rows[d].color === rows[c].color) d++
        co[c] = d - c
        for (let k = c + 1; k < d; k++) co[k] = 0
        c = d
      }
      p = q
    }
    i = j
  }
  return { wh, pr, co }
}

const spanPack = ref({ wh: [], pr: [], co: [] })

watch(
  tableRows,
  (rows) => {
    spanPack.value = computeStockSpans(rows)
  },
  { immediate: true, deep: true }
)

const mergedSpanMethod = ({ rowIndex, column }) => {
  if (!mergeCells.value) return [1, 1]
  const prop = column.property
  const pack = spanPack.value
  if (prop === '_wh') {
    const s = pack.wh[rowIndex] ?? 1
    return s > 0 ? [s, 1] : [0, 0]
  }
  if (prop === '_tp') {
    const s = pack.wh[rowIndex] ?? 1
    return s > 0 ? [s, 1] : [0, 0]
  }
  if (prop === '_pr') {
    const s = pack.pr[rowIndex] ?? 1
    return s > 0 ? [s, 1] : [0, 0]
  }
  if (prop === 'color') {
    const s = pack.co[rowIndex] ?? 1
    return s > 0 ? [s, 1] : [0, 0]
  }
  return [1, 1]
}

onMounted(load)
</script>

<template>
  <div class="warehouse-page">
    <el-card>
      <template #header>
        <div class="card-head">
          <span>成品库存</span>
          <div class="toolbar">
            <el-radio-group v-model="inventoryScope" size="small">
              <el-radio-button value="factory">仅工厂仓</el-radio-button>
              <el-radio-button value="all">全部库存（工厂仓 + 本地仓）</el-radio-button>
            </el-radio-group>
            <el-checkbox v-model="mergeCells" size="small">合并相同仓库 / 产品 / 颜色列</el-checkbox>
            <el-button size="small" @click="load">刷新</el-button>
          </div>
        </div>
      </template>
      <el-table
        :data="tableRows"
        size="small"
        border
        max-height="640"
        :span-method="mergedSpanMethod"
        empty-text="暂无库存数据"
      >
        <el-table-column prop="_wh" label="仓库" min-width="160" />
        <el-table-column v-if="inventoryScope === 'all'" prop="_tp" label="类型" width="88" />
        <el-table-column prop="_pr" label="产品" min-width="100" />
        <el-table-column prop="color" label="颜色" width="100" />
        <el-table-column prop="size" label="尺码" width="100" />
        <el-table-column prop="quantity" label="数量" width="100" align="right" />
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.warehouse-page {
  padding: 16px 0;
}
.card-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}
</style>
