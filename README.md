# 工厂生产管理系统

## 项目概述

面向工厂生产与库存的 Web 系统：工厂与仓库主数据、物料（坯布 / 染色布 / 辅料）、外协染色单与布厂单、产品、生产计划与明细、成品库存、调拨、数据看板、JWT 登录、可选 AI 总结、超级管理员系统备份等。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Django 6 + Django REST Framework + SimpleJWT + Gunicorn |
| 前端 | Vue 3 + Element Plus + ECharts + Vite |
| 数据库 | SQLite（`manufacture_backend/db.sqlite3`，适合中小规模；Docker/VPS 请持久化该文件与 `media/`） |

## 仓库结构

```
manufacture_backend/     # Django 项目（manage.py、production 应用、SQLite、media）
manufacture_frontend/    # Vue 3 前端（生产构建由 Nginx 提供静态资源并反代 /api）
docker-compose.yml       # 本地与服务器一键编排（backend + frontend）
PROJECT_STATUS.md        # 数据模型与 API 端点参考（偏技术细节）
```

## 本地开发（非 Docker）

1. **后端**（建议使用 `manufacture_backend/.venv`）  
   ```bash
   cd manufacture_backend
   python -m venv .venv && . .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env   # 按需填写 SILICONFLOW_* 等
   python manage.py migrate
   python manage.py runserver 0.0.0.0:8000
   ```
   管理后台：`http://127.0.0.1:8000/admin/`（需先 `createsuperuser`）。

2. **前端**  
   ```bash
   cd manufacture_frontend
   npm install
   npm run dev
   ```
   默认 `http://localhost:5173`，Vite 将 `/api` 代理到 `http://127.0.0.1:9876`（见 `vite.config.js`）。若后端端口不同，请改代理目标或在前端 `.env` 中设置 `VITE_API_BASE_URL`。

3. **演示数据**（可选）  
   ```bash
   cd manufacture_backend && . .venv/bin/activate
   python manage.py seed_demo_data          # 首次写入
   python manage.py seed_demo_data --force  # 覆盖已有【演示】数据
   ```

4. **自动化测试**  
   ```bash
   cd manufacture_backend && . .venv/bin/activate
   python manage.py test production.tests.test_functional_api -v 2
   ```

## Docker 部署（本地验证与 VPS 一致）

在项目根目录 **构建并启动**（日常改代码后发版同样使用）：

```bash
docker compose build
docker compose up -d
```

需要彻底重编镜像时：`docker compose build --no-cache`。

- 前端：`http://localhost:5173`（Nginx 提供静态页，并把 `/api/`、`/media/` 转到后端或挂载目录）。
- 后端直连（调试）：`http://localhost:9876`。
- **数据持久化**：`docker-compose.yml` 将 `./manufacture_backend` 挂载到容器内 `/app`，因此 `db.sqlite3`、`media/`、`backups/` 均在宿主机 `manufacture_backend/` 下，与 VPS 路径一致，不依赖「仅本机可用」的路径。

容器启动命令会执行 `migrate` 后再启动 Gunicorn（超时 300s，避免 AI 长请求被 worker 杀死）。

## 外协与物料业务链路（简）

与本系统衔接的典型顺序（「材料溯源」「外协订单」「生产管理」）：

1. **布厂外协**：坯布单登记到货 → 坯布进入库存。  
2. **下染色单**：按约定产量 **扣减** 所选坯布库存（视为坯布已寄染厂）。  
3. **染色到货**：增加染色布库存、累加本单已收；**不再**重复扣坯布。  
4. **删除染色单**：仅当尚无到货记录时可删，并 **退回** 建单时扣除的坯布数量。  
5. **删除布厂单**：与染色单一致——尚无到货、`received_quantity` 为 0 时可删；已有到货记录则不可删（需线下冲账再在材料页调整）。  
6. **染色收尾记损耗**：当实际交货率低于约定量时，`POST /api/dyeing-orders/{id}/close-with-loss/` 将「约定 − 已收」记入 `lost_quantity` 并 **关单**；建单时已扣坯布不会因损耗回补。关单后不可再登记到货。  

口径上只区分 **计划量 / 已到货量**（不要求单独「在途」字段）。

## 生产计划：两套模型与模板成品

