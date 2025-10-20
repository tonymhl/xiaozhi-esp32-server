##############################################################################
# 小智ESP32服务器 - 仅重新打包 Web 镜像
# 用途: 快速重新构建和导出 Web 镜像
##############################################################################

$ErrorActionPreference = "Stop"

# 颜色输出函数
function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Print-Info    { param([string]$Message) Write-ColorOutput "[INFO] $Message" "Cyan" }
function Print-Success { param([string]$Message) Write-ColorOutput "[SUCCESS] $Message" "Green" }
function Print-Error   { param([string]$Message) Write-ColorOutput "[ERROR] $Message" "Red" }
function Print-Title   { 
    param([string]$Title)
    Write-Host ""
    Write-ColorOutput "================================================" "Green"
    Write-ColorOutput "  $Title" "Green"
    Write-ColorOutput "================================================" "Green"
    Write-Host ""
}

# 获取项目根目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outputDir = Join-Path $projectRoot "web-image-$timestamp"

Print-Title "小智ESP32服务器 - Web 镜像重新打包工具"

# 检查 Docker
Print-Info "检查 Docker..."
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Print-Error "Docker 未安装"
    exit 1
}

# 创建输出目录
Print-Info "创建输出目录: $outputDir"
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

# 清理旧的 web 镜像和缓存
Print-Title "清理旧镜像和缓存"
Print-Info "删除旧的 web 镜像..."
docker rmi xiaozhi-esp32-server:web_custom -f 2>$null

Print-Info "清理构建缓存..."
docker builder prune -f

# 重新构建 web 镜像
Print-Title "构建 Web 镜像"
Set-Location $projectRoot

Print-Info "开始构建 xiaozhi-esp32-server-web 镜像..."
Print-Info "这可能需要 5-10 分钟，请耐心等待..."

docker build --no-cache -t xiaozhi-esp32-server:web_custom -f .\Dockerfile-web .

if ($LASTEXITCODE -ne 0) {
    Print-Error "镜像构建失败"
    exit 1
}

Print-Success "镜像构建完成"

# 导出镜像
Print-Title "导出镜像"
$tarFile = Join-Path $outputDir "web.tar"

Print-Info "导出 web 镜像到: $tarFile"
docker save xiaozhi-esp32-server:web_custom -o $tarFile

Print-Success "镜像导出完成"

# 生成 MD5 校验
Print-Info "生成 MD5 校验和..."
$hash = Get-FileHash -Path $tarFile -Algorithm MD5
$checksumContent = "$($hash.Hash.ToLower())  web.tar`n"
$checksumFile = Join-Path $outputDir "web.tar.md5"
[System.IO.File]::WriteAllText($checksumFile, $checksumContent, [System.Text.UTF8Encoding]::new($false))

# 生成部署脚本
$deployScript = @'
#!/bin/bash
##############################################################################
# Web 镜像更新脚本
##############################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  小智ESP32服务器 - Web 镜像更新工具${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# 检查文件
if [ ! -f "web.tar" ]; then
    echo -e "${RED}[ERROR]${NC} web.tar 文件不存在"
    exit 1
fi

# MD5 校验
if [ -f "web.tar.md5" ]; then
    echo -e "${BLUE}[INFO]${NC} 验证镜像完整性..."
    if md5sum -c web.tar.md5 --quiet 2>/dev/null; then
        echo -e "${GREEN}[SUCCESS]${NC} 镜像文件校验通过"
    else
        echo -e "${YELLOW}[WARNING]${NC} MD5 校验失败，但继续执行"
    fi
fi

# 停止 web 容器
echo -e "${BLUE}[INFO]${NC} 停止 web 容器..."
docker-compose -f docker-compose-offline.yml stop xiaozhi-esp32-server-web 2>/dev/null || \
    docker stop xiaozhi-esp32-server-web 2>/dev/null || true

# 删除旧镜像
echo -e "${BLUE}[INFO]${NC} 删除旧的 web 镜像..."
docker rmi xiaozhi-esp32-server:web_custom -f 2>/dev/null || true

