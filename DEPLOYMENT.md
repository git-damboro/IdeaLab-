# 远程服务器部署指南

## 📋 部署流程概览

1. **上传项目文件到服务器**
2. **配置服务器环境（Docker、Python、Node.js）**
3. **配置环境变量**
4. **启动 Docker 服务（MongoDB、Milvus）**
5. **上传数据文件并执行导入**
6. **启动后端和前端服务**

---

## 步骤 1: 上传项目文件

### 需要上传的文件/目录：

```
agent-project-lxy/
├── app/                    # 后端代码（必须）
│   ├── backend.py
│   ├── etl_import.py      # 导入脚本（必须）
│   └── utils.py
├── frontend/               # 前端代码（必须）
│   ├── src/
│   ├── package.json
│   └── ...
├── data/                   # 数据文件目录（必须）
│   └── anthology+abstracts1.bib  # 你的 .bib 数据文件
├── docker-compose.yml      # Docker 配置（必须）
├── requirements.txt        # Python 依赖（必须）
├── .env                    # 环境变量（必须，但不要上传到 Git）
└── volumes/                # 数据卷目录（可选，会自动创建）
```

### 上传方式：

**方式1：使用 SCP（推荐）**
```bash
# 在本地执行
scp -r agent-project-lxy/ user@your-server-ip:/path/to/destination/
```

**方式2：使用 Git（如果代码在 Git 仓库）**
```bash
# 在服务器上执行
git clone your-repo-url
cd agent-project-lxy
```

**方式3：使用 FTP/SFTP 工具**
- FileZilla
- WinSCP
- VS Code Remote SSH

---

## 步骤 2: 配置服务器环境

### 2.1 安装 Docker 和 Docker Compose

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

### 2.2 安装 Python 3.8+ 和 pip

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip

# 验证
python3 --version
pip3 --version
```

### 2.3 安装 Node.js 16+ 和 npm

```bash
# 使用 NodeSource 仓库（推荐）
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 验证
node --version
npm --version
```

---

## 步骤 3: 配置环境变量

### 3.1 创建 .env 文件

在项目根目录创建 `.env` 文件：

```env
# MongoDB 连接配置（服务器上使用容器名或 localhost）
MONGO_URI=mongodb://lxystock:123456@localhost:27017/?authSource=admin

# Milvus 配置
MILVUS_HOST=localhost
MILVUS_PORT=19530

# 阿里云 API Key（用于 Embedding 和 AI 功能）
ALIBABA_API_KEY=your_api_key_here

# 导入策略（首次导入建议设为 true）
CLEAR_BEFORE_IMPORT=true
SKIP_EXISTING=true
```

**⚠️ 重要：**
- 如果 MongoDB 和 Milvus 在 Docker 容器中，使用 `localhost` 即可
- 如果使用远程数据库，修改相应的主机和端口
- 确保 `.env` 文件不会被提交到 Git（已在 .gitignore 中）

---

## 步骤 4: 启动 Docker 服务

```bash
# 进入项目目录
cd /path/to/agent-project-lxy

# 启动所有服务（MongoDB、Milvus、etcd、minio）
docker-compose up -d

# 等待服务启动（约30秒）
sleep 30

# 检查服务状态
docker-compose ps

# 应该看到所有服务都是 "Up" 状态
```

### 验证服务：

```bash
# 检查 MongoDB
docker logs research_mongo

# 检查 Milvus
docker logs milvus-standalone

# 检查所有服务日志
docker-compose logs
```

---

## 步骤 5: 安装依赖并执行数据导入

### 5.1 安装 Python 依赖

```bash
cd /path/to/agent-project-lxy

# 安装 Python 依赖
pip3 install -r requirements.txt

# 或者使用虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 5.2 确认数据文件位置

```bash
# 检查数据文件是否存在
ls -lh data/anthology+abstracts1.bib

# 如果文件在其他位置，修改 etl_import.py 中的路径
# 或创建软链接
ln -s /path/to/your/data.bib data/anthology+abstracts1.bib
```

### 5.3 执行数据导入

