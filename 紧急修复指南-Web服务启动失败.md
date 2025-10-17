# 紧急修复指南 - Web服务启动失败

> **问题**: `xiaozhi-esp32-server-web` 容器报错 `exec /start.sh: no such file or directory`

---

## 🔍 问题原因

1. **`/start.sh` 文件缺失**: Docker镜像中缺少启动脚本
2. **`.config.yaml` 未复制**: 隐藏的配置文件没有被打包

---

## ✅ 已修复内容

### 1. `.dockerignore` 文件
- ✅ 添加 `!docs/docker/` 确保构建脚本不被排除

### 2. 打包脚本（`offline-package.ps1` 和 `offline-package.sh`）
- ✅ 自动复制 `data` 目录下的所有隐藏配置文件
- ✅ 包括 `.config.yaml`, `.wakeup_words.yaml` 等

---

## 🚀 解决方案

### 方案A：重新打包并部署（推荐，30-40分钟）

#### 步骤1：清理并重新打包

```powershell
# 在Windows开发机上执行
cd D:\workspace\xiaozhi-esp32-server

# 1. 清理旧文件
.\scripts\clean-and-rebuild.ps1

# 2. 重新打包（使用修复后的脚本）
.\scripts\offline-package.ps1
```

#### 步骤2：传输新部署包

```bash
# 传输到CentOS服务器
scp xiaozhi-offline-deployment-*.tar.gz root@服务器IP:/root/
```

#### 步骤3：在CentOS上重新部署

```bash
# 1. 停止并清理旧容器
cd /home/app/xiaozhi-esp32-server/xiaozhi-offline-deployment-*/
docker-compose -f docker-compose-offline.yml down -v

# 2. 解压新部署包
cd /root
tar -xzf xiaozhi-offline-deployment-*.tar.gz
cd xiaozhi-offline-deployment-*/

# 3. 部署
chmod +x offline-deploy.sh
sudo ./offline-deploy.sh
```

---

### 方案B：手动修复现有部署（应急，10分钟）

如果重新打包时间太长，可以手动修复：

#### 步骤1：修复start.sh文件

```bash
# 在CentOS服务器上执行
cd /home/app/xiaozhi-esp32-server/xiaozhi-offline-deployment-*/

# 检查start.sh是否存在
ls -la docs/docker/start.sh

# 如果不存在，手动创建
mkdir -p docs/docker
cat > docs/docker/start.sh << 'EOF'
#!/bin/bash
# 启动Java后端（docker内监听8003端口）
java -jar /app/xiaozhi-esp32-api.jar \
  --server.port=8003 \
  --spring.datasource.druid.url=${SPRING_DATASOURCE_DRUID_URL} \
  --spring.datasource.druid.username=${SPRING_DATASOURCE_DRUID_USERNAME} \
  --spring.datasource.druid.password=${SPRING_DATASOURCE_DRUID_PASSWORD} \
  --spring.data.redis.host=${SPRING_DATA_REDIS_HOST} \
  --spring.data.redis.password=${SPRING_DATA_REDIS_PASSWORD} \
  --spring.data.redis.port=${SPRING_DATA_REDIS_PORT} &

# 启动Nginx（前台运行保持容器存活）
nginx -g 'daemon off;'
EOF

chmod +x docs/docker/start.sh
```

#### 步骤2：重新构建web镜像

```bash
# 重新加载web镜像（如果本地有web.tar）
cd images
docker load -i web.tar

# 或者从Windows重新传输web.tar
# scp images/web.tar root@服务器IP:/home/app/xiaozhi-esp32-server/xiaozhi-offline-deployment-*/images/
```

#### 步骤3：补充配置文件

```bash
cd /home/app/xiaozhi-esp32-server/xiaozhi-offline-deployment-*/

# 如果data目录下缺少.config.yaml，需要从开发机复制或手动创建
# 临时方案：检查config.yaml是否存在
ls -la data/config.yaml
ls -la data/.config.yaml

# 如果.config.yaml不存在但config.yaml存在，可以暂时不管
# 或者从开发机复制
```

#### 步骤4：重启服务

