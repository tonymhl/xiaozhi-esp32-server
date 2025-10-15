# 小智ESP32服务器 - 离线部署文档总览

> 📦 完整的离线部署解决方案，帮助您将项目顺利迁移到离线CentOS环境

---

## 📚 文档导航

### 🚀 快速开始

如果您是第一次部署，建议按以下顺序阅读：

1. **[快速部署指南](offline-deployment-quickstart.md)** ⭐ 推荐
   - 5分钟快速部署
   - 最精简的步骤说明
   - 常用命令速查

2. **[部署检查清单](offline-deployment-checklist.md)**
   - 完整的检查项目
   - 确保不遗漏任何步骤
   - 可打印使用

### 📖 详细文档

3. **[完整部署指南](offline-deployment-guide.md)**
   - 最详细的部署说明
   - 包含所有配置细节
   - 故障排查基础指南
   - 服务管理和维护

4. **[故障排查手册](offline-deployment-troubleshooting.md)**
   - 常见问题详细解决方案
   - 系统诊断方法
   - 性能优化建议
   - 数据恢复方案

### 🛠️ 脚本工具

5. **[脚本使用说明](../scripts/README.md)**
   - 所有脚本的详细说明
   - 使用方法和示例
   - 故障排查技巧

---

## 📦 文件结构

```
xiaozhi-offline-deployment/
├── images/                          # Docker镜像文件
│   ├── server.tar                   # Python服务镜像
│   ├── web.tar                      # Web管理镜像
│   ├── mysql.tar                    # MySQL镜像
│   ├── redis.tar                    # Redis镜像
│   └── checksums.md5                # 校验和文件
│
├── scripts/                         # 运维脚本
│   ├── backup.sh                    # 数据备份脚本
│   └── README.md                    # 脚本说明文档
│
├── data/                            # 应用配置目录
│   ├── config.yaml                  # 主配置文件
│   └── config_from_api.yaml         # API配置
│
├── mysql/                           # MySQL数据目录
│   └── data/                        # 数据库文件
│
├── uploadfile/                      # 上传文件目录
│
├── models/                          # AI模型目录
│   └── SenseVoiceSmall/
│       └── model.pt                 # 语音识别模型
│
├── docker-compose-offline.yml       # Docker Compose配置
├── offline-deploy.sh                # 自动部署脚本
├── install-docker-centos.sh         # Docker安装脚本
│
├── offline-deployment-guide.md      # 完整部署指南
├── offline-deployment-quickstart.md # 快速部署指南
├── offline-deployment-checklist.md  # 部署检查清单
├── offline-deployment-troubleshooting.md # 故障排查手册
├── DEPLOYMENT-MANIFEST.txt          # 部署清单
└── README.txt                       # 快速说明
```

---

## 🎯 使用场景

### 场景一：全新部署

**目标**: 在一台全新的CentOS服务器上部署

**步骤**:
1. 传输部署包到服务器
2. 解压部署包
3. 执行 `install-docker-centos.sh`
4. 执行 `offline-deploy.sh`
5. 访问Web界面验证

**参考文档**: [快速部署指南](offline-deployment-quickstart.md)

---

### 场景二：开发环境打包

**目标**: 在开发机器上打包最新代码

**步骤**:
1. 确保所有代码已提交
2. 运行打包脚本
   - Windows: `.\scripts\offline-package.ps1`
   - Linux/Mac: `./scripts/offline-package.sh`
3. 获得压缩包

**参考文档**: [脚本使用说明](../scripts/README.md)

---

### 场景三：版本升级

**目标**: 在已部署的服务器上升级到新版本

**步骤**:
1. 备份现有数据 (`scripts/backup.sh`)
2. 传输新版本部署包
3. 停止旧版本服务
4. 加载新版本镜像
5. 启动新版本服务
6. 验证功能

