# 工厂生产管理系统项目状态文档

## 1. 数据库结构设计

### 1.1 核心模型

#### Factory (工厂)
- `id`: 主键
- `name`: 工厂名称 (CharField, max_length=100)
- `location`: 地区 (CharField, max_length=100)
- `workshop`: 车间 (CharField, max_length=50)

#### Supplier (供应商)
- `id`: 主键
- `name`: 供应商名称 (CharField, max_length=100)
- `type`: 供应商类型 (CharField, max_length=10, choices=['辅料', '面料'])

#### Material (原料)
- `id`: 主键
- `type`: 原料类型 (CharField, max_length=10, choices=['辅料', '面料'])
- `name`: 原料名称 (CharField, max_length=100)
- `quantity`: 数量 (DecimalField, max_digits=10, decimal_places=2)
- `unit`: 单位 (CharField, max_length=10)
- `stock_date`: 入库日期 (DateField)
- `supplier`: 供应商 (ForeignKey to Supplier, nullable)
- `factory`: 目标工厂 (ForeignKey to Factory, nullable)
- `attachment`: 附件 (ImageField, upload_to='material_attachments/')

#### Product (产品)
- `id`: 主键
- `name`: 产品名称 (CharField, max_length=100, unique=True)
- `colors`: 颜色选项 (CharField, max_length=200, default='')
- `specifications`: 规格参数 (CharField, max_length=200, default='')

#### ProductionPlan (生产计划)
- `id`: 主键
- `product`: 产品 (ForeignKey to Product)
- `quantity`: 计划数量 (IntegerField)
- `start_date`: 开始日期 (DateField)
- `expected_end_date`: 预计结束日期 (DateField)

#### ProductionProgress (生产进度)
- `id`: 主键
- `plan`: 生产计划 (ForeignKey to ProductionPlan)
- `current_quantity`: 当前数量 (IntegerField)
- `status`: 状态 (CharField, max_length=10, choices=['进行中', '已完成', '暂停'])
- `update_time`: 更新时间 (DateTimeField, auto_now=True)

#### OutboundRecord (出库记录)
- `id`: 主键
- `product`: 产品 (ForeignKey to Product)
- `quantity`: 出库数量 (IntegerField)
- `outbound_date`: 出库日期 (DateField)
- `warehouse`: 仓库 (CharField, max_length=100)

#### Warehouse (仓库)
- `id`: 主键
- `product`: 产品 (ForeignKey to Product)
- `color`: 颜色 (CharField, max_length=50)
- `size`: 尺码 (CharField, max_length=20)
- `quantity`: 数量 (IntegerField)
- `factory`: 工厂 (ForeignKey to Factory)

## 2. 技术栈选型

### 2.1 前端技术
- **框架**: Vue 3 with Composition API
- **UI库**: Element Plus
- **HTTP客户端**: Axios
- **表格导出**: ExcelJS
- **构建工具**: Vite

### 2.2 后端技术
- **框架**: Django 6.0.3
- **API框架**: Django REST Framework
- **数据库**: SQLite (开发环境)
- **文件上传**: Pillow (处理图片附件)

### 2.3 其他工具
- **版本控制**: Git
- **开发环境**: Visual Studio Code

## 3. 核心业务逻辑流程

### 3.1 工厂管理
- 工厂信息的增删改查
- 支持批量车间输入
- 显示格式为"地区 车间"

### 3.2 原料管理
- 原料信息的增删改查
- 供应商管理
- 附件上传与管理（支持预览、下载、删除）
- 导出功能（支持导出带图片的Excel文件）

### 3.3 产品管理
- 产品信息的增删改查
- 颜色选项管理
- 规格参数管理（支持XS-5XL尺码选择）
- 导出功能（导出Excel文件）

### 3.4 生产计划与进度管理
- 生产计划的创建与管理
- 生产进度的实时更新与跟踪
- 状态管理（进行中、已完成、暂停）

### 3.5 仓库管理
- 库存信息的实时更新
- 支持按工厂、产品、颜色、尺码查询
- 与出库管理集成，自动更新库存

