<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth.js'

// 激活的标签页
const activeTab = ref('suppliers')

// 辅料商数据
const suppliers = ref([])
const supplierForm = ref({ name: '', type: '辅料' })
const supplierDialogVisible = ref(false)

// 布厂数据
const fabricFactories = ref([])
const fabricFactoryForm = ref({ name: '' })
const fabricFactoryDialogVisible = ref(false)

// 染厂数据
const dyeingFactories = ref([])
const dyeingFactoryForm = ref({ name: '' })
const dyeingFactoryDialogVisible = ref(false)

// 布料库存数据
const fabricInventory = ref([])
const fabricForm = ref({ name: '', composition: '', quantity: 0, unit: '米' })
const fabricDialogVisible = ref(false)

// 染色相关数据
const dyeingForm = ref({ fabricId: '', color: '', quantity: 0 })
const dyeingDialogVisible = ref(false)
const colors = ref([
  '军绿', '黑色', '白色', '红色', '蓝色', '黄色', '灰色', '紫色', '粉色', '橙色'
])

// 加载数据
const fetchSuppliers = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:9876/api/suppliers/')
    suppliers.value = response.data
  } catch (error) {
    console.error('Error fetching suppliers:', error)
  }
}

const fetchFabricFactories = async () => {
  // 从供应商数据中过滤出类型为'布料'的供应商作为布厂
  fabricFactories.value = suppliers.value.filter(supplier => supplier.type === '布料')
}

const fetchDyeingFactories = async () => {
  // 从供应商数据中过滤出类型为'面料'的供应商作为染厂
  dyeingFactories.value = suppliers.value.filter(supplier => supplier.type === '面料')
}

// 初始化认证
const authStore = useAuthStore()

// 获取布料库存
const fetchFabricInventory = async () => {
  // 从材料溯源模块获取布料数据
  try {
    const response = await axios.get('http://127.0.0.1:9876/api/materials/')
    fabricInventory.value = response.data.filter(item => item.type === '布料')
  } catch (error) {
    console.error('Error fetching fabric inventory:', error)
  }
}

onMounted(async () => {
  // 初始化认证
  await authStore.initAuth()
  // 加载数据
  fetchSuppliers()
  fetchFabricFactories()
  fetchDyeingFactories()
  fetchFabricInventory()
})

// 保存辅料商
const saveSupplier = async () => {
  try {
    await axios.post('http://127.0.0.1:9876/api/suppliers/', supplierForm.value)
    supplierDialogVisible.value = false
    fetchSuppliers()
    ElMessage.success('辅料商保存成功')
  } catch (error) {
    console.error('Error saving supplier:', error)
    ElMessage.error('保存失败：' + (error.message || '未知错误'))
  }
}

// 保存布厂
const saveFabricFactory = async () => {
  try {
    // 由于没有专门的布厂API，我们使用供应商API，类型设为'布料'
    const supplierData = {
      name: fabricFactoryForm.value.name,
      type: '布料'
    }
    await axios.post('http://127.0.0.1:9876/api/suppliers/', supplierData)
    fabricFactoryDialogVisible.value = false
    fetchSuppliers()
    fetchFabricFactories()
    ElMessage.success('布厂保存成功')
  } catch (error) {
    console.error('Error saving fabric factory:', error)
    ElMessage.error('保存失败：' + (error.message || '未知错误'))
  }
}

// 保存染厂
const saveDyeingFactory = async () => {
  try {
    // 由于没有专门的染厂API，我们使用供应商API，类型设为'面料'
    const supplierData = {
      name: dyeingFactoryForm.value.name,
      type: '面料'
    }
    await axios.post('http://127.0.0.1:9876/api/suppliers/', supplierData)
    dyeingFactoryDialogVisible.value = false
    fetchSuppliers()
    fetchDyeingFactories()
    ElMessage.success('染厂保存成功')
  } catch (error) {
    console.error('Error saving dyeing factory:', error)
    ElMessage.error('保存失败：' + (error.message || '未知错误'))
  }
}

