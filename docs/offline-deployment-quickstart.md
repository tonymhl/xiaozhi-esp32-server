# 小智ESP32服务器 - 离线部署快速指南

> 这是一份精简的快速部署指南，完整详细的说明请参考 [offline-deployment-guide.md](offline-deployment-guide.md)

---

## 🚀 5分钟快速部署

### 第一步：在线环境打包（有网络的机器）

**Windows:**
```powershell
cd xiaozhi-esp32-server
.\scripts\offline-package.ps1
```

**Linux/Mac:**
```bash
cd xiaozhi-esp32-server
chmod +x scripts/offline-package.sh
./scripts/offline-package.sh
```

完成后得到：`xiaozhi-offline-deployment-YYYYMMDD-HHMMSS.tar.gz`

---

### 第二步：传输到目标服务器

```bash
# 方式1: SCP传输
scp xiaozhi-offline-deployment-*.tar.gz root@目标服务器IP:/root/

# 方式2: U盘拷贝
# 将文件复制到U盘，然后插入目标服务器
```

---

### 第三步：离线部署（CentOS服务器）

```bash
# 1. 解压
cd /root
tar -xzf xiaozhi-offline-deployment-*.tar.gz
cd xiaozhi-offline-deployment-*/

# 2. 安装Docker（如未安装）
chmod +x install-docker-centos.sh
sudo ./install-docker-centos.sh

# 3. 一键部署
chmod +x offline-deploy.sh
sudo ./offline-deploy.sh
```

等待3-5分钟，部署完成！

---

### 第四步：访问服务

打开浏览器访问：
```
http://服务器IP:8002
```

---

## 📋 常用命令

```bash
# 查看服务状态
docker-compose -f docker-compose-offline.yml ps

# 查看日志
docker-compose -f docker-compose-offline.yml logs -f

# 重启服务
docker-compose -f docker-compose-offline.yml restart

# 停止服务
docker-compose -f docker-compose-offline.yml down

# 启动服务
docker-compose -f docker-compose-offline.yml up -d
```

---

## 🔧 快速配置修改

### 修改端口（如果端口冲突）

编辑 `docker-compose-offline.yml`：
```yaml
ports:
  - "8100:8000"  # 将8000改为8100
  - "8102:8002"  # 将8002改为8102
```

### 修改数据库密码

编辑 `docker-compose-offline.yml`：
```yaml
environment:
  - MYSQL_ROOT_PASSWORD=你的新密码
```

### 修改应用配置

编辑 `data/config.yaml`，然后重启服务。

---

## ❓ 常见问题

### 问题1: 端口被占用
```bash
# 查看端口占用
netstat -tlnp | grep 8000

# 方案：修改docker-compose中的端口映射
```

### 问题2: 容器启动失败
```bash
# 查看详细日志
docker logs xiaozhi-esp32-server

# 检查目录权限
chmod -R 777 mysql/data
```

### 问题3: 无法访问Web界面
```bash
# 检查防火墙
firewall-cmd --list-ports

# 开放端口
firewall-cmd --zone=public --add-port=8002/tcp --permanent
firewall-cmd --reload
```

### 问题4: 数据库连接失败
```bash
# 等待数据库初始化（首次启动需要1-3分钟）
docker logs xiaozhi-esp32-server-db

# 检查数据库状态
docker exec xiaozhi-esp32-server-db mysqladmin ping -h localhost
```

---

## 📞 获取帮助

- 详细部署指南: [offline-deployment-guide.md](offline-deployment-guide.md)
- 检查清单: [offline-deployment-checklist.md](offline-deployment-checklist.md)
- 项目文档: https://github.com/xinnan-tech/xiaozhi-esp32-server/tree/main/docs
- 问题反馈: https://github.com/xinnan-tech/xiaozhi-esp32-server/issues

---

## ✅ 验证部署成功

运行以下命令，如果都返回正常则部署成功：

```bash
# 1. 检查容器
docker ps | grep xiaozhi
# 应该看到4个容器都在运行

# 2. 测试Web服务
curl http://localhost:8002
# 应该返回HTML内容

# 3. 测试数据库
docker exec xiaozhi-esp32-server-db mysql -uroot -p123456 -e "SHOW DATABASES;"
# 应该看到xiaozhi_esp32_server数据库

# 4. 检查工具函数
docker exec xiaozhi-esp32-server ls -l /opt/xiaozhi-esp32-server/plugins_func/functions/
# 应该看到你的工具函数文件
```

---

**恭喜！部署完成！** 🎉

