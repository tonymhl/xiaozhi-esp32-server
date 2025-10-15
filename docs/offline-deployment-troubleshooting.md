# 小智ESP32服务器 - 离线部署故障排查手册

本文档提供离线部署过程中常见问题的详细排查步骤和解决方案。

---

## 📋 目录

- [一、打包阶段问题](#一打包阶段问题)
- [二、传输阶段问题](#二传输阶段问题)
- [三、部署阶段问题](#三部署阶段问题)
- [四、运行时问题](#四运行时问题)
- [五、性能问题](#五性能问题)
- [六、数据问题](#六数据问题)

---

## 一、打包阶段问题

### 1.1 Docker编译镜像失败

**症状**:
```
Error response from daemon: failed to build...
```

**可能原因**:
1. Docker守护进程未运行
2. Dockerfile路径错误
3. 磁盘空间不足
4. 网络问题导致依赖下载失败
5. 基础镜像拉取失败

**排查步骤**:

```bash
# 1. 检查Docker状态
systemctl status docker
docker ps

# 2. 检查磁盘空间
df -h
docker system df

# 3. 清理Docker缓存
docker system prune -a

# 4. 手动拉取基础镜像
docker pull python:3.10-slim
docker pull node:18
docker pull maven:3.9.4-eclipse-temurin-21

# 5. 查看详细构建日志
docker build -t xiaozhi-esp32-server:server_custom -f ./Dockerfile-server . --progress=plain
```

**解决方案**:

```bash
# 方案1: 重启Docker服务
sudo systemctl restart docker

# 方案2: 增加Docker资源限制（Docker Desktop）
# 在Docker Desktop设置中增加内存和CPU配额

# 方案3: 使用国内镜像源
# 编辑 /etc/docker/daemon.json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}
sudo systemctl restart docker

# 方案4: 清理空间后重试
docker image prune -a
docker volume prune
```

---

### 1.2 Python依赖安装失败

**症状**:
```
ERROR: Could not find a version that satisfies the requirement...
```

**可能原因**:
1. PyPI源连接超时
2. 包版本不兼容
3. 网络问题

**排查步骤**:

```bash
# 1. 检查requirements.txt
cat main/xiaozhi-server/requirements.txt

# 2. 测试pip连接
pip install --index-url https://mirrors.aliyun.com/pypi/simple/ requests

# 3. 单独测试安装失败的包
pip install package_name==version --verbose
```

**解决方案**:

```bash
# 方案1: 在Dockerfile中增加重试和超时
RUN pip install --no-cache-dir -r requirements.txt \
    --default-timeout=120 \
    --retries 5 \
    --index-url https://mirrors.aliyun.com/pypi/simple/

# 方案2: 使用国内源
# 已在Dockerfile中配置，无需修改

# 方案3: 分步安装
# 将大包先安装
RUN pip install torch==2.2.2
RUN pip install -r requirements.txt
```

---

### 1.3 NPM包安装失败

**症状**:
```
npm ERR! network timeout
npm ERR! fetch failed
```

**可能原因**:
1. NPM源连接慢
2. 网络不稳定
3. 包版本冲突

**排查步骤**:

```bash
# 1. 检查package.json
cat main/manager-web/package.json

# 2. 测试npm连接
npm config get registry

# 3. 清理npm缓存
npm cache clean --force
```

**解决方案**:

```bash
# 方案1: 使用淘宝镜像
npm config set registry https://registry.npmmirror.com

# 方案2: 在Dockerfile中添加
RUN npm config set registry https://registry.npmmirror.com && \
    npm install --verbose

# 方案3: 增加超时时间
RUN npm install --timeout=300000
```

---

### 1.4 镜像导出失败

**症状**:
```
Error response from daemon: write /var/lib/docker/...: no space left on device
```

**可能原因**:
1. 磁盘空间不足
2. 镜像过大
3. 临时目录空间不足

**排查步骤**:

```bash
# 1. 检查磁盘空间
df -h
du -sh offline-package/

# 2. 检查镜像大小
docker images xiaozhi-esp32-server

# 3. 检查Docker数据目录
docker info | grep "Docker Root Dir"
df -h $(docker info | grep "Docker Root Dir" | cut -d: -f2)
```

**解决方案**:

```bash
# 方案1: 清理空间
docker system prune -a --volumes
rm -rf /tmp/*

# 方案2: 修改Docker数据目录
# 将Docker移到空间更大的分区

# 方案3: 分批导出和压缩
docker save xiaozhi-esp32-server:server_custom | gzip > server.tar.gz
```

---

## 二、传输阶段问题

### 2.1 文件传输中断

**症状**:
```
Connection reset by peer
Broken pipe
```

**可能原因**:
1. 网络不稳定
2. 文件过大
3. SSH超时设置

**解决方案**:

```bash
# 方案1: 使用rsync断点续传
rsync -avz --partial --progress \
    xiaozhi-offline-deployment-*.tar.gz \
    root@目标服务器:/root/

# 方案2: 分卷压缩传输
# 打包时分卷
tar czf - offline-package/ | split -b 2G - xiaozhi-deployment-part-

# 传输
scp xiaozhi-deployment-part-* root@目标服务器:/root/

# 目标服务器上合并
cat xiaozhi-deployment-part-* | tar xzf -

# 方案3: 修改SSH超时设置
# 在 ~/.ssh/config 添加
Host *
    ServerAliveInterval 60
    ServerAliveCountMax 10
```

---

### 2.2 文件校验失败

**症状**:
```
md5sum: WARNING: 1 computed checksum did NOT match
```

**可能原因**:
1. 传输过程中文件损坏
2. 传输模式错误（文本/二进制）
3. 存储介质故障

**排查步骤**:

```bash
# 1. 比对原始文件和目标文件
md5sum source.tar.gz
ssh root@目标服务器 "md5sum /root/source.tar.gz"

# 2. 检查文件大小
ls -lh source.tar.gz
ssh root@目标服务器 "ls -lh /root/source.tar.gz"

# 3. 测试文件解压
tar -tzf source.tar.gz > /dev/null
```

**解决方案**:

```bash
# 方案1: 重新传输文件
rm 损坏的文件
重新scp

# 方案2: 使用校验和验证传输
scp -o "Compression=yes" -o "CheckHostIP=yes" ...

# 方案3: 使用U盘传输
# 避免网络传输问题
```

---

## 三、部署阶段问题

### 3.1 Docker未安装或启动失败

**症状**:
```
docker: command not found
Failed to start docker.service
```

**排查步骤**:

```bash
# 1. 检查Docker安装
which docker
docker --version

# 2. 检查Docker服务
systemctl status docker
journalctl -u docker -n 50

# 3. 检查系统版本
cat /etc/os-release
uname -r
```

**解决方案**:

```bash
# 方案1: 使用安装脚本
chmod +x install-docker-centos.sh
sudo ./install-docker-centos.sh

# 方案2: 手动安装
# CentOS 7/8
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io

# 方案3: 启动Docker
sudo systemctl start docker
sudo systemctl enable docker

# 方案4: 检查内核版本（Docker需要3.10+）
uname -r
# 如果版本过低，需要升级内核
```

---

### 3.2 镜像加载失败

**症状**:
```
Error processing tar file(exit status 1): unexpected EOF
```

**可能原因**:
1. tar文件损坏
2. 磁盘空间不足
3. 权限问题

**排查步骤**:

```bash
# 1. 验证tar文件完整性
tar -tzf images/server.tar > /dev/null
echo $?  # 返回0表示正常

# 2. 检查磁盘空间
df -h

# 3. 验证MD5
cd images/
md5sum -c checksums.md5

# 4. 查看Docker日志
journalctl -u docker -n 100
```

**解决方案**:

```bash
# 方案1: 重新传输损坏的tar文件

# 方案2: 清理空间
docker system prune -a
rm -rf /var/lib/docker/tmp/*

# 方案3: 手动加载
docker load < images/server.tar --verbose

# 方案4: 检查文件权限
chmod 644 images/*.tar
```

---

### 3.3 容器启动失败

**症状**:
```
Error starting userland proxy: listen tcp4 0.0.0.0:8000: bind: address already in use
```

**可能原因**:
1. 端口被占用
2. 数据卷权限问题
3. 配置文件错误
4. 依赖服务未就绪

**排查步骤**:

```bash
# 1. 检查端口占用
netstat -tlnp | grep 8000
lsof -i :8000

# 2. 查看容器日志
docker logs xiaozhi-esp32-server
docker logs xiaozhi-esp32-server-web
docker logs xiaozhi-esp32-server-db

# 3. 检查数据卷
ls -la mysql/data/
ls -la data/

# 4. 检查配置文件
cat docker-compose-offline.yml
cat data/config.yaml

# 5. 查看容器详细信息
docker inspect xiaozhi-esp32-server
```

**解决方案**:

```bash
# 方案1: 释放端口
# 找到占用端口的进程
netstat -tlnp | grep 8000
# 停止该进程
kill -9 PID

# 方案2: 修改端口映射
# 编辑docker-compose-offline.yml
ports:
  - "8100:8000"  # 改用8100

# 方案3: 修复权限
chmod -R 755 data/
chmod -R 777 mysql/data/

# 方案4: 等待依赖服务
# MySQL需要初始化时间
docker logs -f xiaozhi-esp32-server-db
# 等待出现 "ready for connections"

# 方案5: 强制重新创建
docker-compose -f docker-compose-offline.yml down -v
docker-compose -f docker-compose-offline.yml up -d
```

---

### 3.4 数据库初始化失败

**症状**:
```
ERROR 2002 (HY000): Can't connect to MySQL server
Access denied for user 'root'
```

**排查步骤**:

```bash
# 1. 检查MySQL容器状态
docker ps | grep mysql
docker logs xiaozhi-esp32-server-db

# 2. 检查MySQL进程
docker exec xiaozhi-esp32-server-db ps aux | grep mysql

# 3. 检查数据目录
ls -la mysql/data/

# 4. 测试连接
docker exec xiaozhi-esp32-server-db mysqladmin ping -h localhost

# 5. 检查配置
docker exec xiaozhi-esp32-server-db env | grep MYSQL
```

**解决方案**:

```bash
# 方案1: 等待初始化完成（首次启动需1-3分钟）
docker logs -f xiaozhi-esp32-server-db
# 等待 "[Server] X Plugin ready for connections"

# 方案2: 重置数据库
docker-compose -f docker-compose-offline.yml down
rm -rf mysql/data/*
docker-compose -f docker-compose-offline.yml up -d

# 方案3: 手动初始化
docker exec -it xiaozhi-esp32-server-db bash
mysql -uroot -p123456
CREATE DATABASE IF NOT EXISTS xiaozhi_esp32_server;
exit

# 方案4: 检查密码配置
# 确保docker-compose中的密码一致
MYSQL_ROOT_PASSWORD: 123456
SPRING_DATASOURCE_DRUID_PASSWORD: 123456

# 方案5: 导入初始数据
docker exec -i xiaozhi-esp32-server-db mysql -uroot -p123456 xiaozhi_esp32_server < init.sql
```

---

## 四、运行时问题

### 4.1 WebSocket连接失败

**症状**:
```
WebSocket connection failed
Connection refused
```

**排查步骤**:

```bash
# 1. 检查服务状态
docker ps | grep xiaozhi-esp32-server
docker logs xiaozhi-esp32-server

# 2. 检查端口监听
netstat -tlnp | grep 8000
ss -tlnp | grep 8000

# 3. 测试连接
telnet localhost 8000
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost:8000

# 4. 检查防火墙
firewall-cmd --list-ports
iptables -L -n | grep 8000

# 5. 检查配置
docker exec xiaozhi-esp32-server cat /opt/xiaozhi-esp32-server/data/config.yaml | grep -A5 server
```

**解决方案**:

```bash
# 方案1: 开放防火墙端口
firewall-cmd --zone=public --add-port=8000/tcp --permanent
firewall-cmd --reload

# 方案2: 检查配置文件
# 编辑 data/config.yaml
server:
  host: 0.0.0.0  # 确保监听所有接口
  port: 8000

# 重启服务
docker-compose -f docker-compose-offline.yml restart xiaozhi-esp32-server

# 方案3: 检查SELinux
sestatus
# 如果开启，可能需要配置策略或临时关闭
setenforce 0

# 方案4: 查看应用日志
docker exec xiaozhi-esp32-server tail -f /opt/xiaozhi-esp32-server/data/logs/app.log
```

---

### 4.2 工具函数调用失败

**症状**:
```
ModuleNotFoundError: No module named 'xxx'
Function not found
AttributeError
```

**排查步骤**:

```bash
# 1. 检查工具函数文件
docker exec xiaozhi-esp32-server ls -l /opt/xiaozhi-esp32-server/plugins_func/functions/
docker exec xiaozhi-esp32-server cat /opt/xiaozhi-esp32-server/plugins_func/functions/get_temperature_load_rate.py

# 2. 检查Python依赖
docker exec xiaozhi-esp32-server pip list
docker exec xiaozhi-esp32-server python -c "import psutil; print(psutil.__version__)"

# 3. 测试导入
docker exec xiaozhi-esp32-server python -c "from plugins_func.functions.get_temperature_load_rate import *"

# 4. 查看应用日志
docker logs xiaozhi-esp32-server | grep -i error
docker logs xiaozhi-esp32-server | grep -i function

# 5. 检查文件权限
docker exec xiaozhi-esp32-server ls -l /opt/xiaozhi-esp32-server/plugins_func/functions/
```

**解决方案**:

```bash
# 方案1: 重新打包镜像（包含新工具函数）
# 在开发机器上
./scripts/offline-package.sh

# 方案2: 临时挂载工具函数
# 修改docker-compose-offline.yml，添加卷挂载
volumes:
  - ./custom_functions:/opt/xiaozhi-esp32-server/plugins_func/functions/

# 方案3: 安装缺失的依赖
docker exec xiaozhi-esp32-server pip install 缺失的包名

# 方案4: 手动复制文件到容器
docker cp local_function.py xiaozhi-esp32-server:/opt/xiaozhi-esp32-server/plugins_func/functions/

# 重启容器使更改生效
docker restart xiaozhi-esp32-server

# 方案5: 检查函数注册
# 确保工具函数在config.yaml中正确配置
```

---

### 4.3 内存溢出

**症状**:
```
OOMKilled
Container exited with code 137
```

**排查步骤**:

```bash
# 1. 检查系统内存
free -h
vmstat 1 10

# 2. 检查容器资源使用
docker stats

# 3. 查看OOM日志
dmesg | grep -i "out of memory"
journalctl -k | grep -i "killed process"

# 4. 检查容器资源限制
docker inspect xiaozhi-esp32-server | grep -i memory
```

**解决方案**:

```bash
# 方案1: 增加系统内存（硬件升级）

# 方案2: 增加swap空间
sudo dd if=/dev/zero of=/swapfile bs=1G count=4
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 方案3: 调整容器内存限制
# 编辑docker-compose-offline.yml
deploy:
  resources:
    limits:
      memory: 8G  # 增加限制

# 方案4: 优化应用配置
# 减少模型加载、批处理大小等

# 方案5: 分离服务
# 将server和web部署到不同机器
```

---

### 4.4 磁盘空间不足

**症状**:
```
no space left on device
ERROR 1114: The table is full
```

**排查步骤**:

```bash
# 1. 检查磁盘使用
df -h
du -sh /* | sort -h

# 2. 检查Docker空间
docker system df -v

# 3. 查找大文件
find / -type f -size +1G -exec ls -lh {} \;

# 4. 检查日志文件
du -sh /var/log/*
du -sh data/logs/
```

**解决方案**:

```bash
# 方案1: 清理Docker
docker system prune -a --volumes
docker image prune -a

# 方案2: 清理日志
# 手动清理
rm -f /var/log/*.log.1 /var/log/*.log.*.gz
rm -f data/logs/*.log.1

# 配置日志轮转（已在docker-compose中配置）

# 方案3: 清理MySQL binlog
docker exec xiaozhi-esp32-server-db mysql -uroot -p123456 -e "PURGE BINARY LOGS BEFORE DATE_SUB(NOW(), INTERVAL 7 DAY);"

# 方案4: 移动数据到其他分区
# 将mysql/data或uploadfile移到大分区
mv mysql/data /data/mysql
ln -s /data/mysql mysql/data

# 方案5: 配置数据定期清理
# 编写清理脚本定期执行
```

---

## 五、性能问题

### 5.1 响应速度慢

**症状**:
- Web界面加载慢
- API响应超时
- WebSocket延迟高

**排查步骤**:

```bash
# 1. 检查系统资源
top
htop
docker stats

# 2. 检查网络延迟
ping 服务器IP
traceroute 服务器IP

# 3. 检查数据库性能
docker exec xiaozhi-esp32-server-db mysql -uroot -p123456 -e "SHOW PROCESSLIST;"
docker exec xiaozhi-esp32-server-db mysql -uroot -p123456 -e "SHOW STATUS LIKE 'Threads_%';"

# 4. 检查Redis性能
docker exec xiaozhi-esp32-server-redis redis-cli INFO stats
docker exec xiaozhi-esp32-server-redis redis-cli SLOWLOG GET 10

# 5. 分析应用日志
docker logs xiaozhi-esp32-server | grep -i "slow\|timeout\|error"
```

**解决方案**:

```bash
# 方案1: 优化数据库
# 增加连接池大小
# 编辑docker-compose-offline.yml MySQL部分
command:
  - --max_connections=1000
  - --innodb_buffer_pool_size=1G

# 方案2: 优化Redis
docker exec xiaozhi-esp32-server-redis redis-cli CONFIG SET maxmemory 1gb

# 方案3: 增加资源限制
# 编辑docker-compose-offline.yml
deploy:
  resources:
    limits:
      cpus: '8'
      memory: 16G

# 方案4: 启用Nginx缓存（Web服务）
# 配置静态资源缓存

# 方案5: 数据库索引优化
# 分析慢查询，添加必要的索引
```

---

### 5.2 CPU使用率过高

**症状**:
```
CPU使用率持续>80%
系统卡顿
```

**排查步骤**:

```bash
# 1. 查看整体CPU
top -d 1
mpstat 1 10

# 2. 查看容器CPU
docker stats --no-stream

# 3. 查看进程详情
docker exec xiaozhi-esp32-server ps aux --sort=-pcpu | head
docker exec xiaozhi-esp32-server-web ps aux --sort=-pcpu | head

# 4. Python性能分析
docker exec xiaozhi-esp32-server python -m cProfile app.py

# 5. 查看系统负载
uptime
cat /proc/loadavg
```

**解决方案**:

```bash
# 方案1: 优化应用代码
# 分析CPU密集型操作，优化算法

# 方案2: 减少并发
# 限制同时处理的请求数

# 方案3: 使用多进程
# Python使用multiprocessing
# Java调整线程池大小

# 方案4: 升级硬件
# 增加CPU核心数

# 方案5: 分布式部署
# 使用负载均衡分散请求
```

---

## 六、数据问题

### 6.1 数据丢失

**症状**:
- 配置丢失
- 用户数据丢失
- 上传文件丢失

**排查步骤**:

```bash
# 1. 检查数据卷
docker inspect xiaozhi-esp32-server | grep -A 10 Mounts
docker inspect xiaozhi-esp32-server-db | grep -A 10 Mounts

# 2. 检查文件系统
ls -la data/
ls -la mysql/data/
ls -la uploadfile/

# 3. 检查备份
ls -la /backup/xiaozhi-esp32-server/

# 4. 查看容器日志
docker logs xiaozhi-esp32-server | grep -i "data\|file\|save"
```

**解决方案**:

```bash
# 方案1: 从备份恢复
# 恢复配置
tar -xzf backup/config_*.tar.gz -C .

# 恢复数据库
gunzip backup/database_*.sql.gz
docker exec -i xiaozhi-esp32-server-db mysql -uroot -p123456 xiaozhi_esp32_server < backup/database_*.sql

# 恢复上传文件
tar -xzf backup/uploadfile_*.tar.gz -C .

# 方案2: 确保数据卷正确挂载
# 检查docker-compose-offline.yml
volumes:
  - ./data:/opt/xiaozhi-esp32-server/data
  - ./mysql/data:/var/lib/mysql
  - ./uploadfile:/uploadfile

# 方案3: 配置自动备份
# 设置定时任务
crontab -e
0 2 * * * /root/offline-package/scripts/backup.sh
```

---

### 6.2 数据库损坏

**症状**:
```
Table 'xxx' is marked as crashed
Can't open file: 'xxx.MYI'
```

**排查步骤**:

```bash
# 1. 检查表状态
docker exec xiaozhi-esp32-server-db mysql -uroot -p123456 -e "CHECK TABLE xiaozhi_esp32_server.表名;"

# 2. 查看错误日志
docker logs xiaozhi-esp32-server-db | grep -i "error\|crash"

# 3. 检查磁盘
df -h
docker exec xiaozhi-esp32-server-db df -h
```

**解决方案**:

```bash
# 方案1: 修复表
docker exec xiaozhi-esp32-server-db mysql -uroot -p123456 -e "REPAIR TABLE xiaozhi_esp32_server.表名;"

# 方案2: 重建索引
docker exec xiaozhi-esp32-server-db mysql -uroot -p123456 xiaozhi_esp32_server -e "OPTIMIZE TABLE 表名;"

# 方案3: 从备份恢复
docker-compose -f docker-compose-offline.yml stop xiaozhi-esp32-server-db
rm -rf mysql/data/*
docker-compose -f docker-compose-offline.yml start xiaozhi-esp32-server-db
# 等待初始化完成
gunzip backup/database_*.sql.gz
docker exec -i xiaozhi-esp32-server-db mysql -uroot -p123456 xiaozhi_esp32_server < backup/database_*.sql

# 方案4: 使用myisamchk修复（MyISAM表）
docker exec xiaozhi-esp32-server-db bash
cd /var/lib/mysql/xiaozhi_esp32_server
myisamchk -r 表名.MYI
exit
docker restart xiaozhi-esp32-server-db
```

---

## 🔍 通用排查方法

### 系统信息收集

遇到问题时，首先收集以下信息：

```bash
#!/bin/bash
# 信息收集脚本

echo "=== 系统信息 ===" > troubleshoot.log
uname -a >> troubleshoot.log
cat /etc/os-release >> troubleshoot.log

echo -e "\n=== 资源使用 ===" >> troubleshoot.log
free -h >> troubleshoot.log
df -h >> troubleshoot.log
top -bn1 | head -20 >> troubleshoot.log

echo -e "\n=== Docker信息 ===" >> troubleshoot.log
docker --version >> troubleshoot.log
docker-compose --version >> troubleshoot.log
docker info >> troubleshoot.log
docker system df >> troubleshoot.log

echo -e "\n=== 容器状态 ===" >> troubleshoot.log
docker ps -a >> troubleshoot.log
docker stats --no-stream >> troubleshoot.log

echo -e "\n=== 容器日志 ===" >> troubleshoot.log
docker logs xiaozhi-esp32-server --tail 100 >> troubleshoot.log 2>&1
docker logs xiaozhi-esp32-server-web --tail 100 >> troubleshoot.log 2>&1
docker logs xiaozhi-esp32-server-db --tail 100 >> troubleshoot.log 2>&1
docker logs xiaozhi-esp32-server-redis --tail 100 >> troubleshoot.log 2>&1

echo -e "\n=== 网络信息 ===" >> troubleshoot.log
netstat -tlnp >> troubleshoot.log
ss -tlnp >> troubleshoot.log

echo -e "\n=== 防火墙 ===" >> troubleshoot.log
firewall-cmd --list-all >> troubleshoot.log 2>&1
iptables -L -n >> troubleshoot.log 2>&1

echo "信息已保存到 troubleshoot.log"
```

### 日志分析

```bash
# 实时查看所有服务日志
docker-compose -f docker-compose-offline.yml logs -f

# 查看特定服务日志
docker logs -f xiaozhi-esp32-server

# 搜索错误
docker logs xiaozhi-esp32-server 2>&1 | grep -i error

# 导出日志
docker logs xiaozhi-esp32-server > server.log 2>&1
```

---

## 📞 获取帮助

如果以上方法都无法解决问题：

1. 使用信息收集脚本生成 troubleshoot.log
2. 查看完整部署指南获取更多信息
3. 访问项目文档: https://github.com/xinnan-tech/xiaozhi-esp32-server/tree/main/docs
4. 提交Issue并附上 troubleshoot.log: https://github.com/xinnan-tech/xiaozhi-esp32-server/issues

---

**祝您顺利解决问题！**

