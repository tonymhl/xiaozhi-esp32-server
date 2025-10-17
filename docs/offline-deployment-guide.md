# 小智ESP32服务器离线部署完整指南

本指南将帮助您将整个项目打包成Docker镜像，并在离线CentOS环境中部署。

## 📋 目录

- [一、概述](#一概述)
- [二、在线环境准备与打包](#二在线环境准备与打包)
- [三、文件传输](#三文件传输)
- [四、离线环境部署](#四离线环境部署)
- [五、验证与测试](#五验证与测试)
- [六、常见问题排查](#六常见问题排查)

---

## 一、概述

### 1.1 部署架构

本项目包含以下组件：

- **xiaozhi-esp32-server**: Python服务（包含您的工具函数）
- **xiaozhi-esp32-server-web**: Vue前端 + Java后端（管理控制台）
- **MySQL**: 数据库
- **Redis**: 缓存服务

### 1.2 部署方式

采用Docker容器化部署，支持两种模式：
- **单服务模式**: 仅部署xiaozhi-esp32-server
- **全模块模式**: 部署所有服务（推荐）

### 1.3 系统要求

**在线打包环境（Windows/Linux/Mac）:**
- Docker 20.10+
- Docker Compose 1.29+
- 网络连接
- 至少20GB可用磁盘空间

**离线目标环境（CentOS 7/8）:**
- CentOS 7.x 或 8.x
- 至少8GB内存
- 至少50GB可用磁盘空间
- Docker 20.10+（需提前安装或随包提供）

---

## 二、在线环境准备与打包

### 2.1 准备工作

在您当前的开发环境中，确保所有新增的工具函数和修改已提交：

```bash
# 检查项目状态
git status

# 确保所有更改已提交
git add .
git commit -m "添加新的工具函数和功能"
```

### 2.2 使用自动化打包脚本（推荐）

我们提供了一键打包脚本，它会自动完成所有打包工作。

#### Windows环境:

```powershell
# 进入项目根目录
cd D:\workspace\xiaozhi-esp32-server

# 执行打包脚本
.\scripts\offline-package.ps1
```

#### Linux/Mac环境:

```bash
# 进入项目根目录
cd /path/to/xiaozhi-esp32-server

# 添加执行权限
chmod +x scripts/offline-package.sh

# 执行打包脚本
./scripts/offline-package.sh
```

脚本将自动完成以下操作：
1. 编译所有Docker镜像
2. 拉取所需的基础镜像（MySQL、Redis）
3. 导出所有镜像为tar文件
4. 复制必要的配置文件和脚本
5. 生成部署清单
6. 打包成一个完整的tar.gz压缩包

**打包完成后，您将获得：**
```
xiaozhi-offline-deployment-YYYYMMDD-HHMMSS.tar.gz
```

### 2.3 手动打包步骤（可选）

如果您需要手动控制打包过程，请按以下步骤操作：

#### 步骤1: 编译自定义镜像

```bash
# 进入项目根目录
cd xiaozhi-esp32-server

# 编译server镜像
docker build -t xiaozhi-esp32-server:server_custom -f ./Dockerfile-server .

# 编译web镜像
docker build -t xiaozhi-esp32-server:web_custom -f ./Dockerfile-web .
```

#### 步骤2: 拉取依赖镜像

```bash
# 拉取MySQL镜像
docker pull mysql:latest

# 拉取Redis镜像
docker pull redis:latest
```

#### 步骤3: 导出所有镜像

```bash
# 创建导出目录
mkdir -p offline-package/images

# 导出server镜像
docker save xiaozhi-esp32-server:server_custom -o offline-package/images/server.tar

# 导出web镜像
docker save xiaozhi-esp32-server:web_custom -o offline-package/images/web.tar

# 导出MySQL镜像
docker save mysql:latest -o offline-package/images/mysql.tar

# 导出Redis镜像
docker save redis:latest -o offline-package/images/redis.tar
```

#### 步骤4: 复制配置文件

```bash
# 复制docker-compose配置
cp main/xiaozhi-server/docker-compose_all.yml offline-package/
cp main/xiaozhi-server/config.yaml offline-package/
cp main/xiaozhi-server/config_from_api.yaml offline-package/

# 复制部署脚本
cp scripts/offline-deploy.sh offline-package/
cp scripts/install-docker-centos.sh offline-package/

# 复制必要的目录结构
mkdir -p offline-package/data
mkdir -p offline-package/mysql/data
mkdir -p offline-package/uploadfile
mkdir -p offline-package/models/SenseVoiceSmall

# 复制模型文件（如果有）
cp -r main/xiaozhi-server/models/* offline-package/models/
```

#### 步骤5: 压缩打包

```bash
# 创建压缩包
tar -czf xiaozhi-offline-deployment-$(date +%Y%m%d-%H%M%S).tar.gz offline-package/

# 查看包大小
ls -lh xiaozhi-offline-deployment-*.tar.gz
```

---

## 三、文件传输

### 3.1 传输方式选择

根据您的网络环境选择合适的传输方式：

**方式A: U盘/移动硬盘（推荐用于完全离线环境）**
```bash
# 将压缩包复制到移动存储设备
cp xiaozhi-offline-deployment-*.tar.gz /media/usb/
```

**方式B: SCP（适用于有临时网络连接）**
```bash
# 传输到目标服务器
scp xiaozhi-offline-deployment-*.tar.gz root@target-server:/root/
```

**方式C: SFTP工具**
- 使用WinSCP、FileZilla等工具传输

### 3.2 验证文件完整性

在传输前生成校验和：
```bash
# 生成MD5校验
md5sum xiaozhi-offline-deployment-*.tar.gz > checksum.md5
```

在目标服务器上验证：
```bash
# 验证文件完整性
md5sum -c checksum.md5
```

---

## 四、离线环境部署

### 4.1 环境准备

#### 步骤1: 检查Docker安装

```bash
# 检查Docker是否已安装
docker --version
docker-compose --version
```

如果未安装Docker，使用提供的安装脚本：

```bash
# 解压部署包
cd /root
tar -xzf xiaozhi-offline-deployment-*.tar.gz
cd offline-package
sed -i 's/\r$//' *.sh scripts/*.sh

# 安装Docker（CentOS 7/8）
chmod +x install-docker-centos.sh
./install-docker-centos.sh
```

#### 步骤2: 启动Docker服务

```bash
# 启动Docker服务
systemctl start docker
systemctl enable docker

# 验证Docker状态
systemctl status docker
```

### 4.2 加载镜像

```bash
# 进入镜像目录
cd /root/offline-package/images

# 加载所有镜像
docker load -i server.tar
docker load -i web.tar
docker load -i mysql.tar
docker load -i redis.tar

# 验证镜像加载
docker images
```

预期输出应包含：
```
REPOSITORY                  TAG            IMAGE ID       SIZE
xiaozhi-esp32-server       server_custom   xxxxx          xxGB
xiaozhi-esp32-server       web_custom      xxxxx          xxGB
mysql                      latest          xxxxx          xxGB
redis                      latest          xxxxx          xxGB
```

### 4.3 配置服务

#### 步骤1: 修改docker-compose配置

```bash
cd /root/offline-package

# 编辑docker-compose文件
vi docker-compose-offline.yml
```

确认以下关键配置：
- 镜像名称和标签正确
- 端口映射符合需求
- 数据卷路径正确
- 环境变量（数据库密码等）设置正确

#### 步骤2: 配置应用参数

```bash
# 编辑配置文件
vi data/config.yaml

# 根据实际环境修改：
# - 服务器IP地址
# - 端口配置
# - API密钥
# - 模型路径等
```

### 4.4 部署服务

#### 使用自动化部署脚本（推荐）

```bash
cd /root/offline-package

# 添加执行权限
chmod +x offline-deploy.sh

# 执行部署
./offline-deploy.sh
```

脚本会自动完成：
- ✅ 检查系统环境
- ✅ 验证镜像完整性
- ✅ 创建必要目录
- ✅ 设置权限
- ✅ 启动所有服务
- ✅ 健康检查

#### 手动部署步骤

如果您需要手动控制部署过程：

```bash
# 创建必要的目录
mkdir -p data mysql/data uploadfile models/SenseVoiceSmall

# 设置权限
chmod -R 755 data uploadfile
chmod -R 777 mysql/data

# 启动服务（全模块模式）
docker-compose -f docker-compose-offline.yml up -d

# 查看服务状态
docker-compose -f docker-compose-offline.yml ps

# 查看服务日志
docker-compose -f docker-compose-offline.yml logs -f
```

### 4.5 等待服务启动

首次启动需要初始化数据库，可能需要1-3分钟：

```bash
# 实时查看启动日志
docker-compose -f docker-compose-offline.yml logs -f

# 检查服务健康状态
docker ps

# 等待所有服务状态变为healthy或running
```

---

## 五、验证与测试

### 5.1 基础连通性测试

```bash
# 测试xiaozhi-server服务
curl http://localhost:8000

# 测试Web管理界面
curl http://localhost:8002

# 测试HTTP服务
curl http://localhost:8003
```

### 5.2 Web界面访问

打开浏览器访问：
```
http://服务器IP:8002
```

默认管理员账号：
- 账号: admin
- 密码: （请参考项目文档）

### 5.3 验证工具函数

测试您新增的工具函数是否正常工作：

```bash
# 进入server容器
docker exec -it xiaozhi-esp32-server bash

# 检查工具函数文件
ls -l /opt/xiaozhi-esp32-server/plugins_func/functions/

# 检查Python依赖
pip list | grep psutil

# 退出容器
exit
```

### 5.4 数据库连接测试

```bash
# 进入MySQL容器
docker exec -it xiaozhi-esp32-server-db mysql -uroot -p123456

# 查看数据库
SHOW DATABASES;
USE xiaozhi_esp32_server;
SHOW TABLES;

# 退出
exit
```

### 5.5 完整功能测试

- [ ] ESP32设备能否正常连接
- [ ] 语音识别功能正常
- [ ] 语音合成功能正常
- [ ] 工具函数调用正常（如get_temperature_load_rate）
- [ ] Web管理界面功能完整
- [ ] 数据持久化正常

---

## 六、常见问题排查

### 6.1 镜像加载失败

**症状**: `docker load` 报错或镜像不完整

**解决方案**:
```bash
# 验证tar文件完整性
tar -tzf server.tar > /dev/null
echo $?  # 返回0表示文件完整

# 重新传输损坏的镜像文件
# 使用md5sum验证文件完整性
```

### 6.2 服务启动失败

**症状**: 容器不断重启

**排查步骤**:
```bash
# 查看详细日志
docker-compose -f docker-compose-offline.yml logs xiaozhi-esp32-server

# 检查容器状态
docker inspect xiaozhi-esp32-server

# 进入容器调试
docker exec -it xiaozhi-esp32-server bash
```

**常见原因**:
- 端口被占用：修改docker-compose中的端口映射
- 权限问题：`chmod -R 777 mysql/data`
- 配置文件错误：检查config.yaml格式
- 模型文件缺失：确认models目录下文件完整

### 6.3 数据库连接失败

**症状**: Web服务无法连接数据库

**解决方案**:
```bash
# 检查数据库容器状态
docker logs xiaozhi-esp32-server-db

# 检查网络连通性
docker exec xiaozhi-esp32-server-web ping xiaozhi-esp32-server-db

# 重置数据库密码
docker exec -it xiaozhi-esp32-server-db mysql -uroot -p
ALTER USER 'root'@'%' IDENTIFIED BY '123456';
FLUSH PRIVILEGES;
```

### 6.4 端口冲突

**症状**: 端口绑定失败

**解决方案**:
```bash
# 检查端口占用
netstat -tlnp | grep 8000
netstat -tlnp | grep 8002
netstat -tlnp | grep 8003

# 关闭占用端口的进程或修改docker-compose端口映射
vi docker-compose-offline.yml
# 修改 "8000:8000" 为 "8100:8000" 等
```

### 6.5 性能问题

**症状**: 服务响应缓慢

**优化建议**:
```bash
# 增加Docker资源限制（docker-compose.yml）
services:
  xiaozhi-esp32-server:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G

# 调整MySQL性能参数
# 调整Redis内存限制
```

### 6.6 工具函数不生效

**症状**: 新增的工具函数无法调用

**排查步骤**:
```bash
# 1. 确认文件已打包
docker exec xiaozhi-esp32-server ls -l /opt/xiaozhi-esp32-server/plugins_func/functions/

# 2. 检查Python依赖
docker exec xiaozhi-esp32-server pip list

# 3. 查看应用日志
docker logs xiaozhi-esp32-server | grep -i error

# 4. 手动测试工具函数
docker exec -it xiaozhi-esp32-server python
>>> from plugins_func.functions.get_temperature_load_rate import *
>>> # 测试函数调用
```

### 6.7 防火墙问题

**症状**: 外部无法访问服务

**解决方案**:
```bash
# CentOS 7
firewall-cmd --zone=public --add-port=8000/tcp --permanent
firewall-cmd --zone=public --add-port=8002/tcp --permanent
firewall-cmd --zone=public --add-port=8003/tcp --permanent
firewall-cmd --reload

# CentOS 8
firewall-cmd --zone=public --add-port=8000/tcp --permanent
firewall-cmd --zone=public --add-port=8002/tcp --permanent
firewall-cmd --zone=public --add-port=8003/tcp --permanent
firewall-cmd --reload

# 或临时关闭防火墙测试
systemctl stop firewalld
```

---

## 七、服务管理

### 7.1 常用命令

```bash
# 启动所有服务
docker-compose -f docker-compose-offline.yml up -d

# 停止所有服务
docker-compose -f docker-compose-offline.yml down

# 重启服务
docker-compose -f docker-compose-offline.yml restart

# 查看服务状态
docker-compose -f docker-compose-offline.yml ps

# 查看实时日志
docker-compose -f docker-compose-offline.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose-offline.yml logs -f xiaozhi-esp32-server

# 进入容器
docker exec -it xiaozhi-esp32-server bash

# 更新服务配置后重启
docker-compose -f docker-compose-offline.yml up -d --force-recreate
```

### 7.2 数据备份

```bash
# 备份配置文件
tar -czf backup-config-$(date +%Y%m%d).tar.gz data/ config*.yaml

# 备份数据库
docker exec xiaozhi-esp32-server-db mysqldump -uroot -p123456 xiaozhi_esp32_server > backup-db-$(date +%Y%m%d).sql

# 备份上传文件
tar -czf backup-uploadfile-$(date +%Y%m%d).tar.gz uploadfile/

# 定期备份脚本（添加到crontab）
0 2 * * * /root/offline-package/scripts/backup.sh
```

### 7.3 系统监控

```bash
# 查看容器资源使用
docker stats

# 查看磁盘使用
df -h

# 查看Docker磁盘使用
docker system df

# 清理未使用的镜像和容器
docker system prune -a
```

---

## 八、升级与维护

### 8.1 版本升级

当有新版本时：

1. 按照"二、在线环境准备与打包"重新打包新版本
2. 备份现有数据
3. 停止旧版本服务
4. 加载新镜像
5. 启动新版本服务

### 8.2 配置更新

```bash
# 修改配置
vi data/config.yaml

# 重启服务使配置生效
docker-compose -f docker-compose-offline.yml restart xiaozhi-esp32-server
```

### 8.3 日志管理

```bash
# 限制日志大小（修改docker-compose.yml）
services:
  xiaozhi-esp32-server:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## 九、附录

### 9.1 目录结构说明

```
offline-package/
├── images/                          # Docker镜像文件
│   ├── server.tar
│   ├── web.tar
│   ├── mysql.tar
│   └── redis.tar
├── docker-compose-offline.yml       # 离线部署配置
├── offline-deploy.sh                # 自动部署脚本
├── install-docker-centos.sh         # Docker安装脚本
├── data/                            # 应用数据目录
│   └── config.yaml                  # 主配置文件
├── mysql/                           # MySQL数据目录
│   └── data/
├── uploadfile/                      # 上传文件目录
├── models/                          # AI模型文件
│   └── SenseVoiceSmall/
└── README.txt                       # 快速部署说明
```

### 9.2 端口映射清单

| 服务 | 容器端口 | 主机端口 | 说明 |
|------|---------|---------|------|
| xiaozhi-esp32-server | 8000 | 8000 | WebSocket服务 |
| xiaozhi-esp32-server | 8003 | 8003 | HTTP服务/视觉分析 |
| xiaozhi-esp32-server-web | 8002 | 8002 | Web管理控制台 |
| xiaozhi-esp32-server-db | 3306 | - | MySQL数据库（内部） |
| xiaozhi-esp32-server-redis | 6379 | - | Redis缓存（内部） |

### 9.3 环境变量清单

关键环境变量说明：

```yaml
# 数据库配置
SPRING_DATASOURCE_DRUID_URL: jdbc:mysql://xiaozhi-esp32-server-db:3306/xiaozhi_esp32_server
SPRING_DATASOURCE_DRUID_USERNAME: root
SPRING_DATASOURCE_DRUID_PASSWORD: 123456

# Redis配置
SPRING_DATA_REDIS_HOST: xiaozhi-esp32-server-redis
SPRING_DATA_REDIS_PORT: 6379
SPRING_DATA_REDIS_PASSWORD: ""

# 时区配置
TZ: Asia/Shanghai
```

### 9.4 联系与支持

- 项目地址: https://github.com/xinnan-tech/xiaozhi-esp32-server
- 问题反馈: 提交Issue到GitHub仓库
- 技术文档: 查看docs目录下的其他文档

---

**祝您部署顺利！**

如有问题，请参考常见问题排查章节或联系技术支持。

