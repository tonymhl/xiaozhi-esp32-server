# Web 镜像快速修复方案对比

## 🎯 问题现状

当前 web 容器报错：
```
exec /start.sh: no such file or directory
```

**原因**：镜像中缺少 `start.sh` 和 `nginx.conf` 文件

---

## 📊 两个方案对比

| 项目 | 方案1：volume 挂载 | 方案2：重新打包镜像 |
|------|-------------------|-------------------|
| **耗时** | 2-3 分钟 | 10-15 分钟 |
| **需要 Windows 操作** | ❌ 否 | ✅ 是 |
| **需要传输文件** | ❌ 否（2 个小文件） | ✅ 是（1-2GB） |
| **Docker 最佳实践** | ✅ 配置外置 | ⚠️ 配置内置 |
| **后续维护** | ✅ 易于修改配置 | ⚠️ 需重建镜像 |
| **风险** | 低 | 低 |
| **推荐度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

---

## ✅ 推荐：方案1 - volume 挂载（最快）

### 为什么推荐这个方案？

1. ⚡ **极快**：2-3 分钟完成，无需重新构建
2. 🎯 **灵活**：后续修改 nginx 配置或启动脚本，只需编辑文件后重启容器
3. 📦 **小巧**：只需创建 2 个文本文件
4. 🔧 **最佳实践**：配置文件本就应该通过 volume 挂载

### 操作步骤（在 CentOS 上）

#### 步骤1：准备配置文件（2分钟）

```bash
# 进入部署目录
cd ~/xiaozhi-offline-deployment-*/

# 创建配置目录
mkdir -p docker-config

# 创建 start.sh
cat > docker-config/start.sh << 'EOF'
#!/bin/bash
set -e

echo "Starting Xiaozhi ESP32 Web Service..."

# 启动 Java 后端
echo "Starting Java backend..."
cd /app/backend
nohup java -jar xiaozhi-*.jar > /var/log/backend.log 2>&1 &

# 等待后端启动
echo "Waiting for backend to start..."
sleep 10

# 启动 Nginx
echo "Starting Nginx..."
nginx -g 'daemon off;'
EOF

# 创建 nginx.conf
cat > docker-config/nginx.conf << 'EOF'
user  nginx;
worker_processes  auto;
error_log  /var/log/nginx/error.log warn;
pid        /var/run/nginx.pid;

events {
    worker_connections  1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;
    sendfile        on;
    keepalive_timeout  65;
    gzip  on;

    server {
        listen       8002;
        server_name  localhost;

        # Vue 前端
        location / {
            root   /app/frontend;
            index  index.html;
            try_files $uri $uri/ /index.html;
        }

        # Java 后端 API
        location /xiaozhi/ {
            proxy_pass http://localhost:8002/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

# 设置权限和换行符
chmod +x docker-config/start.sh
sed -i 's/\r$//' docker-config/start.sh
sed -i 's/\r$//' docker-config/nginx.conf

echo "✓ 配置文件准备完成"
ls -lh docker-config/
```

#### 步骤2：修改 docker-compose（1分钟）

```bash
# 备份原文件
cp docker-compose-offline.yml docker-compose-offline.yml.backup

# 编辑文件
vi docker-compose-offline.yml
```

找到 `xiaozhi-esp32-server-web` 服务，在 `volumes` 部分添加两行：

```yaml
  xiaozhi-esp32-server-web:
    image: xiaozhi-esp32-server:web_custom
    container_name: xiaozhi-esp32-server-web
    restart: always
    networks:
      - default
    depends_on:
      xiaozhi-esp32-server-db:
        condition: service_healthy
      xiaozhi-esp32-server-redis:
        condition: service_healthy
    ports:
      - "8002:8002"
    environment:
      - TZ=Asia/Shanghai
      - SPRING_DATASOURCE_DRUID_URL=jdbc:mysql://xiaozhi-esp32-server-db:3306/xiaozhi_esp32_server?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai&nullCatalogMeansCurrent=true&connectTimeout=30000&socketTimeout=30000&autoReconnect=true&failOverReadOnly=false&maxReconnects=10
      - SPRING_DATASOURCE_DRUID_USERNAME=root
      - SPRING_DATASOURCE_DRUID_PASSWORD=123456
      - SPRING_DATA_REDIS_HOST=xiaozhi-esp32-server-redis
      - SPRING_DATA_REDIS_PASSWORD=
      - SPRING_DATA_REDIS_PORT=6379
    volumes:
      # 原有的 volume
      - ./uploadfile:/uploadfile
      # 新增：挂载启动脚本和 Nginx 配置
      - ./docker-config/start.sh:/start.sh:ro
      - ./docker-config/nginx.conf:/etc/nginx/nginx.conf:ro
```