```bash
cd /home/app/xiaozhi-esp32-server/xiaozhi-offline-deployment-*/

# 停止现有容器
docker-compose -f docker-compose-offline.yml down

# 重新启动
docker-compose -f docker-compose-offline.yml up -d

# 查看日志
docker logs -f xiaozhi-esp32-server-web
```

---

### 方案C：仅重新打包web镜像（中间方案，15分钟）

如果只想修复web服务：

#### 在Windows上：

```powershell
cd D:\workspace\xiaozhi-esp32-server

# 只重新编译web镜像
docker build -t xiaozhi-esp32-server:web_custom -f .\Dockerfile-web .

# 导出web镜像
docker save xiaozhi-esp32-server:web_custom -o web.tar

# 传输到服务器
scp web.tar root@服务器IP:/home/app/xiaozhi-esp32-server/xiaozhi-offline-deployment-*/images/
```

#### 在CentOS上：

```bash
cd /home/app/xiaozhi-esp32-server/xiaozhi-offline-deployment-*/

# 加载新镜像
docker load -i images/web.tar

# 重启web服务
docker-compose -f docker-compose-offline.yml stop xiaozhi-esp32-server-web
docker-compose -f docker-compose-offline.yml up -d xiaozhi-esp32-server-web

# 查看日志
docker logs -f xiaozhi-esp32-server-web
```

---

## 🔍 验证修复

### 检查容器状态

```bash
docker ps | grep xiaozhi
```

应该看到4个容器都在运行。

### 检查Web服务日志

```bash
docker logs xiaozhi-esp32-server-web
```

应该看到类似：
```
Starting Java application...
Starting Nginx...
```

### 访问Web界面

```bash
# 本地测试
curl http://localhost:8002

# 浏览器访问
http://服务器IP:8002
```

---

## 📋 关于配置文件

### config.yaml vs .config.yaml

项目中有两个配置文件：

1. **`config.yaml`** - 主配置文件
   - 包含完整的服务配置
   - 位置：`main/xiaozhi-server/config.yaml`
   - 打包后：`data/config.yaml`

2. **`.config.yaml`** - 隐藏的补充配置
   - 通常包含特定环境的配置
   - 位置：`main/xiaozhi-server/data/.config.yaml`
   - 打包后：`data/.config.yaml`

### 如果缺少配置文件

如果部署后 `data/` 目录下缺少配置文件：

```bash
# 临时方案：从开发机复制
# 在Windows上
scp main\xiaozhi-server\config.yaml root@服务器IP:/home/app/xiaozhi-esp32-server/xiaozhi-offline-deployment-*/data/
scp main\xiaozhi-server\data\.config.yaml root@服务器IP:/home/app/xiaozhi-esp32-server/xiaozhi-offline-deployment-*/data/

# 重启server服务使配置生效
docker-compose -f docker-compose-offline.yml restart xiaozhi-esp32-server
```

---

## 🎯 推荐操作

### 对于生产环境：
**使用方案A** - 重新打包并完整部署，确保所有文件正确

### 对于测试环境：
**使用方案C** - 仅重新打包web镜像，快速修复

### 对于应急情况：
**使用方案B** - 手动修复，最快速度恢复服务

---

## 📞 后续检查

部署成功后，请检查：

1. ✅ 4个容器都在运行
2. ✅ 可以访问 http://服务器IP:8002
3. ✅ Web界面正常显示
4. ✅ 可以登录管理后台
5. ✅ `data/config.yaml` 存在
6. ✅ `data/.config.yaml` 存在（如果原项目有）

---

## 💡 预防措施

为避免以后再出现类似问题：

1. **始终使用最新的打包脚本**
2. **打包前检查 `.dockerignore` 配置**
3. **打包后验证部署包内容**:
   ```powershell
   # 解压后检查
   tar -tzf xiaozhi-offline-deployment-*.tar.gz | grep -E "(start.sh|config.yaml)"
   ```
4. **保持开发环境和部署环境的脚本同步**

---

需要帮助请查看完整文档：
- `docs/offline-deployment-guide.md`
- `docs/offline-deployment-troubleshooting.md`
- `换行符问题修复指南.md`