// 删除辅料商
const deleteSupplier = async (id) => {
  if (confirm('确定要删除这个辅料商吗？')) {
    try {
      await axios.delete(`http://127.0.0.1:9876/api/suppliers/${id}/`)
      fetchSuppliers()
      ElMessage.success('辅料商删除成功')
    } catch (error) {
      console.error('Error deleting supplier:', error)
      ElMessage.error('删除失败：' + (error.message || '未知错误'))
    }
  }
}

// 删除布厂
const deleteFabricFactory = async (id) => {
  if (confirm('确定要删除这个布厂吗？')) {
    try {
      await axios.delete(`http://127.0.0.1:9876/api/suppliers/${id}/`)
      fetchSuppliers()
      fetchFabricFactories()
      ElMessage.success('布厂删除成功')
    } catch (error) {
      console.error('Error deleting fabric factory:', error)
      ElMessage.error('删除失败：' + (error.message || '未知错误'))
    }
  }
}

// 删除染厂
const deleteDyeingFactory = async (id) => {
  if (confirm('确定要删除这个染厂吗？')) {
    try {
      await axios.delete(`http://127.0.0.1:9876/api/suppliers/${id}/`)
      fetchSuppliers()
      fetchDyeingFactories()
      ElMessage.success('染厂删除成功')
    } catch (error) {
      console.error('Error deleting dyeing factory:', error)
      ElMessage.error('删除失败：' + (error.message || '未知错误'))
    }
  }
}

// 打开辅料商对话框
const openSupplierDialog = () => {
  supplierForm.value = { name: '', type: '辅料' }
  supplierDialogVisible.value = true
}

// 打开布厂对话框
const openFabricFactoryDialog = () => {
  fabricFactoryForm.value = { name: '' }
  fabricFactoryDialogVisible.value = true
}

// 打开染厂对话框
const openDyeingFactoryDialog = () => {
  dyeingFactoryForm.value = { name: '' }
  dyeingFactoryDialogVisible.value = true
}

// 打开添加布料对话框
const openFabricDialog = () => {
  fabricForm.value = { name: '', composition: '', quantity: 0, unit: '米' }
  fabricDialogVisible.value = true
}

// 打开染色对话框
const openDyeingDialog = () => {
  dyeingForm.value = { fabricId: '', color: '', quantity: 0 }
  dyeingDialogVisible.value = true
}

// 保存布料
const saveFabric = async () => {
  try {
    // 使用材料溯源的API添加布料
    const materialData = {
      type: '布料',
      name: fabricForm.value.name,
      quantity: Number(fabricForm.value.quantity) || 0,
      unit: fabricForm.value.unit || '米',
      supplier: null, // 可以根据需要选择供应商
      factory: null, // 可以根据需要选择工厂
      stock_date: new Date().toISOString().split('T')[0],
      remark: `成分: ${fabricForm.value.composition}`
    }
    await axios.post('http://127.0.0.1:9876/api/materials/', materialData)
    fabricDialogVisible.value = false
    fetchFabricInventory()
    ElMessage.success('布料添加成功')
  } catch (error) {
    console.error('Error saving fabric:', error)
    ElMessage.error('保存失败：' + (error.message || '未知错误'))
  }
}

// 执行染色操作
const performDyeing = async () => {
  try {
    // 获取选中的布料
    const selectedFabric = fabricInventory.value.find(fabric => fabric.id == dyeingForm.value.fabricId)
    if (!selectedFabric) {
      ElMessage.error('请选择要染色的布料')
      return
    }
    
    // 检查库存是否足够
    if (selectedFabric.quantity < dyeingForm.value.quantity) {
      ElMessage.error('库存不足')
      return
    }
    
    // 计算剩余库存
    const remainingQuantity = selectedFabric.quantity - dyeingForm.value.quantity
    
    // 更新原布料库存
    await axios.put(`http://127.0.0.1:9876/api/materials/${selectedFabric.id}/`, {
      quantity: remainingQuantity
    })
    
    // 创建染色后的面料
    const dyedFabricData = {
      type: '面料',
      name: `${selectedFabric.name}(${dyeingForm.value.color})`,
      quantity: Number(dyeingForm.value.quantity) || 0,
      unit: selectedFabric.unit,
      supplier: selectedFabric.supplier?.id || null,
      factory: selectedFabric.factory?.id || null,
      stock_date: new Date().toISOString().split('T')[0],
      remark: `原布料: ${selectedFabric.name}, 染色: ${dyeingForm.value.color}`
    }
    await axios.post('http://127.0.0.1:9876/api/materials/', dyedFabricData)
    
    // 刷新数据
    fetchFabricInventory()
    dyeingDialogVisible.value = false
    ElMessage.success('染色操作成功')
  } catch (error) {
    console.error('Error performing dyeing:', error)
    ElMessage.error('染色失败：' + (error.message || '未知错误'))
  }
}

