# Docker构建优化 - 快速参考指南

## 🚨 问题诊断

### **当前Dockerfile-server的问题**
```dockerfile
FROM ghcr.io/xinnan-tech/xiaozhi-esp32-server:server-base  ← ❌ 依赖远程镜像
COPY --from=builder ...  ← ❌ builder阶段未定义
```

**影响**：离线环境无法构建镜像

---

## ✅ 解决方案

### **已创建文件：Dockerfile-server-offline**
- ✅ 自包含，无远程依赖
- ✅ 适合离线部署
- ✅ 包含所有依赖

### **已更新脚本**
- ✅ `scripts/offline-package.ps1` - 自动使用新Dockerfile
- ✅ `scripts/offline-deploy.sh` - 支持新模块目录

---

## 📦 新增热更新支持

### **打包时自动复制的模块**
```
xiaozhi-offline-deployment-*/
├── plugins_func/functions/*.py       ← 工具函数
├── memory/mem_local_short/*.py       ← 记忆模块（新增）
├── intent/intent_llm/*.py            ← Intent识别（新增）
├── docker-config/                    ← Docker配置（新增）
└── redis/data/                       ← Redis数据（新增）
```

### **热更新操作**
```bash
# 1. 修改文件
vi /root/xiaozhi-offline-deployment-*/intent/intent_llm/intent_llm.py

# 2. 重启容器
docker-compose -f docker-compose-offline.yml restart xiaozhi-esp32-server

# 3. 查看日志
docker-compose -f docker-compose-offline.yml logs --tail=200 -f xiaozhi-esp32-server
```

---

## 🚀 快速重新部署

### **Windows环境（打包）**
```powershell
cd D:\workspace\xiaozhi-esp32-server
.\scripts\offline-package.ps1
```

### **CentOS环境（部署）**
```bash
# 1. 传输文件
scp xiaozhi-offline-deployment-*.tar.gz root@服务器IP:/root/

# 2. 解压
cd /root
tar -xzf xiaozhi-offline-deployment-*.tar.gz
cd xiaozhi-offline-deployment-*/
sed -i 's/\r$//' *.sh scripts/*.sh

# 3. 备份旧数据（可选）
# 如果需要保留数据，从旧版本复制：
# cp -r ../旧版本/mysql/data ./mysql/
# cp -r ../旧版本/uploadfile/* ./uploadfile/

# 4. 一键部署
chmod +x offline-deploy.sh
sudo ./offline-deploy.sh
```

---

## 📊 方案对比

| 特性 | 旧方案 | 新方案 |
|------|--------|--------|
| 离线构建 | ❌ 失败 | ✅ 成功 |
| 远程依赖 | ❌ 有 | ✅ 无 |
| 热更新模块 | ⚠️ 2个 | ✅ 4个 |
| 构建时间 | ~20分钟 | ~20分钟 |
| 镜像大小 | ~3-5GB | ~3-5GB |

---

## 🎯 核心改进

### **1. 修复构建问题**
- 使用`Dockerfile-server-offline`替代问题版本
- 自包含所有依赖，无需远程base镜像

### **2. 完善热更新**
- 新增`memory`模块挂载
- 新增`intent`模块挂载
- 新增`docker-config`配置挂载

### **3. 优化目录结构**
- 自动创建所有必要目录
- 设置正确的权限

---

## ⚠️ 注意事项

### **Dockerfile选择**
- ✅ 离线部署：使用 `Dockerfile-server-offline`
- ⚠️ 开发环境：可以使用修复后的 `Dockerfile-server`

### **数据迁移**
重新部署前备份：
```bash
# 备份数据库
cp -r mysql/data mysql/data.backup

# 备份上传文件
cp -r uploadfile uploadfile.backup

# 备份配置
cp -r data data.backup
```

---

## 📚 完整文档

详细说明请参考：**`离线部署-Docker构建优化方案.md`**

---

**立即开始优化部署！** 🚀

