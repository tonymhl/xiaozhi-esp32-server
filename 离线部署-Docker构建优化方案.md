# 小智ESP32服务器 - Docker构建优化方案

> 本文档详细说明项目Docker构建方式的变化、问题分析及优化方案

---

## 📊 Docker构建方式变化分析

### 🔄 **项目作者的两阶段构建策略**

项目引入了基础镜像+生产镜像的分离构建方式：

#### **1. Dockerfile-server-base（基础镜像）**
```dockerfile
FROM python:3.10-slim
# 安装系统依赖（libopus0, ffmpeg）
# 安装Python包（requirements.txt）
# 优点：重量级依赖单独构建，很少更新，可复用
```

#### **2. Dockerfile-server（生产镜像）**
```dockerfile
FROM ghcr.io/xinnan-tech/xiaozhi-esp32-server:server-base
# 仅复制应用代码
# 优点：快速构建，适合频繁迭代
```

### ❌ **当前Dockerfile-server存在的问题**

1. **依赖远程镜像**
   - `FROM ghcr.io/xinnan-tech/xiaozhi-esp32-server:server-base`
   - 离线环境无法访问此镜像仓库

2. **重复安装依赖**
   - 第15-18行又安装了PyTorch等依赖
   - 违背两阶段分离原则，导致镜像臃肿

3. **多阶段构建错误**
   - 第32行：`COPY --from=builder ...`
   - 但未定义`builder`阶段，会导致构建失败

4. **结构混乱**
   - 同时使用base镜像引用和多阶段构建
   - 逻辑冲突，不符合最佳实践

---

## 🎯 优化方案对比

### **方案A：自包含离线构建（推荐）** ⭐

**特点：**
- ✅ 单一Dockerfile，不依赖远程镜像
- ✅ 适合离线环境，一次构建包含所有内容
- ✅ 简单可靠，易于维护
- ⚠️ 镜像较大（约3-5GB）

**适用场景：**
- 离线部署环境
- 不频繁重新构建镜像
- 追求构建稳定性

**文件：** `Dockerfile-server-offline`

---

### **方案B：本地两阶段构建**

**特点：**
- ✅ 基础镜像和应用镜像分离
- ✅ 应用镜像快速构建（约1-2分钟）
- ⚠️ 需要先构建base镜像
- ⚠️ 管理两个Dockerfile，稍复杂

**适用场景：**
- 频繁开发迭代
- 有网络环境（可拉取依赖）
- 追求构建速度

**实施步骤：**
```bash
# 1. 构建基础镜像（首次或依赖更新时）
docker build -t xiaozhi-esp32-server:server-base -f Dockerfile-server-base .

# 2. 修改Dockerfile-server第2行
FROM xiaozhi-esp32-server:server-base  # 使用本地base镜像

# 3. 构建应用镜像
docker build -t xiaozhi-esp32-server:server_custom -f Dockerfile-server .
```

---

## 🛠️ 方案A实施（推荐）

### **1. 使用新的Dockerfile-server-offline**

已为您创建 `Dockerfile-server-offline`，特点：
- 自包含，不依赖远程镜像
- 优化了pip配置（国内镜像源）
- 明确的分阶段安装（先PyTorch，再其他依赖）
- 设置时区和暴露端口

### **2. 更新的打包脚本功能**

`scripts/offline-package.ps1` 已优化：

✅ **新增功能：**
1. 自动检测 `Dockerfile-server-offline`，优先使用
2. 复制 `memory` 模块（支持热更新）
3. 复制 `intent` 模块（支持热更新）
4. 复制 `docker-config` 配置文件
5. 创建 `redis/data` 目录

✅ **构建逻辑：**
```powershell
if (Test-Path ".\Dockerfile-server-offline") {
    # 使用离线专用Dockerfile
    docker build -t xiaozhi-esp32-server:server_custom -f .\Dockerfile-server-offline .
} else {
    # 回退到标准Dockerfile
    docker build -t xiaozhi-esp32-server:server_custom -f .\Dockerfile-server .
}
```

### **3. 更新的部署脚本功能**

`scripts/offline-deploy.sh` 已优化：

✅ **新增目录：**
```bash
mkdir -p redis/data memory/mem_local_short intent/intent_llm docker-config
```

✅ **权限设置：**
```bash
chmod -R 755 memory intent docker-config
chmod -R 777 redis/data
```

---

## 📦 完整的打包部署流程

### **第一步：打包（Windows环境）**

```powershell
# 进入项目根目录
cd D:\workspace\xiaozhi-esp32-server

# 执行打包脚本
.\scripts\offline-package.ps1
```