// 删除布料
const deleteFabric = async (id) => {
  if (confirm('确定要删除这个布料吗？')) {
    try {
      await axios.delete(`http://127.0.0.1:9876/api/materials/${id}/`)
      fetchFabricInventory()
      ElMessage.success('布料删除成功')
    } catch (error) {
      console.error('Error deleting fabric:', error)
      ElMessage.error('删除失败：' + (error.message || '未知错误'))
    }
  }
}
</script>

<template>
  <div class="supplies-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>辅料面料管理</span>
        </div>
      </template>
      
      <el-tabs v-model="activeTab">
        <!-- 管理辅料商 -->
        <el-tab-pane label="辅料商管理" name="suppliers">
          <div style="margin-bottom: 20px;">
            <el-button type="primary" @click="openSupplierDialog">添加辅料商</el-button>
          </div>
          <el-table :data="suppliers.filter(s => s.type === '辅料')" style="width: 100%">
            <el-table-column prop="name" label="辅料商名称" width="200" />
            <el-table-column prop="type" label="类型" width="150" />
            <el-table-column label="操作" width="150" align="center">
              <template #default="scope">
                <el-button type="danger" size="small" @click="deleteSupplier(scope.row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        
        <!-- 管理布厂 -->
        <el-tab-pane label="布厂管理" name="fabric-factories">
          <div style="margin-bottom: 20px;">
            <el-button type="primary" @click="openFabricFactoryDialog">添加布厂</el-button>
          </div>
          <el-table :data="suppliers.filter(s => s.type === '布料')" style="width: 100%">
            <el-table-column prop="name" label="布厂名称" width="200" />
            <el-table-column label="操作" width="150" align="center">
              <template #default="scope">
                <el-button type="danger" size="small" @click="deleteFabricFactory(scope.row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        
        <!-- 管理染厂 -->
        <el-tab-pane label="染厂管理" name="dyeing-factories">
          <div style="margin-bottom: 20px;">
            <el-button type="primary" @click="openDyeingFactoryDialog">添加染厂</el-button>
          </div>
          <el-table :data="suppliers.filter(s => s.type === '面料')" style="width: 100%">
            <el-table-column prop="name" label="染厂名称" width="200" />
            <el-table-column label="操作" width="150" align="center">
              <template #default="scope">
                <el-button type="danger" size="small" @click="deleteDyeingFactory(scope.row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        
        <!-- 布料管理 -->
        <el-tab-pane label="布料管理" name="fabric-management">
          <div style="margin-bottom: 20px;">
            <el-button type="primary" @click="openFabricDialog">添加布料</el-button>
          </div>
          <el-table :data="fabricInventory" style="width: 100%">
            <el-table-column prop="name" label="布料名称" width="200" />
            <el-table-column label="成分" width="200">
              <template #default="scope">
                {{ scope.row.remark ? scope.row.remark.replace('成分: ', '') : '无' }}
              </template>
            </el-table-column>
            <el-table-column prop="quantity" label="数量" width="100" />
            <el-table-column prop="unit" label="单位" width="80" />
            <el-table-column prop="stock_date" label="入库日期" width="150" />
            <el-table-column label="操作" width="150" align="center">
              <template #default="scope">
                <el-button type="danger" size="small" @click="deleteFabric(scope.row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        
        <!-- 染色管理 -->
        <el-tab-pane label="染色管理" name="dyeing-management">
          <div style="margin-bottom: 20px;">
            <el-button type="primary" @click="openDyeingDialog">执行染色</el-button>
          </div>
          <el-table :data="fabricInventory.filter(f => f.quantity > 0)" style="width: 100%">
            <el-table-column prop="name" label="布料名称" width="200" />
            <el-table-column label="成分" width="200">
              <template #default="scope">
                {{ scope.row.remark ? scope.row.remark.replace('成分: ', '') : '无' }}
              </template>
            </el-table-column>
            <el-table-column prop="quantity" label="剩余数量" width="100" />
            <el-table-column prop="unit" label="单位" width="80" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 辅料商对话框 -->
    <el-dialog
      v-model="supplierDialogVisible"
      title="添加辅料商"
      width="500px"
    >
      <el-form :model="supplierForm" label-width="100px">
        <el-form-item label="辅料商名称">
          <el-input v-model="supplierForm.name" placeholder="输入辅料商名称" style="width: 100%" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="supplierForm.type" style="width: 100%">
            <el-option label="辅料" value="辅料" />
            <el-option label="面料" value="面料" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="supplierDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveSupplier">保存</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 布厂对话框 -->
    <el-dialog
      v-model="fabricFactoryDialogVisible"
      title="添加布厂"
      width="500px"
    >
      <el-form :model="fabricFactoryForm" label-width="100px">
        <el-form-item label="布厂名称">
          <el-input v-model="fabricFactoryForm.name" placeholder="输入布厂名称" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="fabricFactoryDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveFabricFactory">保存</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 染厂对话框 -->
    <el-dialog
      v-model="dyeingFactoryDialogVisible"
      title="添加染厂"
      width="500px"
    >
      <el-form :model="dyeingFactoryForm" label-width="100px">
        <el-form-item label="染厂名称">
          <el-input v-model="dyeingFactoryForm.name" placeholder="输入染厂名称" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dyeingFactoryDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveDyeingFactory">保存</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 布料添加对话框 -->
    <el-dialog
      v-model="fabricDialogVisible"
      title="添加布料"
      width="500px"
    >
      <el-form :model="fabricForm" label-width="100px">
        <el-form-item label="布料名称">
          <el-input v-model="fabricForm.name" placeholder="输入布料名称" style="width: 100%" />
        </el-form-item>
        <el-form-item label="成分">
          <el-input v-model="fabricForm.composition" placeholder="例如：80棉20涤" style="width: 100%" />
        </el-form-item>
        <el-form-item label="数量">
          <div style="display: flex; align-items: center;">
            <el-input v-model.number="fabricForm.quantity" type="number" style="width: 70%" />
            <el-input v-model="fabricForm.unit" placeholder="单位" style="width: 30%; margin-left: 10px" />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="fabricDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveFabric">保存</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 染色对话框 -->
    <el-dialog
      v-model="dyeingDialogVisible"
      title="执行染色"
      width="500px"
    >
      <el-form :model="dyeingForm" label-width="100px">
        <el-form-item label="选择布料">
          <el-select v-model="dyeingForm.fabricId" style="width: 100%" placeholder="选择要染色的布料">
            <el-option
              v-for="fabric in fabricInventory.filter(f => f.quantity > 0)"
              :key="fabric.id"
              :label="`${fabric.name} (${fabric.quantity}${fabric.unit})`"
              :value="fabric.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="选择颜色">
          <el-select v-model="dyeingForm.color" style="width: 100%" placeholder="选择颜色">
            <el-option
              v-for="color in colors"
              :key="color"
              :label="color"
              :value="color"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="染色数量">
          <el-input v-model.number="dyeingForm.quantity" type="number" style="width: 100%" placeholder="输入染色数量" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dyeingDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="performDyeing">执行染色</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.supplies-management {
  padding: 20px 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dialog-footer {
  width: 100%;
  display: flex;
  justify-content: flex-end;
}
</style>