```bash
cd app

# 方式1：直接运行（推荐用于首次导入）
python3 etl_import.py

# 方式2：使用 nohup 后台运行（适合大批量导入）
nohup python3 etl_import.py > import.log 2>&1 &

# 查看导入进度
tail -f import.log

# 查看进程
ps aux | grep etl_import
```

**导入过程：**
- 会显示进度条和统计信息
- 如果中断，可以重新运行（已导入的数据会被跳过）
- 导入完成后会显示统计报告

### 5.4 验证导入结果

```bash
# 检查 MongoDB 中的数据量
docker exec -it research_mongo mongosh -u lxystock -p 123456 --authenticationDatabase admin
use research_db
db.papers.countDocuments()

# 检查 Milvus 中的数据量
# 访问 http://your-server-ip:8000 (Attu 可视化工具)
```

---

## 步骤 6: 启动后端服务

### 6.1 开发模式（测试用）

```bash
cd app
python3 backend.py
```

### 6.2 生产模式（推荐）

```bash
cd app

# 使用 uvicorn（支持多进程）
uvicorn backend:app --host 0.0.0.0 --port 8001 --workers 4

# 或使用 nohup 后台运行
nohup uvicorn backend:app --host 0.0.0.0 --port 8001 --workers 4 > backend.log 2>&1 &

# 查看日志
tail -f backend.log
```

### 6.3 使用 systemd 管理（推荐生产环境）

创建 `/etc/systemd/system/research-backend.service`：

```ini
[Unit]
Description=Research Backend Service
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/agent-project-lxy/app
Environment="PATH=/path/to/agent-project-lxy/venv/bin"
ExecStart=/path/to/agent-project-lxy/venv/bin/uvicorn backend:app --host 0.0.0.0 --port 8001 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable research-backend
sudo systemctl start research-backend
sudo systemctl status research-backend
```

---

## 步骤 7: 配置反向代理（Nginx）

**⚠️ 重要：反向代理配置应该在数据导入之后、启动服务之前完成**

### 7.1 安装 Nginx

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx

# CentOS/RHEL
sudo yum install nginx

# 启动并设置开机自启
sudo systemctl start nginx
sudo systemctl enable nginx
```

### 7.2 创建 Nginx 配置文件

创建配置文件 `/etc/nginx/sites-available/research-app`：

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名或服务器IP

    # 前端静态文件
    root /path/to/agent-project-lxy/frontend/dist;
    index index.html;

    # 前端路由（Vue Router）
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 反向代理后端 API
    location /api {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        
        # 请求头设置
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持（如果需要）
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置（推荐原因生成可能需要较长时间）
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 7.3 启用配置

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/research-app /etc/nginx/sites-enabled/

# 删除默认配置（可选）
sudo rm /etc/nginx/sites-enabled/default

# 测试配置
sudo nginx -t

# 如果测试通过，重新加载 Nginx
sudo systemctl reload nginx
```

### 7.4 配置 HTTPS（可选但推荐）

使用 Let's Encrypt 免费 SSL 证书：

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书（会自动配置 Nginx）
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

---

## 步骤 8: 构建前端并启动服务

### 8.1 安装依赖并构建前端

```bash
cd /path/to/agent-project-lxy/frontend

# 安装依赖
npm install

# 构建生产版本
npm run build

# 构建后的文件在 frontend/dist 目录
```

### 8.2 验证前端文件

```bash
# 检查构建结果
ls -lh frontend/dist/

# 应该看到 index.html 和其他静态文件
```

### 8.3 启动后端服务

```bash
cd /path/to/agent-project-lxy/app

# 使用 systemd 管理（推荐）
sudo systemctl start research-backend
sudo systemctl status research-backend

# 或使用 nohup（临时方案）
nohup uvicorn backend:app --host 0.0.0.0 --port 8001 --workers 4 > backend.log 2>&1 &
```

### 8.4 验证服务

```bash
# 检查后端是否运行
curl http://localhost:8001/docs

# 检查 Nginx 是否正常
curl http://localhost/api/docs

# 检查前端是否可访问
curl http://localhost/
```