**脚本会自动：**
1. ✅ 使用 `Dockerfile-server-offline` 构建Server镜像
2. ✅ 使用 `Dockerfile-web` 构建Web镜像
3. ✅ 拉取MySQL和Redis镜像
4. ✅ 导出所有镜像为tar文件
5. ✅ 复制配置文件和所有模块
6. ✅ 生成部署脚本和文档
7. ✅ 打包为tar.gz压缩包

**输出文件：**
```
xiaozhi-offline-deployment-20241024-153000.tar.gz
```

### **第二步：传输到CentOS服务器**

```bash
# 方式A: U盘/移动硬盘（推荐）
# 方式B: SCP网络传输
scp xiaozhi-offline-deployment-*.tar.gz root@服务器IP:/root/
```

### **第三步：部署（CentOS环境）**

```bash
# 1. 解压
cd /root
tar -xzf xiaozhi-offline-deployment-*.tar.gz
cd xiaozhi-offline-deployment-*/

# 2. 修复换行符
sed -i 's/\r$//' *.sh scripts/*.sh

# 3. 安装Docker（如未安装）
chmod +x install-docker-centos.sh
sudo ./install-docker-centos.sh

# 4. 一键部署
chmod +x offline-deploy.sh
sudo ./offline-deploy.sh
```

### **第四步：验证部署**

```bash
# 查看容器状态
docker ps

# 访问Web界面
http://服务器IP:8002

# 查看日志
docker-compose -f docker-compose-offline.yml logs -f xiaozhi-esp32-server
```

---

## 🔄 热更新支持

### **支持热更新的模块**

现在打包时会自动复制并挂载以下模块，支持在宿主机直接修改：

1. **工具函数模块** `plugins_func/functions/*.py`
2. **记忆模块** `memory/mem_local_short/mem_local_short.py`
3. **Intent识别模块** `intent/intent_llm/intent_llm.py`
4. **配置文件** `data/config.yaml`

### **热更新操作**

```bash
# 1. 修改文件（在宿主机上）
vi /root/xiaozhi-offline-deployment-*/plugins_func/functions/get_temperature_load_rate.py
vi /root/xiaozhi-offline-deployment-*/intent/intent_llm/intent_llm.py
vi /root/xiaozhi-offline-deployment-*/memory/mem_local_short/mem_local_short.py

# 2. 重启容器使更改生效
cd /root/xiaozhi-offline-deployment-*/
docker-compose -f docker-compose-offline.yml restart xiaozhi-esp32-server
docker-compose -f docker-compose-offline.yml up -d --force-recreate

# 3. 验证更改
docker-compose -f docker-compose-offline.yml logs --tail=200 -f xiaozhi-esp32-server
```

### **docker-compose挂载配置**

打包时使用的模板 `scripts/docker-compose-offline.template.yml` 已包含：

```yaml
xiaozhi-esp32-server:
  volumes:
    # 配置文件
    - ./data:/opt/xiaozhi-esp32-server/data
    # 工具函数
    - ./plugins_func/functions:/opt/xiaozhi-esp32-server/plugins_func/functions
    - ./plugins_func/register.py:/opt/xiaozhi-esp32-server/plugins_func/register.py
    # 记忆模块
    - ./memory/mem_local_short/mem_local_short.py:/opt/xiaozhi-esp32-server/core/providers/memory/mem_local_short/mem_local_short.py
    # Intent识别模块
    - ./intent/intent_llm/intent_llm.py:/opt/xiaozhi-esp32-server/core/providers/intent/intent_llm/intent_llm.py
    # 模型文件
    - ./models/SenseVoiceSmall/model.pt:/opt/xiaozhi-esp32-server/models/SenseVoiceSmall/model.pt
```

---

## 📊 新旧方案对比

| 对比项 | 旧方案 | 新方案（方案A） |
|--------|--------|----------------|
| **Dockerfile** | Dockerfile-server（有问题） | Dockerfile-server-offline |
| **远程依赖** | ❌ 依赖ghcr.io镜像 | ✅ 完全自包含 |
| **离线构建** | ❌ 会失败 | ✅ 完全支持 |
| **构建时间** | ~20分钟 | ~20分钟 |
| **镜像大小** | ~3-5GB | ~3-5GB |
| **热更新支持** | ⚠️ 仅部分 | ✅ 全面支持 |
| **维护复杂度** | 中等 | 低 |

---

## ✅ 升级建议

### **建议重新打包部署**

推荐您重新打包并迁移部署，原因：

1. ✅ **修复构建问题**：使用自包含Dockerfile，避免远程依赖
2. ✅ **完整热更新支持**：新增memory和intent模块挂载
3. ✅ **更好的容器配置**：优化资源限制和日志配置
4. ✅ **迭代完整版本**：包含您所有的开发成果

### **升级步骤**

