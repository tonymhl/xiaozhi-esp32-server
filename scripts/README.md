# 小智ESP32服务器 - 脚本工具说明

本目录包含小智ESP32服务器离线部署所需的所有脚本工具。

---

## 📁 文件清单

### 打包脚本（在线环境使用）

#### `offline-package.sh` - Linux/Mac打包脚本
**用途**: 在有网络的Linux/Mac环境中，自动打包所有Docker镜像和配置文件

**使用方法**:
```bash
chmod +x offline-package.sh
./offline-package.sh
```

**功能**:
- ✅ 自动编译Docker镜像
- ✅ 拉取依赖镜像（MySQL、Redis）
- ✅ 导出所有镜像为tar文件
- ✅ 复制配置文件和文档
- ✅ 生成部署清单
- ✅ 创建校验和
- ✅ 打包为tar.gz压缩包

**输出**: `xiaozhi-offline-deployment-YYYYMMDD-HHMMSS.tar.gz`

---

#### `offline-package.ps1` - Windows打包脚本
**用途**: 在有网络的Windows环境中，自动打包所有Docker镜像和配置文件

**使用方法**:
```powershell
.\offline-package.ps1
```

**功能**: 与Linux版本相同，适配Windows PowerShell环境

**注意**: Windows环境需要安装Docker Desktop

---

### 部署脚本（离线环境使用）

#### `offline-deploy.sh` - 离线自动部署脚本
**用途**: 在离线CentOS服务器上，自动部署所有服务

**使用方法**:
```bash
chmod +x offline-deploy.sh
sudo ./offline-deploy.sh
```

**功能**:
- ✅ 检查Docker环境
- ✅ 验证镜像文件完整性
- ✅ 加载所有Docker镜像
- ✅ 创建必要的目录结构
- ✅ 配置防火墙规则
- ✅ 启动所有服务
- ✅ 健康检查
- ✅ 显示访问信息

**前置条件**: Docker和Docker Compose已安装

---

#### `install-docker-centos.sh` - Docker安装脚本
**用途**: 在CentOS 7/8/Stream上安装Docker和Docker Compose

**使用方法**:
```bash
chmod +x install-docker-centos.sh
sudo ./install-docker-centos.sh
```

**功能**:
- ✅ 检测系统版本
- ✅ 卸载旧版本Docker
- ✅ 配置阿里云镜像源
- ✅ 安装Docker CE
- ✅ 安装Docker Compose
- ✅ 配置Docker守护进程
- ✅ 启动Docker服务
- ✅ 运行测试容器验证

**支持系统**: CentOS 7/8/Stream, RHEL, Rocky Linux, AlmaLinux

---

### 运维脚本

#### `backup.sh` - 数据备份脚本
**用途**: 定期备份配置文件、数据库和上传文件

**使用方法**:
```bash
chmod +x backup.sh
sudo ./backup.sh
```

**功能**:
- ✅ 备份配置文件
- ✅ 备份MySQL数据库
- ✅ 备份上传文件
- ✅ 生成备份清单
- ✅ 自动清理30天前的旧备份

**备份位置**: `/backup/xiaozhi-esp32-server/YYYYMM/YYYYMMDD_HHMMSS/`

**定时备份设置**:
```bash
# 编辑crontab
crontab -e

# 添加以下行（每天凌晨2点备份）
0 2 * * * /root/offline-package/scripts/backup.sh >> /var/log/xiaozhi-backup.log 2>&1
```

---

### 配置模板

#### `docker-compose-offline.template.yml` - Docker Compose配置模板
**用途**: 离线部署的Docker Compose配置文件模板

**特点**:
- 使用自定义镜像标签
- 包含资源限制配置
- 包含日志轮转配置
- 优化的数据库和Redis参数

**使用**: 打包脚本会自动将此模板复制并修改为 `docker-compose-offline.yml`

---

## 🔄 完整工作流程

### 1️⃣ 在线环境（开发机器）

```bash
# 1. 进入项目根目录
cd xiaozhi-esp32-server

# 2. 执行打包（Linux/Mac）
chmod +x scripts/offline-package.sh
./scripts/offline-package.sh

# 或者（Windows）
.\scripts\offline-package.ps1

# 3. 获得压缩包
# xiaozhi-offline-deployment-YYYYMMDD-HHMMSS.tar.gz
```