保存并退出（`:wq`）

#### 步骤3：重启 web 容器（1分钟）

```bash
# 停止并删除 web 容器（保留镜像）
docker-compose -f docker-compose-offline.yml stop xiaozhi-esp32-server-web
docker-compose -f docker-compose-offline.yml rm -f xiaozhi-esp32-server-web

# 重新启动
docker-compose -f docker-compose-offline.yml up -d xiaozhi-esp32-server-web

# 查看日志（应该不再有 start.sh 错误）
docker logs -f xiaozhi-esp32-server-web
```

#### 预期结果

✅ 不再看到 `exec /start.sh: no such file or directory`  
✅ 看到 Nginx 和 Java 服务启动日志  
✅ 能够访问 http://服务器IP:8002

---

## 🔄 备选：方案2 - 重新打包镜像

如果您更喜欢"一劳永逸"地将文件打包进镜像：

### 在 Windows 上操作

```powershell
# 进入项目目录
cd D:\workspace\xiaozhi-esp32-server

# 执行快速打包脚本
.\scripts\rebuild-web-only.ps1
```

**耗时**：约 10-15 分钟

### 传输到 CentOS

```powershell
# 传输整个目录
scp -r web-image-* root@10.80.127.51:/root/
```

### 在 CentOS 上更新

```bash
# 进入上传的目录
cd /root/web-image-*/

# 转换脚本换行符
sed -i 's/\r$//' update-web-image.sh

# 添加执行权限
chmod +x update-web-image.sh

# 进入部署目录
cd ~/xiaozhi-offline-deployment-*/

# 复制镜像文件
cp /root/web-image-*/web.tar ./images/
cp /root/web-image-*/web.tar.md5 ./images/

# 执行更新
/root/web-image-*/update-web-image.sh
```

---

## 🎯 我的建议

**强烈推荐方案1（volume 挂载）**，因为：

### ✅ 方案1的优势

1. **极快**：2-3 分钟完成 vs 10-15 分钟
2. **简单**：只在 CentOS 上操作，不需要 Windows
3. **灵活**：后续可以随时修改配置文件
4. **符合 Docker 最佳实践**：
   - 配置文件应该外置
   - 镜像应该是不可变的
   - 方便配置管理和版本控制

### 🔧 后续维护示例（方案1）

如果以后需要修改 Nginx 配置：

```bash
# 直接编辑文件
vi ~/xiaozhi-offline-deployment-*/docker-config/nginx.conf

# 重启容器生效
docker-compose -f docker-compose-offline.yml restart xiaozhi-esp32-server-web
```

**无需重新构建镜像！**

---

## ⚠️ 常见问题

### Q1: volume 挂载会影响性能吗？

**A**: 不会。volume 挂载的性能开销可以忽略不计，尤其是只读挂载（`:ro`）。

### Q2: 两个方案可以同时用吗？

**A**: 可以！volume 挂载会覆盖镜像中的文件。即使镜像中有 start.sh，挂载的版本会优先使用。

### Q3: 如果方案1失败了怎么办？

**A**: 可以随时切换到方案2。两个方案互不影响。

### Q4: 方案1是否适用于生产环境？

**A**: 是的！许多生产环境都使用 volume 挂载配置文件，这是 Docker 的最佳实践。

---

## 📝 总结

| 场景 | 推荐方案 |
|------|----------|
| 快速修复当前问题 | ✅ 方案1（2-3分钟）|
| 后续需要经常调整配置 | ✅ 方案1（灵活）|
| 希望一劳永逸 | 方案2（10-15分钟）|
| 追求 Docker 最佳实践 | ✅ 方案1 |
| 没有 Windows 环境 | ✅ 方案1（只需 CentOS）|

**建议**：先尝试方案1，如果有任何问题，再考虑方案2。

---

## 🚀 立即开始

推荐您现在就在 CentOS 上执行方案1：

```bash
# 一键执行（复制整个命令块）
cd ~/xiaozhi-offline-deployment-*/ && \
mkdir -p docker-config && \
cat > docker-config/start.sh << 'EOF'
#!/bin/bash
set -e
echo "Starting Xiaozhi ESP32 Web Service..."
cd /app/backend
nohup java -jar xiaozhi-*.jar > /var/log/backend.log 2>&1 &
echo "Waiting for backend to start..."
sleep 10
echo "Starting Nginx..."
nginx -g 'daemon off;'
EOF
chmod +x docker-config/start.sh && \
sed -i 's/\r$//' docker-config/start.sh && \
echo "✓ start.sh 创建完成，现在请创建 nginx.conf 并修改 docker-compose-offline.yml"
```

然后按照上面的步骤2和步骤3完成！

