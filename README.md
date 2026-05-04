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

在项目根目录：

```bash
docker compose build
docker compose up -d
```

- 前端：`http://localhost:5173`（Nginx 提供静态页，并把 `/api/`、`/media/` 转到后端或挂载目录）。
- 后端直连（调试）：`http://localhost:9876`。
- **数据持久化**：`docker-compose.yml` 将 `./manufacture_backend` 挂载到容器内 `/app`，因此 `db.sqlite3`、`media/`、`backups/` 均在宿主机 `manufacture_backend/` 下，与 VPS 路径一致，不依赖「仅本机可用」的路径。

容器启动命令会执行 `migrate` 后再启动 Gunicorn（超时 300s，避免 AI 长请求被 worker 杀死）。

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
- 主要资源：`factories`、`suppliers`、`warehouse-nodes`、`materials`、`dyeing-orders`、`weaving-orders`、`products`、`production-plans`、`production-plan-details`、`production-progress`、`warehouse`（成品库存）、`transfer-orders`；以及 `auth/me/`、`ai/*`、`system/backup/*`（备份仅超级管理员）。

## 功能一览（与界面模块对应）

- 数据看板、工厂管理、物料与供应商、外协（染色 / 布厂）、产品、生产计划与明细、成品库存与调拨、登录与权限、AI 总结（需配置 Key）、系统备份与恢复、深色模式与导出等。

**说明**：早期 README 中的「出库记录」独立模块已随模型迭代调整；以当前代码与 `PROJECT_STATUS.md` 为准。

## 文档维护约定

**每次合并或发布「重要功能」**（新模块、新 API、部署方式变更、认证/备份/外协等行为变化）时，请同步更新本 `README.md`（用户能跑通、能部署）；细节型字段与表结构可补充进 `PROJECT_STATUS.md`。

## 联系方式

如有问题，请联系系统管理员。