### 2️⃣ 文件传输

```bash
# 方式A: SCP传输
scp xiaozhi-offline-deployment-*.tar.gz root@目标服务器:/root/

# 方式B: U盘拷贝
# 将文件复制到U盘，然后插入目标服务器
```

### 3️⃣ 离线环境（CentOS服务器）

```bash
# 1. 解压部署包
cd /root
tar -xzf xiaozhi-offline-deployment-*.tar.gz
cd xiaozhi-offline-deployment-*/

# 2. 安装Docker（如未安装）
chmod +x install-docker-centos.sh
sudo ./install-docker-centos.sh

# 3. 执行部署
chmod +x offline-deploy.sh
sudo ./offline-deploy.sh

# 4. 配置定时备份
chmod +x scripts/backup.sh
sudo crontab -e
# 添加: 0 2 * * * /root/xiaozhi-offline-deployment-*/scripts/backup.sh
```

---

## 📝 脚本使用注意事项

### 权限要求
- 所有脚本都需要执行权限：`chmod +x script_name.sh`
- 部署和安装脚本需要root权限：使用`sudo`或root用户执行

### 环境要求

**打包环境（在线）**:
- Docker 20.10+
- Docker Compose 1.29+
- 网络连接
- 20GB+ 可用磁盘空间

**部署环境（离线）**:
- CentOS 7/8/Stream
- 8GB+ 内存
- 50GB+ 可用磁盘空间
- Docker 20.10+（可使用脚本安装）

### 执行顺序

1. **首次部署**:
   ```
   offline-package.sh → 传输 → install-docker-centos.sh → offline-deploy.sh
   ```

2. **后续维护**:
   ```
   backup.sh（定期执行）
   ```

3. **版本升级**:
   ```
   offline-package.sh（打包新版本） → 传输 → offline-deploy.sh
   ```

---

## 🐛 故障排查

### 打包失败

**现象**: offline-package脚本执行失败

**排查**:
```bash
# 检查Docker服务
systemctl status docker

# 检查磁盘空间
df -h

# 检查网络连接
ping mirrors.aliyun.com

# 查看详细错误信息
./offline-package.sh 2>&1 | tee package.log
```

### 部署失败

**现象**: offline-deploy脚本执行失败

**排查**:
```bash
# 检查镜像文件
ls -lh images/

# 验证镜像完整性
cd images && md5sum -c checksums.md5

# 检查Docker服务
systemctl status docker

# 查看容器日志
docker logs xiaozhi-esp32-server
```

### Docker安装失败

**现象**: install-docker-centos脚本执行失败

**排查**:
```bash
# 检查系统版本
cat /etc/os-release

# 检查网络（如果不是完全离线）
ping mirrors.aliyun.com

# 手动安装
yum install -y docker-ce docker-ce-cli containerd.io
```

---

## 📚 相关文档

- [完整部署指南](../docs/offline-deployment-guide.md) - 详细的步骤说明
- [快速部署指南](../docs/offline-deployment-quickstart.md) - 5分钟快速部署
- [部署检查清单](../docs/offline-deployment-checklist.md) - 完整的检查清单

---

## 💡 提示和技巧

### 自定义打包内容

修改 `offline-package.sh` 中的 `copy_configs()` 函数来包含额外的文件：

```bash
# 在copy_configs函数中添加
cp 你的额外文件 "${PACKAGE_DIR}/"
```

### 修改镜像标签

如果需要使用不同的镜像标签，修改脚本中的：
```bash
# 从
docker build -t xiaozhi-esp32-server:server_custom ...

# 改为
docker build -t xiaozhi-esp32-server:v2.0 ...
```

### 调试模式

在脚本开头添加 `set -x` 启用调试输出：
```bash
#!/bin/bash
set -x  # 启用调试
set -e  # 遇到错误退出
```

---

## 🆘 获取帮助

如果脚本执行遇到问题：

1. 查看脚本输出的错误信息
2. 参考 [offline-deployment-guide.md](../docs/offline-deployment-guide.md) 故障排查章节
3. 查看项目文档: https://github.com/xinnan-tech/xiaozhi-esp32-server/tree/main/docs
4. 提交Issue: https://github.com/xinnan-tech/xiaozhi-esp32-server/issues

---

**版本**: 1.0
**最后更新**: 2024
**维护者**: Xinnan Tech