### 7.3 或使用 PM2 运行开发服务器（不推荐生产环境）

```bash
npm install -g pm2
cd frontend
pm2 start npm --name "research-frontend" -- run dev
pm2 save
pm2 startup
```

---

## 步骤 9: 配置防火墙

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 8001/tcp    # 后端 API（如果直接暴露）
sudo ufw enable

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload
```

---

## 📋 完整部署顺序总结

**正确的部署顺序：**

1. ✅ **上传项目文件到服务器**
2. ✅ **安装服务器环境**（Docker、Python、Node.js、Nginx）
3. ✅ **配置环境变量**（.env 文件）
4. ✅ **启动 Docker 服务**（MongoDB、Milvus）
5. ✅ **安装 Python 依赖**
6. ✅ **执行数据导入**（这是关键步骤，必须在服务启动前完成）
7. ✅ **配置 Nginx 反向代理**（在导入之后，服务启动前）
8. ✅ **构建前端**
9. ✅ **启动后端服务**
10. ✅ **配置防火墙**
11. ✅ **验证部署**

**为什么反向代理要在导入之后？**
- 数据导入是初始化过程，不依赖 Web 服务
- 反向代理是服务配置，需要在服务启动前准备好
- 但可以在导入过程中并行配置，节省时间

---

## 🔍 验证部署

1. **检查后端 API**：
   ```bash
   curl http://localhost:8001/docs
   ```

2. **检查前端**：
   访问 `http://your-server-ip` 或 `http://your-domain.com`

3. **检查数据库连接**：
   查看后端日志，应该看到：
   ```
   ✅ MongoDB连接成功
   ✅ Milvus连接成功
   ```

---

## 📝 常见问题

### Q1: 导入过程中断怎么办？

**A:** 重新运行导入脚本即可，已导入的数据会被自动跳过（`SKIP_EXISTING=true`）。

### Q2: 如何查看导入进度？

**A:** 
```bash
# 如果使用 nohup
tail -f import.log

# 如果直接运行，会显示进度条
```

### Q3: 服务器内存不足怎么办？

**A:** 
- 减小 `batch_size`（在 `etl_import.py` 中）
- 增加服务器内存
- 分批导入数据

### Q4: 如何更新代码？

**A:**
```bash
# 如果使用 Git
git pull origin main

# 重启服务
sudo systemctl restart research-backend
sudo systemctl reload nginx
```

### Q5: 如何备份数据？

**A:**
```bash
# 备份 MongoDB
docker exec research_mongo mongodump -u lxystock -p 123456 --authenticationDatabase admin --out /backup

# 备份 Milvus（数据在 volumes/milvus_data）
tar -czf milvus_backup.tar.gz volumes/milvus_data/
```

---

## 🚀 快速部署脚本

创建 `deploy.sh`：

```bash
#!/bin/bash
set -e

echo "🚀 开始部署..."

# 1. 启动 Docker
echo "📦 启动 Docker 服务..."
docker-compose up -d
sleep 30

# 2. 安装依赖
echo "📥 安装 Python 依赖..."
pip3 install -r requirements.txt

# 3. 导入数据
echo "📚 开始导入数据..."
cd app
python3 etl_import.py

# 4. 启动后端
echo "🔧 启动后端服务..."
cd ..
cd app
nohup uvicorn backend:app --host 0.0.0.0 --port 8001 --workers 4 > backend.log 2>&1 &

# 5. 构建前端
echo "🎨 构建前端..."
cd ../frontend
npm install
npm run build

echo "✅ 部署完成！"
echo "后端日志: tail -f app/backend.log"
echo "访问: http://your-server-ip"
```

使用：
```bash
chmod +x deploy.sh
./deploy.sh
```

---

## 📞 需要帮助？

如果遇到问题，请检查：
1. Docker 服务是否正常运行
2. `.env` 文件配置是否正确
3. 端口是否被占用
4. 防火墙规则是否正确
5. 查看日志文件：`backend.log`、`import.log`