**参考文档**: [完整部署指南 - 升级与维护](offline-deployment-guide.md#八升级与维护)

---

### 场景四：故障排查

**目标**: 解决部署或运行时问题

**步骤**:
1. 识别问题现象
2. 查看[故障排查手册](offline-deployment-troubleshooting.md)
3. 按照对应章节排查
4. 收集系统信息（如需帮助）
5. 联系技术支持

**参考文档**: [故障排查手册](offline-deployment-troubleshooting.md)

---

## 🎓 学习路径

### 初学者

```
快速部署指南 → 实际操作 → 遇到问题查故障排查手册
```

### 运维人员

```
完整部署指南 → 部署检查清单 → 脚本使用说明 → 故障排查手册
```

### 开发人员

```
脚本使用说明 → 完整部署指南 → 自定义修改 → 打包测试
```

---

## ⚡ 常用命令速查

### 服务管理

```bash
# 启动所有服务
docker-compose -f docker-compose-offline.yml up -d

# 停止所有服务
docker-compose -f docker-compose-offline.yml down

# 重启服务
docker-compose -f docker-compose-offline.yml restart

# 查看状态
docker-compose -f docker-compose-offline.yml ps

# 查看日志
docker-compose -f docker-compose-offline.yml logs -f
```

### 容器操作

```bash
# 进入server容器
docker exec -it xiaozhi-esp32-server bash

# 查看server日志
docker logs -f xiaozhi-esp32-server

# 重启单个容器
docker restart xiaozhi-esp32-server
```

### 数据备份

```bash
# 手动备份
./scripts/backup.sh

# 配置自动备份
crontab -e
# 添加: 0 2 * * * /root/offline-package/scripts/backup.sh
```

### 系统诊断

```bash
# 检查资源使用
docker stats

# 检查磁盘空间
df -h
docker system df

# 检查网络连接
netstat -tlnp | grep -E "8000|8002|8003"

# 查看防火墙
firewall-cmd --list-ports
```

---

## 🔑 关键配置文件

### docker-compose-offline.yml
Docker服务编排配置，包含：
- 镜像名称和标签
- 端口映射
- 数据卷挂载
- 环境变量
- 资源限制

**修改后需要**: `docker-compose -f docker-compose-offline.yml up -d --force-recreate`

### data/config.yaml
应用主配置文件，包含：
- 服务器IP和端口
- API密钥
- 功能开关
- 工具函数配置

**修改后需要**: `docker-compose -f docker-compose-offline.yml restart xiaozhi-esp32-server`

---

## 📊 系统要求

### 最低配置

| 组件 | 要求 |
|------|------|
| 操作系统 | CentOS 7.x / 8.x / Stream |
| CPU | 4核心 |
| 内存 | 8GB |
| 磁盘 | 50GB可用空间 |
| Docker | 20.10+ |

### 推荐配置

| 组件 | 要求 |
|------|------|
| 操作系统 | CentOS 8 / Stream |
| CPU | 8核心+ |
| 内存 | 16GB+ |
| 磁盘 | 100GB+ SSD |
| Docker | 最新版本 |

---

## 🔐 安全建议

### 必须修改的默认配置

```yaml
# 1. 修改MySQL密码
# docker-compose-offline.yml
environment:
  - MYSQL_ROOT_PASSWORD: 你的强密码

# 2. 修改管理员账号密码
# 登录Web界面后立即修改

# 3. 配置防火墙
firewall-cmd --permanent --add-rich-rule='
  rule family="ipv4" source address="允许的IP段"
  port protocol="tcp" port="8002" accept'

# 4. 启用HTTPS（生产环境）
# 配置Nginx SSL证书
```

---

## 📈 性能优化建议

### 数据库优化

```yaml
# docker-compose-offline.yml MySQL部分
command:
  - --max_connections=1000
  - --innodb_buffer_pool_size=2G  # 设置为总内存的50-70%
  - --innodb_log_file_size=256M
  - --query_cache_size=64M
```

### Redis优化

```yaml
command:
  - redis-server
  - --maxmemory 2gb
  - --maxmemory-policy allkeys-lru
```

### 应用优化

```yaml
# docker-compose-offline.yml server部分
deploy:
  resources:
    limits:
      cpus: '8'
      memory: 16G
```

---

## 📞 获取支持

### 在线资源

- **项目主页**: https://github.com/xinnan-tech/xiaozhi-esp32-server
- **文档中心**: https://github.com/xinnan-tech/xiaozhi-esp32-server/tree/main/docs
- **问题反馈**: https://github.com/xinnan-tech/xiaozhi-esp32-server/issues

### 提交问题时请提供

1. 系统信息（OS版本、Docker版本）
2. 部署包版本和打包时间
3. 错误现象和日志
4. troubleshoot.log（使用故障排查手册中的脚本生成）

### 社区支持

- 查看已有的Issue和讨论
- 参考Wiki文档
- 参与社区讨论

---

## 📝 更新日志

### v1.0 (2024)

**新功能**:
- ✅ 完整的离线部署方案
- ✅ 自动化打包和部署脚本
- ✅ 详细的文档体系
- ✅ 故障排查指南
- ✅ 数据备份和恢复方案

**改进**:
- ✅ 优化Docker镜像构建
- ✅ 增加资源限制配置
- ✅ 配置日志轮转
- ✅ 添加健康检查

---

## ✅ 部署成功标志

当您看到以下现象时，说明部署成功：

- ✅ 4个容器都处于运行状态
- ✅ 可以访问 http://服务器IP:8002
- ✅ Web界面正常显示
- ✅ 可以正常登录管理后台
- ✅ 数据库连接正常
- ✅ 工具函数可以正常调用
- ✅ ESP32设备可以连接（如有）

---

## 🎉 结语

这套离线部署方案经过精心设计和测试，旨在帮助您：

- 🚀 **快速部署** - 自动化脚本简化流程
- 🛡️ **稳定可靠** - 完整的故障处理方案
- 📚 **文档完善** - 详细的说明和示例
- 🔧 **易于维护** - 运维脚本和监控方案
- 🆘 **技术支持** - 完整的问题排查指南

如果您在使用过程中有任何问题或建议，欢迎反馈！

**祝您部署顺利！** 🎊

---

**文档版本**: 1.0
**最后更新**: 2024
**维护者**: Xinnan Tech