# 加载新镜像
echo -e "${BLUE}[INFO]${NC} 加载新的 web 镜像..."
docker load -i web.tar

# 验证镜像加载
if docker images | grep -q "xiaozhi-esp32-server.*web_custom"; then
    echo -e "${GREEN}[SUCCESS]${NC} 新镜像加载成功"
else
    echo -e "${RED}[ERROR]${NC} 镜像加载失败"
    exit 1
fi

# 重新启动容器
echo -e "${BLUE}[INFO]${NC} 重新启动 web 容器..."
docker-compose -f docker-compose-offline.yml up -d xiaozhi-esp32-server-web

# 等待启动
echo -e "${BLUE}[INFO]${NC} 等待容器启动..."
sleep 5

# 检查状态
if docker ps | grep -q xiaozhi-esp32-server-web; then
    echo ""
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}  ✓ Web 镜像更新成功！${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo ""
    echo -e "${BLUE}查看日志:${NC} docker logs -f xiaozhi-esp32-server-web"
    echo ""
else
    echo -e "${RED}[ERROR]${NC} 容器启动失败，请查看日志"
    docker logs xiaozhi-esp32-server-web
    exit 1
fi
'@

$deployScriptFile = Join-Path $outputDir "update-web-image.sh"
Set-Content -Path $deployScriptFile -Value $deployScript -Encoding UTF8

# 生成 README
$readmeContent = @"
# Web 镜像更新包

生成时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

## 文件清单

- web.tar         : Web 镜像文件
- web.tar.md5     : MD5 校验文件
- update-web-image.sh : 自动更新脚本

## 使用步骤

### 1. 传输到 CentOS 服务器

``````powershell
scp -r web-image-$timestamp root@服务器IP:/root/
``````

### 2. 在 CentOS 上执行更新

``````bash
cd /root/web-image-$timestamp

# 转换脚本换行符
sed -i 's/\r`$`$//' update-web-image.sh

# 添加执行权限
chmod +x update-web-image.sh

# 进入部署目录
cd ~/xiaozhi-offline-deployment-*/

# 复制镜像文件
cp /root/web-image-$timestamp/web.tar ./images/
cp /root/web-image-$timestamp/web.tar.md5 ./images/

# 执行更新
/root/web-image-$timestamp/update-web-image.sh
``````

### 3. 验证

``````bash
# 查看日志
docker logs -f xiaozhi-esp32-server-web

# 访问 Web 界面
# http://服务器IP:8002
``````

## 注意事项

1. 更新前会自动停止 web 容器
2. 数据库和其他服务不受影响
3. 上传文件目录（uploadfile）不受影响
4. 更新过程约 2-3 分钟

## 回滚

如果更新后有问题，可以回滚到旧镜像：

``````bash
# 停止容器
docker-compose -f docker-compose-offline.yml stop xiaozhi-esp32-server-web

# 加载旧镜像（从原始部署包）
cd ~/xiaozhi-offline-deployment-*/images
docker load -i web.tar

# 重启容器
docker-compose -f docker-compose-offline.yml up -d xiaozhi-esp32-server-web
``````
"@

$readmeFile = Join-Path $outputDir "README.txt"
Set-Content -Path $readmeFile -Value $readmeContent -Encoding UTF8

# 显示总结
Print-Title "打包完成"

$fileSize = (Get-Item $tarFile).Length / 1GB

Write-Host ""
Write-ColorOutput "✓ Web 镜像打包成功！" "Green"
Write-Host ""
Write-Host "输出目录: " -NoNewline
Write-ColorOutput $outputDir "Cyan"
Write-Host "镜像文件: " -NoNewline
Write-ColorOutput "web.tar ($("{0:N2}" -f $fileSize) GB)" "Cyan"
Write-Host ""
Write-ColorOutput "下一步操作:" "Yellow"
Write-Host "  1. 将 $outputDir 传输到 CentOS 服务器"
Write-Host "  2. 在服务器上执行 update-web-image.sh"
Write-Host ""
Write-ColorOutput "传输命令:" "Green"
Write-Host "  scp -r $outputDir root@服务器IP:/root/"
Write-Host ""

