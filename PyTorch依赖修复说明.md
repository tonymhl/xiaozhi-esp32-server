# PyTorch 依赖安装问题修复

## 🐛 问题描述

在打包过程中遇到错误：
```
ERROR: Invalid requirement: 'torch==2.2.2+cpu torchvision==0.17.2+cpu torchaudio==2.2.2+cpu': 
Expected end or semicolon (after version specifier)
```

---

## 🔍 原因分析

### 问题1：requirements.txt 格式错误

**第2行原内容**：
```
torch==2.2.2+cpu torchvision==0.17.2+cpu torchaudio==2.2.2+cpu
```

**错误**：
1. 三个包写在同一行（应该每行一个包）
2. 使用了 `+cpu` 后缀（pip标准格式不支持）
3. 与第9行的 `torchaudio==2.2.2` 重复

### 问题2：PyTorch CPU版本安装

`+cpu` 后缀是PyTorch特定的版本标识符，需要从PyTorch官方索引安装：
```
--index-url https://download.pytorch.org/whl/cpu
```

---

## ✅ 修复方案

### 修复1：更新 requirements.txt

将PyTorch相关包从 `requirements.txt` 中移除并注释：

```python
pyyml==0.0.2
# torch和torchaudio在Dockerfile中单独安装CPU版本
# torch==2.2.2
# torchaudio==2.2.2
silero_vad==6.0.0
...其他依赖...
```

### 修复2：更新 Dockerfile-server

在Dockerfile中单独安装PyTorch CPU版本：

```dockerfile
# 安装Python依赖
# 先安装PyTorch（较大的包），然后安装其他依赖
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir torch==2.2.2 torchaudio==2.2.2 \
    --index-url https://download.pytorch.org/whl/cpu \
    --default-timeout=120 --retries 5 && \
    pip install --no-cache-dir -r requirements.txt \
    --default-timeout=120 --retries 5
```

---

## 🎯 优势

### 1. **使用CPU版本** - 镜像更小
- PyTorch GPU版本：~2GB
- PyTorch CPU版本：~200MB
- **节省约1.8GB镜像大小**

### 2. **构建更稳定**
- PyTorch从官方索引下载，更可靠
- 其他依赖从阿里云镜像下载，更快

### 3. **避免冲突**
- 不会重复安装PyTorch
- 版本明确控制

---

## 📋 验证修复

### 步骤1：清理并重新打包

```powershell
# 清理旧的Docker缓存
.\scripts\clean-and-rebuild.ps1

# 重新打包
.\scripts\offline-package.ps1
```

### 步骤2：检查构建日志

应该看到：
```
Successfully installed torch-2.2.2 torchaudio-2.2.2
Successfully installed [其他依赖...]
```

### 步骤3：验证容器中的PyTorch

部署后验证：
```bash
docker exec xiaozhi-esp32-server python -c "import torch; print(torch.__version__); print('CUDA available:', torch.cuda.is_available())"
```

预期输出：
```
2.2.2+cpu
CUDA available: False
```

---

## 🔄 如果需要GPU支持

如果将来需要GPU支持，修改Dockerfile-server：

```dockerfile
# GPU版本（需要CUDA环境）
RUN pip install --no-cache-dir torch==2.2.2 torchaudio==2.2.2 \
    --index-url https://download.pytorch.org/whl/cu118
```

但请注意：
1. 基础镜像需要包含CUDA
2. 镜像大小会显著增加
3. 部署环境需要NVIDIA GPU

---

## 📝 相关文件

修改的文件：
- `main/xiaozhi-server/requirements.txt` - 移除PyTorch依赖
- `Dockerfile-server` - 添加PyTorch CPU版本安装

---

## ⚠️ 注意事项

### 1. 版本锁定

当前锁定版本：
- torch: 2.2.2
- torchaudio: 2.2.2

如需升级，同时修改：
- `Dockerfile-server` 中的版本号
- `requirements.txt` 中的注释

### 2. 依赖顺序

PyTorch必须先于其他依赖安装，因为某些包（如 `funasr`）依赖PyTorch。

### 3. 镜像源

- PyTorch: `https://download.pytorch.org/whl/cpu`
- 其他包: `https://mirrors.aliyun.com/pypi/simple/`

---

## ✅ 修复后的完整流程

```powershell
# 1. 清理环境
.\scripts\clean-and-rebuild.ps1

# 2. 重新打包（约30-40分钟）
.\scripts\offline-package.ps1

# 3. 传输到CentOS
scp xiaozhi-offline-deployment-*.tar.gz root@服务器IP:/root/

# 4. 部署
# 在CentOS上
tar -xzf xiaozhi-offline-deployment-*.tar.gz
cd xiaozhi-offline-deployment-*/
./offline-deploy.sh
```

---

## 🎉 总结

通过将PyTorch安装独立出来并使用官方CPU索引：
- ✅ 解决了requirements.txt格式错误
- ✅ 使用CPU版本减小镜像大小
- ✅ 提高构建稳定性
- ✅ 避免依赖冲突

现在可以正常打包部署了！

