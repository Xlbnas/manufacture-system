# 工厂生产管理系统

## 项目概述

本系统是一个用于统计工厂生产情况的网站，包括工厂管理、原料管理、生产管理、出库管理和数据可视化等功能。

## 技术栈

- **后端**：Django + Django REST Framework
- **前端**：Vue 3 + Element Plus + ECharts
- **数据库**：SQLite

## 项目结构

```
Manufacture/
├── manufacture_backend/    # 后端Django项目
│   ├── manufacture_project/  # 项目配置
│   ├── production/           # 生产管理应用
│   ├── venv/                # 虚拟环境
│   └── manage.py            # 管理脚本
├── manufacture_frontend/   # 前端Vue项目
│   ├── src/                 # 源代码
│   ├── public/              # 静态资源
│   └── package.json         # 项目配置
└── README.md               # 项目说明
```

## 部署步骤

### 后端部署

1. **进入后端目录**
   ```bash
   cd manufacture_backend
   ```

2. **激活虚拟环境**
   ```bash
   venv\Scripts\Activate.ps1  # Windows PowerShell
   # 或
   venv\Scripts\activate      # Windows Command Prompt
   ```

3. **启动开发服务器**
   ```bash
   python manage.py runserver
   ```

4. **访问Django Admin后台**
   - 地址：http://127.0.0.1:8000/admin/
   - 用户名：Xlbnas
   - 密码：创建时设置的密码

### 前端部署

1. **进入前端目录**
   ```bash
   cd manufacture_frontend
   ```

2. **安装依赖**
   ```bash
   npm install
   ```

3. **启动开发服务器**
   ```bash
   npm run dev
   ```

4. **访问前端界面**
   - 地址：http://localhost:5173/

## 系统功能

### 1. 数据看板
- 生产进度统计图表
- 库存分布饼图
- 出库趋势折线图

### 2. 工厂管理
- 添加工厂和车间信息
- 查看工厂列表
- 删除工厂信息

### 3. 原料管理
- 添加辅料和面料
- 查看原料列表
- 删除原料信息

### 4. 生产管理
- 添加生产计划
- 更新生产进度
- 查看生产计划和进度列表
- 删除生产计划和进度信息

### 5. 出库管理
- 添加出库记录
- 查看出库记录列表
- 删除出库记录

## API接口

后端提供了以下API接口：

- **工厂管理**：/api/factories/
- **原料管理**：/api/materials/
- **产品管理**：/api/products/
- **生产计划**：/api/production-plans/
- **生产进度**：/api/production-progress/
- **出库记录**：/api/outbound-records/

## 注意事项

1. 本系统使用的是SQLite数据库，适合中小规模应用。
2. 开发环境下使用的是Django和Vite的开发服务器，生产环境需要使用专业的Web服务器。
3. 系统目前没有实现用户认证和权限控制，生产环境需要添加相关功能。

## 联系方式

如有问题，请联系系统管理员。