```powershell
# 1. 在Windows环境重新打包
cd D:\workspace\xiaozhi-esp32-server
.\scripts\offline-package.ps1

# 2. 传输新包到服务器
scp xiaozhi-offline-deployment-*.tar.gz root@服务器IP:/root/

# 3. 在服务器上备份数据
cd /root/xiaozhi-offline-deployment-旧版本/
sudo ./scripts/backup.sh

# 4. 停止旧服务
docker-compose -f docker-compose-offline.yml down

# 5. 解压新包并部署
cd /root
tar -xzf xiaozhi-offline-deployment-新版本.tar.gz
cd xiaozhi-offline-deployment-新版本/

# 6. 复制数据（如需要）
cp -r ../xiaozhi-offline-deployment-旧版本/mysql/data ./mysql/
cp -r ../xiaozhi-offline-deployment-旧版本/uploadfile/* ./uploadfile/

# 7. 一键部署
chmod +x offline-deploy.sh
sudo ./offline-deploy.sh
```

---

## 🔧 方案B实施（可选）

如果您希望使用两阶段构建，需要：

### **1. 修复Dockerfile-server**

```dockerfile
# ==================== 第一阶段：构建阶段 ====================
FROM python:3.10-slim as builder

WORKDIR /app

# 配置pip
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.trusted-host mirrors.aliyun.com && \
    pip config set global.timeout 120 && \
    pip config set install.retries 5

# 复制requirements.txt
COPY main/xiaozhi-server/requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir torch==2.2.2 torchaudio==2.2.2 --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# ==================== 第二阶段：生产镜像 ====================
FROM python:3.10-slim

WORKDIR /opt/xiaozhi-esp32-server

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends libopus0 ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 从构建阶段复制Python包
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用代码
COPY main/xiaozhi-server .

# 暴露端口
EXPOSE 8000 8003

# 设置时区
ENV TZ=Asia/Shanghai

# 启动应用
CMD ["python", "app.py"]
```

### **2. 更新打包脚本**

修改 `scripts/offline-package.ps1`：

```powershell
# 编译Docker镜像
function Build-DockerImages {
    Print-Title "编译Docker镜像"
    Set-Location $global:ProjectRoot

    # 构建基础镜像（首次或依赖更新时）
    Print-Info "构建基础镜像..."
    docker build -t xiaozhi-esp32-server:server-base -f .\Dockerfile-server-base .

    # 构建生产镜像
    Print-Info "构建生产镜像..."
    docker build -t xiaozhi-esp32-server:server_custom -f .\Dockerfile-server .

    Print-Info "编译xiaozhi-esp32-server-web镜像..."
    docker build -t xiaozhi-esp32-server:web_custom -f .\Dockerfile-web .

    Print-Success "所有镜像编译完成"
}

# 导出Docker镜像
function Export-DockerImages {
    Print-Title "导出Docker镜像"
    $imagesDir = Join-Path $global:PackageDir "images"

    # 导出base镜像（新增）
    Print-Info "导出xiaozhi-esp32-server-base镜像..."
    docker save xiaozhi-esp32-server:server-base -o (Join-Path $imagesDir "server-base.tar")

    # 导出server镜像
    Print-Info "导出xiaozhi-esp32-server镜像..."
    docker save xiaozhi-esp32-server:server_custom -o (Join-Path $imagesDir "server.tar")

    # ... 其他镜像 ...
}
```

---

## 📝 总结

### **推荐方案**

✅ **使用方案A（自包含离线构建）**
- 已创建 `Dockerfile-server-offline`
- 已更新 `scripts/offline-package.ps1`
- 已更新 `scripts/offline-deploy.sh`
- 已完善热更新挂载配置

### **关键优势**

1. ✅ **完全离线**：不依赖任何远程镜像
2. ✅ **构建稳定**：避免网络问题和镜像版本冲突
3. ✅ **热更新完善**：支持工具函数、memory、intent模块
4. ✅ **易于维护**：单一Dockerfile，逻辑清晰

### **下一步行动**

```bash
# 1. 重新打包
.\scripts\offline-package.ps1

# 2. 传输到服务器
scp xiaozhi-offline-deployment-*.tar.gz root@服务器IP:/root/

# 3. 备份旧数据（如需要）
# 4. 部署新版本
sudo ./offline-deploy.sh

# 5. 验证功能
docker ps
http://服务器IP:8002
```

---

## 📚 相关文档

- `离线部署-快速操作指南.md` - 快速部署步骤
- `Dockerfile-server-offline` - 离线专用Dockerfile
- `scripts/offline-package.ps1` - 打包脚本
- `scripts/offline-deploy.sh` - 部署脚本
- `scripts/docker-compose-offline.template.yml` - Docker Compose配置模板

---

**享受优化后的离线部署体验！** 🚀

