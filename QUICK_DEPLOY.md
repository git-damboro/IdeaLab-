# 智能文献检索系统 — 快速部署指南

## 环境要求

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- 至少 4GB 内存（Milvus 需要）

---

## 第一步：启动基础设施

```bash
docker-compose up -d
```

等待约 30 秒，确认服务正常：

```bash
docker ps
```

应看到 4 个容器：`research_mongo`、`milvus-standalone`、`milvus-etcd`、`milvus-minio`。

---

## 第二步：配置环境变量

编辑 `.env`，确认以下内容（按实际修改）：

```ini
# 阿里云 DashScope API Key
ALIBABA_API_KEY=sk-你的key

# MongoDB
MONGO_URI=mongodb://lxystock:123456@localhost:27017/?authSource=admin

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530

# 默认管理员（首次启动自动创建，密码须6-16位且同时含字母和数字）
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```

> 如果不需要默认管理员，留空 ADMIN_USERNAME 和 ADMIN_PASSWORD 即可。

---

## 第三步：安装后端依赖

```bash
pip install -r requirements.txt
```

---

## 第四步：导入论文数据

```bash
cd app
python etl_import.py
```

此步骤会：
- 解析 `data/anthology+abstracts1.bib` 中的论文
- 写入 MongoDB
- 自动创建 Milvus 的 `paper_vectors` 集合 + 索引
- 调用 embedding 接口写入向量

> 首次导入耗时较长（取决于论文数量和 API 速度），请耐心等待。

---

## 第五步：启动后端

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

观察日志，应看到：
- `✅ MongoDB连接成功`
- `✅ 默认管理员已创建: admin，首次登录后请立即修改密码`（如果配了管理员）
- Milvus 连接成功（无 SchemaNotReadyException）

---

## 第六步：构建前端

**用户端：**

```bash
cd frontend
npm install
npm run build
```

**管理端：**

```bash
cd admin-frontend
npm install
npm run build
```

---

## 第七步：访问系统

| 入口 | 地址 |
|---|---|
| 用户端 | 由前端部署方式决定（开发模式：`npm run dev`，默认端口 5173） |
| 管理端 | 由前端部署方式决定（开发模式：`npm run dev`，默认端口 5174） |
| 后端 API | http://localhost:8001 |
| API 文档 | http://localhost:8001/docs |
| Milvus 可视化 | http://localhost:8000 |

---

## 开发模式快速启动

如果只是本地开发调试，后端启动后分别开两个终端跑前端即可：

```bash
# 终端1：用户端
cd frontend && npm install && npm run dev

# 终端2：管理端
cd admin-frontend && npm install && npm run dev
```

前端 dev 模式会自动代理 `/api` 请求到后端 8001 端口。

---

## 常见问题

### Milvus 连接失败

确认容器正常运行：`docker ps | grep milvus`。如果刚启动，等待 30 秒再试。

### 默认管理员未创建

检查 `.env` 中 ADMIN_USERNAME 和 ADMIN_PASSWORD 是否填写，密码是否符合策略（6-16位、必须同时含字母和数字、不能有特殊字符）。

### etl_import 报错 ALIBABA_API_KEY

确认 `.env` 中 ALIBABA_API_KEY 已填写且有效。

### 端口冲突

- MongoDB: 27017
- Milvus: 19530
- 后端: 8001
- 用户端: 5173
- 管理端: 5174
- Milvus Attu: 8000

如需修改，对应修改 `.env`、`docker-compose.yml` 或前端 `vite.config.js`。

---

## 停止服务

```bash
# 停止后端：Ctrl+C

# 停止 Docker 服务
docker-compose down

# 如需清除所有数据（重新部署）
docker-compose down -v
```
