# 项目部署教程（跨电脑可复用）

本文档用于把本项目交付到另一台电脑部署，包含两种方式：
- 方案 A：全新部署（不迁移历史数据）
- 方案 B：迁移历史数据（新电脑无需重新导入）

适用系统：Windows / macOS / Linux（以下命令以 Windows PowerShell 为主，其他系统命令等价）

---

## 1. 项目结构与服务说明

本项目包含 5 类服务：
1. 基础设施（Docker）
- `MongoDB`：业务数据
- `Milvus`：向量检索
- `etcd`、`minio`：Milvus 依赖
- `Attu`（可选）：Milvus 可视化

2. 后端 API（FastAPI）
- 启动入口：`app.main:app`
- 端口：`8001`

3. 用户前端（Vite + Vue）
- 目录：`frontend`
- 端口：`5173`

4. 管理前端（Vite + Vue）
- 目录：`admin-frontend`
- 端口：`5174`

5. 本地数据目录（非常关键）
- `volumes/mongo_data`：Mongo 持久化数据
- `volumes/milvus_data`：Milvus 持久化数据
- `data/uploads`：后台上传文件

---

## 2. 前置条件（新电脑）

请先安装：
1. `Git`
2. `Docker Desktop`（或 Docker Engine + Compose）
3. `Python 3.10+`
4. `Node.js 18+`（建议 Node 20 LTS）

检查版本（可选）：

```powershell
git --version
docker --version
docker compose version
python --version
node --version
npm --version
```

---

## 3. 交付给另一台电脑时，建议打包哪些内容

至少包含以下内容：
1. 代码目录（建议通过 Git 仓库）
2. `.env`（可从 `.env.example` 补齐）
3. 如果要迁移历史数据，还要带上：
- `volumes/mongo_data`
- `volumes/milvus_data`
- `data/uploads`

不建议传输：
- `frontend/node_modules`
- `admin-frontend/node_modules`
- `__pycache__`

---

## 4. 环境变量配置

在项目根目录创建或更新 `.env`：

```env
# 大模型 API Key
ALIBABA_API_KEY=your_api_key_here

# MongoDB
MONGO_URI=mongodb://lxystock:123456@localhost:27017/?authSource=admin

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530

# 可选：API 前缀（默认 /api/v1）
# API_V1_PREFIX=/api/v1
```

说明：
1. 如果后端与数据库在同一台机器，`localhost` 可保持默认。
2. 若数据库放在远程服务器，请改成远程地址。

---

## 5. 启动顺序（通用）

### Step 1) 启动 Docker 基础设施

在项目根目录执行：

```powershell
docker compose up -d
```

检查状态：

```powershell
docker compose ps
```

应看到以下容器为 `Up`：
- `research_mongo`
- `milvus-standalone`
- `milvus-etcd`
- `milvus-minio`
- `milvus-attu`（可选）

### Step 2) 启动后端

```powershell
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

健康检查：
- `http://localhost:8001/api/v1/health`
- `http://localhost:8001/docs`

### Step 3) 启动用户前端

新开终端：

```powershell
cd frontend
npm install
npm run dev
```

访问：`http://localhost:5173`

### Step 4) 启动管理前端

新开终端：

```powershell
cd admin-frontend
npm install
npm run dev
```

访问：`http://localhost:5174`

---

## 6. 方案 A：全新部署（不迁移历史数据）

适用于首次在新电脑上跑通项目。

流程：
1. 完成第 4、5 节操作。
2. 如需导入 Bib 数据，在项目根目录执行：

```powershell
python app/etl_import.py
```

说明：
- `etl_import.py` 默认读取 `data/anthology+abstracts1.bib`。
- 导入会写入 Mongo + Milvus。

---

## 7. 方案 B：迁移历史数据（推荐，避免重新导入）

目标：新电脑上线后直接使用旧数据。

### 7.1 在旧电脑导出

1. 停止容器，避免数据写入中复制导致不一致：

```powershell
docker compose down
```

2. 打包以下目录：
- `volumes/mongo_data`
- `volumes/milvus_data`
- `data/uploads`

3. 同时带上：
- 项目代码
- `.env`

### 7.2 在新电脑导入

1. 将上述目录放到新电脑项目相同位置。
2. 在项目根目录执行：

```powershell
docker compose up -d
```

3. 启动后端和前端（见第 5 节）。

### 7.3 验证迁移成功

1. 登录后检查历史账号是否存在。
2. 检查论文检索是否可直接返回结果。
3. 管理端检查 Jobs / Papers / Users 是否有历史记录。
4. 如有上传文件，验证下载或引用路径是否正常。

---

## 8. 快速联调清单（5 分钟）

按顺序验证：
1. `docker compose ps` 容器全 Up
2. `GET /api/v1/health` 返回 `{ "ok": true }`
3. 用户端可注册/登录/搜索
4. 管理端可登录并查看 Papers/Users/Jobs
5. Notes 页面可新增并再次读取

---

## 9. 常见问题与排查

### 9.1 后端启动报 Mongo 连接失败

排查：
1. `docker compose ps` 看 `research_mongo` 是否 Up
2. `.env` 的 `MONGO_URI` 账号密码是否与 `docker-compose.yml` 一致
3. 端口 `27017` 是否被占用

### 9.2 后端启动报 Milvus 连接失败

排查：
1. `milvus-standalone`、`milvus-etcd`、`milvus-minio` 是否 Up
2. `.env` 中 `MILVUS_HOST/MILVUS_PORT` 是否正确
3. 首次启动可等待 20-60 秒后再试

### 9.3 前端打不开或接口 404

排查：
1. 后端是否运行在 `8001`
2. 前端代理配置是否指向 `http://localhost:8001`
3. 浏览器开发者工具查看网络请求路径

### 9.4 换电脑后数据丢失

原因通常是未迁移以下目录：
- `volumes/mongo_data`
- `volumes/milvus_data`
- `data/uploads`

解决：补传目录后重启容器。

---

## 10. 停止与重启

停止全部 Docker 服务：

```powershell
docker compose down
```

仅重启基础设施：

```powershell
docker compose restart
```

后端/前端服务在各自终端 `Ctrl + C` 停止后重新执行启动命令即可。

---

## 11. 生产/长期运行建议（可选）

1. 把 Mongo/Milvus 放到固定服务器，不随开发机迁移。
2. 定期备份：
- `volumes/mongo_data`
- `volumes/milvus_data`
- `data/uploads`
3. 将 `.env` 中密钥通过安全方式分发，不放公开仓库。

---

## 12. 一键最短路径（给同事）

如果你只想把最短执行步骤发给同事：

```powershell
# 1) 在项目根目录
cp .env.example .env   # 若仓库有该文件；否则手工创建 .env

# 2) 启动基础设施
docker compose up -d

# 3) 启动后端
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 4) 启动用户前端（新终端）
cd frontend
npm install
npm run dev

# 5) 启动管理前端（新终端）
cd admin-frontend
npm install
npm run dev
```

访问：
- 用户端：`http://localhost:5173`
- 管理端：`http://localhost:5174`
- 后端文档：`http://localhost:8001/docs`