### 3.6 出库管理
- 多步骤选择出库产品
- 尺码选择与数量输入
- 库存验证
- 导出功能（支持合并相同日期的单元格）
- 清除记录功能（带备份导出）

## 4. 项目状态

### 4.1 已完成功能
- 工厂管理模块
- 原料管理模块（含供应商管理和附件管理）
- 产品管理模块
- 生产计划与进度管理模块
- 仓库管理模块
- 出库管理模块
- 所有模块的导出功能（导出Excel文件）
- 响应式设计
- 深色模式支持

### 4.2 待优化项
- 性能优化（大数据量处理）
- 权限管理
- 生产环境部署配置
- 单元测试

## 5. 关键文件结构

### 5.1 前端文件
- `src/components/`
  - `factory.vue` - 工厂管理组件
  - `material.vue` - 原料管理组件
  - `product.vue` - 产品管理组件
  - `production.vue` - 生产计划与进度管理组件
  - `warehouse.vue` - 仓库管理组件
  - `outbound.vue` - 出库管理组件
  - `dashboard.vue` - 仪表盘组件

### 5.2 后端文件
- `production/models.py` - 数据库模型定义
- `production/serializers.py` - API序列化器
- `production/views.py` - API视图
- `production/urls.py` - API路由

## 6. API端点

### 6.1 工厂相关
- `GET /api/factories/` - 获取工厂列表
- `POST /api/factories/` - 创建工厂
- `GET /api/factories/{id}/` - 获取工厂详情
- `PUT /api/factories/{id}/` - 更新工厂
- `DELETE /api/factories/{id}/` - 删除工厂

### 6.2 供应商相关
- `GET /api/suppliers/` - 获取供应商列表
- `POST /api/suppliers/` - 创建供应商
- `GET /api/suppliers/{id}/` - 获取供应商详情
- `PUT /api/suppliers/{id}/` - 更新供应商
- `DELETE /api/suppliers/{id}/` - 删除供应商

### 6.3 原料相关
- `GET /api/materials/` - 获取原料列表
- `POST /api/materials/` - 创建原料
- `GET /api/materials/{id}/` - 获取原料详情
- `PUT /api/materials/{id}/` - 更新原料
- `DELETE /api/materials/{id}/` - 删除原料

### 6.4 产品相关
- `GET /api/products/` - 获取产品列表
- `POST /api/products/` - 创建产品
- `GET /api/products/{id}/` - 获取产品详情
- `PUT /api/products/{id}/` - 更新产品
- `DELETE /api/products/{id}/` - 删除产品

### 6.5 生产计划相关
- `GET /api/production-plans/` - 获取生产计划列表
- `POST /api/production-plans/` - 创建生产计划
- `GET /api/production-plans/{id}/` - 获取生产计划详情
- `PUT /api/production-plans/{id}/` - 更新生产计划
- `DELETE /api/production-plans/{id}/` - 删除生产计划

### 6.6 生产进度相关
- `GET /api/production-progress/` - 获取生产进度列表
- `POST /api/production-progress/` - 创建生产进度
- `GET /api/production-progress/{id}/` - 获取生产进度详情
- `PUT /api/production-progress/{id}/` - 更新生产进度
- `DELETE /api/production-progress/{id}/` - 删除生产进度

### 6.7 出库记录相关
- `GET /api/outbound-records/` - 获取出库记录列表
- `POST /api/outbound-records/` - 创建出库记录
- `GET /api/outbound-records/{id}/` - 获取出库记录详情
- `PUT /api/outbound-records/{id}/` - 更新出库记录
- `DELETE /api/outbound-records/{id}/` - 删除出库记录

### 6.8 仓库相关
- `GET /api/warehouse/` - 获取仓库列表
- `POST /api/warehouse/` - 创建仓库记录
- `GET /api/warehouse/{id}/` - 获取仓库记录详情
- `PUT /api/warehouse/{id}/` - 更新仓库记录
- `DELETE /api/warehouse/{id}/` - 删除仓库记录