| 用途 | API / 模型 | 说明 |
|------|--------------|------|
| 看板粗计划 | `production-plans`、`production-progress` | 每条粗计划仍关联一条 `Product`（应与排产所用模板线一致）；**与排产明细无自动汇总**。 |
| 日常排产表 | `production-plan-details` | 尺码矩阵、客户、用料等；`template` 字段与生产页模板 radio 取值一致。 |

**模板即产品**：成品库存与调拨外键仍指向 `Product`，但每条 `Product` 必须带 **唯一** 的 `production_template_key`（与前端 `productionTemplates` 常量一致）。排产明细不再单独存「成品外键」；**完工入库**（`POST .../complete-production/`）只按当前排产的 `template` 解析对应 `Product` 并入账。**库存 SKU** 语义为：模板键 + 颜色 + 尺码。缺产品行时可执行 `python manage.py sync_template_products` 或 `POST /api/products/sync-from-catalog/`。前端 **模板成品** 页按模板键维护显示名与颜色/尺码提示。默认入库仓为该排产目标工厂的工厂仓，也可传 `warehouse_id`。

染色布、辅料到工厂后的裁床车缝及后续环节 **不在本系统管理范围**，由线下衔接；仅在排产上做「到货齐」「完工入库」记账。

## 部署到 VPS 检查清单

1. **环境变量**（参考 `manufacture_backend/.env.example`）  
   - `SECRET_KEY`：强随机字符串，勿使用仓库默认值。  
   - `DEBUG=False`  
   - `ALLOWED_HOSTS`：你的域名或公网 IP，**并包含** `backend`（前端容器反代使用服务名访问后端）。示例：  
     `your-domain.com,www.your-domain.com,backend,127.0.0.1`  
   - `CORS_ALLOWED_ORIGINS`：浏览器实际访问前端的完整 Origin，逗号分隔。示例：  
     `https://your-domain.com`  
   - 若前端为 **HTTPS**，设置 `CSRF_TRUSTED_ORIGINS`（与上同源的 `https://...` 列表），否则浏览器可能对部分请求拦截 CSRF。

2. **不要在生产挂载整仓源码**（可选优化）：当前 compose 为便于热更新挂载了 `./manufacture_backend`；若仅部署镜像，请为 `db.sqlite3` 与 `media` 使用 **具名卷或宿主机目录卷**，避免数据库进镜像层。

3. **HTTPS**：生产建议在容器外使用 Caddy / Nginx 终止 TLS，再反代到 `5173`；或将 compose 改为仅监听内网再由边缘代理。

4. **备份**：系统内「系统备份」需超级管理员；另请定期拷贝宿主机上的 `db.sqlite3` 与 `media/`。

## API 与认证

- 路由前缀：`/api/`（见 `manufacture_backend/production/urls.py`）。  
- 默认 **JWT**：`POST /api/token/` 获取 access/refresh；请求头 `Authorization: Bearer <access>`。  
- 主要资源：`factories`、`suppliers`、`warehouse-nodes`、`materials`、`dyeing-orders`（含 `receipts/`、`complete/`、`close-with-loss/`）、`weaving-orders`、`products`（含 `sync-from-catalog/` 补全模板线）、`production-plans`、`production-plan-details`（含 `complete-production/`）、`production-progress`、`warehouse`（成品库存）、`transfer-orders`；以及 `auth/me/`、`ai/*`、`system/backup/*`（备份仅超级管理员）。

## 功能一览（与界面模块对应）

- 数据看板、工厂管理、物料与供应商、外协（染色 / 布厂）、模板成品（按排产模板键维护成品档案）、生产计划与明细、成品库存与调拨、登录与权限、AI 总结（需配置 Key）、系统备份与恢复、深色模式与导出等。

**说明**：早期 README 中的「出库记录」独立模块已随模型迭代调整；以当前代码与 `PROJECT_STATUS.md` 为准。

## 文档维护约定

**每次合并或发布「重要功能」**（新模块、新 API、部署方式变更、认证/备份/外协等行为变化）时，请同步更新本 `README.md`（用户能跑通、能部署）；细节型字段与表结构可补充进 `PROJECT_STATUS.md`。

## 联系方式

如有问题，请联系系统管理员。
