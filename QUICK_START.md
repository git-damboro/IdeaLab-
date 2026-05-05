# 快速启动指南

## ⚠️ 重要：必须先启动 Docker 服务！

### 步骤 1：启动 Docker 服务

**Windows 用户：**
```bash
# 方式1：双击运行
start_docker.bat

# 方式2：命令行运行
docker-compose up -d
```

**等待约 30 秒让服务完全启动**

### 步骤 2：检查服务状态

```bash
# 检查 Docker 容器
docker-compose ps

# 应该看到以下服务：
# - research_mongo (MongoDB) - 状态应该是 "Up"
# - milvus-standalone (Milvus) - 状态应该是 "Up"
```

### 步骤 3：确认 .env 文件存在

项目根目录应该有 `.env` 文件，内容如下：

```env
MONGO_URI=mongodb://lxystock:123456@localhost:27017/?authSource=admin
MILVUS_HOST=localhost
MILVUS_PORT=19530
ALIBABA_API_KEY=your_api_key_here
```

### 步骤 4：启动后端服务

```bash
# 方式1：使用脚本
start_backend.bat

# 方式2：手动启动
cd app
python backend.py
```

**成功标志：** 后端控制台应该显示：
```
✅ MongoDB连接成功
✅ Milvus连接成功
```

### 步骤 5：启动前端服务

```bash
cd frontend
npm install  # 首次运行需要
npm run dev
```

## 🔧 故障排查

### 问题1：MongoDB 连接超时

**症状：** `localhost:27017: timed out`

**解决方案：**
1. 检查 Docker Desktop 是否运行
2. 检查 MongoDB 容器是否启动：
   ```bash
   docker ps | findstr mongo
   ```
3. 如果没有运行，启动 Docker：
   ```bash
   docker-compose up -d
   ```
4. 等待 30 秒后重试

### 问题2：找不到 .env 文件

**解决方案：**
1. 在项目根目录创建 `.env` 文件
2. 复制 `.env.example` 的内容（如果存在）
3. 或使用以下内容：
   ```env
   MONGO_URI=mongodb://lxystock:123456@localhost:27017/?authSource=admin
   MILVUS_HOST=localhost
   MILVUS_PORT=19530
   ALIBABA_API_KEY=your_api_key_here
   ```

### 问题3：Docker 容器启动失败

**解决方案：**
1. 检查端口是否被占用：
   - 27017 (MongoDB)
   - 19530 (Milvus)
2. 停止并重新启动：
   ```bash
   docker-compose down
   docker-compose up -d
   ```
3. 查看日志：
   ```bash
   docker-compose logs mongodb
   ```

### 问题4：后端启动但显示连接失败

**检查清单：**
- [ ] Docker Desktop 正在运行
- [ ] `.env` 文件存在且配置正确
- [ ] MongoDB 容器状态为 "Up"
- [ ] 端口 27017 未被其他程序占用

## 📝 完整启动命令序列

```bash
# 1. 启动 Docker（必须首先执行）
docker-compose up -d

# 2. 等待服务启动（约30秒）
timeout /t 30

# 3. 检查服务状态
docker-compose ps

# 4. 启动后端（新终端）
cd app
python backend.py

# 5. 启动前端（新终端）
cd frontend
npm run dev
```

## ✅ 验证服务正常运行

1. **MongoDB**: 访问 `http://localhost:27017` 应该无法访问（正常，MongoDB 不提供 HTTP 接口）
2. **后端 API**: 访问 `http://localhost:8001/docs` 应该看到 API 文档
3. **前端**: 访问 `http://localhost:5173` 应该看到登录页面

## 🆘 仍然有问题？

1. 运行诊断脚本：
   ```bash
   check_services.bat
   ```

2. 查看 Docker 日志：
   ```bash
   docker-compose logs
   ```

3. 检查后端日志中的错误信息




