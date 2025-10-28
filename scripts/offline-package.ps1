##############################################################################
# 小智ESP32服务器 - 离线部署包自动打包脚本 (Windows PowerShell)
# 用途: 在有网络的环境中，一键打包所有需要的Docker镜像和配置文件
##############################################################################

# 设置错误时停止
$ErrorActionPreference = "Stop"

# 颜色输出函数
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Print-Info {
    param([string]$Message)
    Write-ColorOutput "[INFO] $Message" "Cyan"
}

function Print-Success {
    param([string]$Message)
    Write-ColorOutput "[SUCCESS] $Message" "Green"
}

function Print-Warning {
    param([string]$Message)
    Write-ColorOutput "[WARNING] $Message" "Yellow"
}

function Print-Error {
    param([string]$Message)
    Write-ColorOutput "[ERROR] $Message" "Red"
}

function Print-Title {
    param([string]$Title)
    Write-Host ""
    Write-ColorOutput "================================================" "Green"
    Write-ColorOutput "  $Title" "Green"
    Write-ColorOutput "================================================" "Green"
    Write-Host ""
}

# 检查命令是否存在
function Test-Command {
    param([string]$Command)

    $exists = $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
    return $exists
}

# 检查必要工具
function Test-Requirements {
    Print-Title "检查系统环境"

    Print-Info "检查Docker..."
    if (-not (Test-Command "docker")) {
        Print-Error "Docker未安装，请先安装Docker Desktop"
        exit 1
    }

    Print-Info "检查Docker Compose..."
    if (-not (Test-Command "docker-compose")) {
        Print-Error "Docker Compose未安装，请先安装Docker Desktop"
        exit 1
    }

    Print-Success "所有必要工具已就绪"
}

# 获取项目根目录
function Get-ProjectRoot {
    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    $projectRoot = Split-Path -Parent $scriptDir
    return $projectRoot
}

# 创建打包目录
function New-PackageDirectory {
    Print-Title "创建打包目录"

    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $global:PackageName = "xiaozhi-offline-deployment-$timestamp"
    $global:PackageDir = Join-Path $global:ProjectRoot $global:PackageName

    Print-Info "创建目录: $global:PackageDir"

    New-Item -ItemType Directory -Path $global:PackageDir -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $global:PackageDir "images") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $global:PackageDir "scripts") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $global:PackageDir "data") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $global:PackageDir "mysql\data") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $global:PackageDir "uploadfile") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $global:PackageDir "models\SenseVoiceSmall") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $global:PackageDir "redis\data") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $global:PackageDir "memory\mem_local_short") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $global:PackageDir "intent\intent_llm") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $global:PackageDir "docker-config") -Force | Out-Null

    Print-Success "打包目录创建完成"
}

# 编译Docker镜像
function Build-DockerImages {
    Print-Title "编译Docker镜像"

    Set-Location $global:ProjectRoot

    Print-Info "编译xiaozhi-esp32-server镜像（使用离线专用Dockerfile）..."
    if (Test-Path ".\Dockerfile-server-offline") {
        Print-Info "检测到Dockerfile-server-offline，使用离线构建方式"
        docker build -t xiaozhi-esp32-server:server_custom -f .\Dockerfile-server-offline .
    } else {
        Print-Warning "未找到Dockerfile-server-offline，使用标准Dockerfile-server"
        docker build -t xiaozhi-esp32-server:server_custom -f .\Dockerfile-server .
    }

    Print-Info "编译xiaozhi-esp32-server-web镜像..."
    docker build -t xiaozhi-esp32-server:web_custom -f .\Dockerfile-web .

    Print-Success "所有镜像编译完成"
}

# 拉取基础镜像
function Get-BaseImages {
    Print-Title "拉取基础镜像"

    Print-Info "拉取MySQL 8.0镜像（稳定版本）..."
    docker pull mysql:8.0

    Print-Info "拉取Redis镜像..."
    docker pull redis:latest

    Print-Success "基础镜像拉取完成"
}

# 导出Docker镜像
function Export-DockerImages {
    Print-Title "导出Docker镜像"

    $imagesDir = Join-Path $global:PackageDir "images"

    Print-Info "导出xiaozhi-esp32-server镜像..."
    docker save xiaozhi-esp32-server:server_custom -o (Join-Path $imagesDir "server.tar")

    Print-Info "导出xiaozhi-esp32-server-web镜像..."
    docker save xiaozhi-esp32-server:web_custom -o (Join-Path $imagesDir "web.tar")

    Print-Info "导出MySQL 8.0镜像..."
    docker save mysql:8.0 -o (Join-Path $imagesDir "mysql.tar")

    Print-Info "导出Redis镜像..."
    docker save redis:latest -o (Join-Path $imagesDir "redis.tar")

    Print-Success "所有镜像导出完成"
}

# 复制配置文件
function Copy-ConfigFiles {
    Print-Title "复制配置文件"

    Print-Info "复制docker-compose配置..."
    $composeSource = Join-Path $global:ProjectRoot "scripts\docker-compose-offline.template.yml"
    $composeDest = Join-Path $global:PackageDir "docker-compose-offline.yml"
    
    # 使用UTF8无BOM编码复制，确保不会出现乱码
    $content = Get-Content $composeSource -Raw -Encoding UTF8
    # 将CRLF转换为LF（Unix格式）
    $content = $content -replace "`r`n", "`n"
    [System.IO.File]::WriteAllText($composeDest, $content, [System.Text.UTF8Encoding]::new($false))
    Print-Success "已复制docker-compose-offline.yml（UTF8-LF格式）"

    Print-Info "复制应用配置文件..."
    
    # 复制主配置文件
    $configYaml = Join-Path $global:ProjectRoot "main\xiaozhi-server\config.yaml"
    if (Test-Path $configYaml) {
        Copy-Item $configYaml (Join-Path $global:PackageDir "data\") -Force
        Print-Success "已复制 config.yaml"
    }

    $configFromApi = Join-Path $global:ProjectRoot "main\xiaozhi-server\config_from_api.yaml"
    if (Test-Path $configFromApi) {
        Copy-Item $configFromApi (Join-Path $global:PackageDir "data\") -Force
        Print-Success "已复制 config_from_api.yaml"
    }
    
    # 复制data目录下的隐藏配置文件（如 .config.yaml, .wakeup_words.yaml）
    $dataDir = Join-Path $global:ProjectRoot "main\xiaozhi-server\data"
    if (Test-Path $dataDir) {
        Get-ChildItem -Path $dataDir -Filter ".*" -File -Force | ForEach-Object {
            Copy-Item $_.FullName (Join-Path $global:PackageDir "data\") -Force
            Print-Success "已复制 $($_.Name)"
        }
    }

    Print-Info "复制部署脚本..."
    Copy-Item (Join-Path $global:ProjectRoot "scripts\offline-deploy.sh") $global:PackageDir -Force
    Copy-Item (Join-Path $global:ProjectRoot "scripts\install-docker-centos.sh") $global:PackageDir -Force
    Copy-Item (Join-Path $global:ProjectRoot "scripts\backup.sh") (Join-Path $global:PackageDir "scripts\") -Force

    Print-Info "复制文档..."
    $docPath = Join-Path $global:ProjectRoot "docs\offline-deployment-guide.md"
    if (Test-Path $docPath) {
        Copy-Item $docPath $global:PackageDir -Force
    } else {
        Print-Warning "未找到离线部署指南文档"
    }

    Print-Info "复制模型文件..."
    $modelsDir = Join-Path $global:ProjectRoot "main\xiaozhi-server\models"
    if (Test-Path $modelsDir) {
        Copy-Item (Join-Path $modelsDir "*") (Join-Path $global:PackageDir "models\") -Recurse -Force -ErrorAction SilentlyContinue
        Print-Success "模型文件复制完成"
    } else {
        Print-Warning "没有找到模型文件，请手动添加"
    }

    Print-Info "复制工具函数目录（支持热更新）..."
    $pluginsFuncDir = Join-Path $global:ProjectRoot "main\xiaozhi-server\plugins_func"
    $targetPluginsFuncDir = Join-Path $global:PackageDir "plugins_func"
    if (Test-Path $pluginsFuncDir) {
        New-Item -ItemType Directory -Path $targetPluginsFuncDir -Force | Out-Null
        New-Item -ItemType Directory -Path (Join-Path $targetPluginsFuncDir "functions") -Force | Out-Null

        $functionsDir = Join-Path $pluginsFuncDir "functions"
        if (Test-Path $functionsDir) {
            Copy-Item (Join-Path $functionsDir "*.py") (Join-Path $targetPluginsFuncDir "functions\") -Force -ErrorAction SilentlyContinue
            Print-Success "已复制工具函数文件"
        }

        $registerFile = Join-Path $pluginsFuncDir "register.py"
        if (Test-Path $registerFile) {
            Copy-Item $registerFile $targetPluginsFuncDir -Force
            Print-Success "已复制register.py"
        }
    } else {
        Print-Warning "未找到plugins_func目录"
    }

    Print-Info "复制记忆模块（支持热更新）..."
    $memoryDir = Join-Path $global:ProjectRoot "main\xiaozhi-server\core\providers\memory\mem_local_short"
    if (Test-Path $memoryDir) {
        $memLocalShortFile = Join-Path $memoryDir "mem_local_short.py"
        if (Test-Path $memLocalShortFile) {
            Copy-Item $memLocalShortFile (Join-Path $global:PackageDir "memory\mem_local_short\") -Force
            Print-Success "已复制mem_local_short.py"
        }
    } else {
        Print-Warning "未找到memory模块"
    }

    Print-Info "复制Intent识别模块（支持热更新）..."
    $intentDir = Join-Path $global:ProjectRoot "main\xiaozhi-server\core\providers\intent\intent_llm"
    if (Test-Path $intentDir) {
        $intentLlmFile = Join-Path $intentDir "intent_llm.py"
        if (Test-Path $intentLlmFile) {
            Copy-Item $intentLlmFile (Join-Path $global:PackageDir "intent\intent_llm\") -Force
            Print-Success "已复制intent_llm.py"
        }
    } else {
        Print-Warning "未找到intent模块"
    }

    Print-Info "复制Docker配置文件（并转换换行符）..."
    $dockerConfigSource = Join-Path $global:ProjectRoot "docs\docker"
    if (Test-Path $dockerConfigSource) {
        # 复制nginx.conf
        $nginxConf = Join-Path $dockerConfigSource "nginx.conf"
        if (Test-Path $nginxConf) {
            $nginxContent = Get-Content $nginxConf -Raw -Encoding UTF8
            $nginxContent = $nginxContent -replace "`r`n", "`n"
            $nginxDest = Join-Path $global:PackageDir "docker-config\nginx.conf"
            [System.IO.File]::WriteAllText($nginxDest, $nginxContent, [System.Text.UTF8Encoding]::new($false))
            Print-Success "已复制nginx.conf（Unix LF格式）"
        }
        
        # 复制start.sh
        $startSh = Join-Path $dockerConfigSource "start.sh"
        if (Test-Path $startSh) {
            $startContent = Get-Content $startSh -Raw -Encoding UTF8
            $startContent = $startContent -replace "`r`n", "`n"
            $startDest = Join-Path $global:PackageDir "docker-config\start.sh"
            [System.IO.File]::WriteAllText($startDest, $startContent, [System.Text.UTF8Encoding]::new($false))
            Print-Success "已复制start.sh（Unix LF格式）"
        }
    } else {
        Print-Warning "未找到docker配置目录"
    }

    Print-Success "配置文件复制完成"
}

function Get-FileSizeGb {
    param([string]$Path)

    if (Test-Path $Path) {
        return (Get-Item $Path).Length / 1GB
    }
    return 0
}

function New-DeploymentManifest {
    Print-Title "生成部署清单"

    $imagesDir = Join-Path $global:PackageDir "images"
    $manifestFile = Join-Path $global:PackageDir "DEPLOYMENT-MANIFEST.txt"

    $serverSize = Get-FileSizeGb (Join-Path $imagesDir "server.tar")
    $webSize    = Get-FileSizeGb (Join-Path $imagesDir "web.tar")
    $mysqlSize  = Get-FileSizeGb (Join-Path $imagesDir "mysql.tar")
    $redisSize  = Get-FileSizeGb (Join-Path $imagesDir "redis.tar")

    $manifestContent = @(
        "========================================"
        "小智ESP32服务器 - 离线部署包清单"
        "========================================"
        ""
        "打包时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        "打包环境: Windows $([System.Environment]::OSVersion.Version)"
        ""
        "========================================"
        "镜像列表"
        "========================================"
        ""
        "镜像1: xiaozhi-esp32-server:server_custom"
        "   文件: images/server.tar"
        "   大小: $("{0:N2}" -f $serverSize) GB"
        "   说明: Python服务，包含所有工具函数"
        ""
        "镜像2: xiaozhi-esp32-server:web_custom"
        "   文件: images/web.tar"
        "   大小: $("{0:N2}" -f $webSize) GB"
        "   说明: Vue前端 + Java后端管理控制台"
        ""
        "镜像3: mysql:8.0"
        "   文件: images/mysql.tar"
        "   大小: $("{0:N2}" -f $mysqlSize) GB"
        "   说明: MySQL 8.0数据库（稳定版本）"
        ""
        "镜像4: redis:latest"
        "   文件: images/redis.tar"
        "   大小: $("{0:N2}" -f $redisSize) GB"
        "   说明: Redis缓存服务"
        ""
        "========================================"
        "配置文件"
        "========================================"
        ""
        "  docker-compose-offline.yml     : Docker Compose配置"
        "  data/config.yaml               : 主配置文件"
        "  data/config_from_api.yaml      : API配置文件"
        "  offline-deploy.sh              : 自动部署脚本"
        "  install-docker-centos.sh       : Docker安装脚本"
        "  scripts/backup.sh              : 数据备份脚本"
        "  offline-deployment-guide.md    : 详细部署指南"
        ""
        "========================================"
        "快速部署步骤"
        "========================================"
        ""
        "步骤1: 传输本压缩包到目标CentOS服务器"
        ""
        "步骤2: 解压"
        "   tar -xzf $global:PackageName.tar.gz"
        "   cd $global:PackageName"
        ""
        "步骤3: 安装Docker（如未安装）"
        "   chmod +x install-docker-centos.sh"
        "   sudo ./install-docker-centos.sh"
        ""
        "步骤4: 执行自动部署"
        "   chmod +x offline-deploy.sh"
        "   sudo ./offline-deploy.sh"
        ""
        "步骤5: 访问服务"
        "   Web管理界面: http://服务器IP:8002"
        "   WebSocket服务: ws://服务器IP:8000"
        "   HTTP服务: http://服务器IP:8003"
        ""
        "========================================"
        "注意事项"
        "========================================"
        ""
        "  确保目标服务器有至少8GB内存和50GB磁盘空间"
        "  首次启动需要1-3分钟初始化数据库"
        "  支持热更新：修改宿主机上的配置或工具函数后重启容器即可"
        "  详细部署说明请参考包内 offline-deployment-guide.md"
        ""
        "========================================"
        "技术支持"
        "========================================"
        ""
        "项目地址: https://github.com/xinnan-tech/xiaozhi-esp32-server"
        "文档地址: https://github.com/xinnan-tech/xiaozhi-esp32-server/tree/main/docs"
        ""
        "========================================"
    )

    $manifestContent -join "`r`n" | Set-Content -Path $manifestFile -Encoding UTF8

    Print-Success "部署清单生成完成"
}

# 生成快速README
function New-ReadmeFile {
    $readmeFile = Join-Path $global:PackageDir "README.txt"

    $readmeContent = @(
        "========================================"
        "小智ESP32服务器 - 离线部署包"
        "========================================"
        ""
        "快速部署步骤："
        ""
        "步骤1. 解压本包"
        "   tar -xzf xiaozhi-offline-deployment-*.tar.gz"
        ""
        "步骤2. 进入目录"
        "   cd xiaozhi-offline-deployment-*/"
        ""
        "步骤3. 安装Docker（如未安装）"
        "   chmod +x install-docker-centos.sh"
        "   sudo ./install-docker-centos.sh"
        ""
        "步骤4. 执行自动部署"
        "   chmod +x offline-deploy.sh"
        "   sudo ./offline-deploy.sh"
        ""
        "步骤5. 访问服务"
        "   http://服务器IP:8002"
        ""
        "详细部署指南请查看："
        "offline-deployment-guide.md"
        ""
        "打包时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        "========================================"
    )

    $readmeContent -join "`r`n" | Set-Content -Path $readmeFile -Encoding UTF8

    Print-Success "README生成完成"
}

# 创建校验和
function New-Checksum {
    Print-Title "生成校验和"

    $imagesDir = Join-Path $global:PackageDir "images"
    $checksumFile = Join-Path $imagesDir "checksums.md5"

    Print-Info "计算镜像文件校验和..."

    $checksums = @()
    Get-ChildItem -Path $imagesDir -Filter "*.tar" | ForEach-Object {
        $hash = Get-FileHash -Path $_.FullName -Algorithm MD5
        $checksums += "$($hash.Hash.ToLower())  $($_.Name)"
    }

    # 使用Unix风格的LF换行符（兼容Linux）
    $checksumContent = $checksums -join "`n"
    $checksumContent += "`n"  # 末尾添加一个换行符
    
    # 写入文件时使用UTF8无BOM编码，并手动控制换行符
    [System.IO.File]::WriteAllText($checksumFile, $checksumContent, [System.Text.UTF8Encoding]::new($false))

    Print-Success "校验和生成完成（Unix LF格式）"
}

# 压缩打包
function Compress-Package {
    Print-Title "压缩打包"

    Set-Location $global:ProjectRoot

    $global:ArchiveName = "$global:PackageName.tar.gz"

    Print-Info "压缩中，请稍候..."
    Print-Info "注意: Windows环境需要安装tar工具或使用WSL"

    if (Test-Command "tar") {
        tar -czf $global:ArchiveName $global:PackageName
        $archiveSize = (Get-Item $global:ArchiveName).Length / 1GB
        Print-Success "打包完成: $global:ArchiveName ($("{0:N2}" -f $archiveSize) GB)"
    } else {
        Print-Warning "未找到tar命令，将使用ZIP格式压缩"
        $zipName = "$global:PackageName.zip"
        Compress-Archive -Path $global:PackageDir -DestinationPath $zipName -CompressionLevel Optimal
        $zipSize = (Get-Item $zipName).Length / 1GB
        Print-Success "打包完成: $zipName ($("{0:N2}" -f $zipSize) GB)"
        $global:ArchiveName = $zipName
    }
}

# 清理临时文件
function Remove-TempFiles {
    Print-Title "清理临时文件"

    $response = Read-Host "是否删除临时打包目录? [y/N]"
    if ($response -match "^[Yy]") {
        Remove-Item -Path $global:PackageDir -Recurse -Force
        Print-Success "临时文件已清理"
    } else {
        Print-Info "保留临时目录: $global:PackageDir"
    }
}

# 显示总结
function Show-Summary {
    Print-Title "打包完成总结"

    Write-Host ""
    Write-ColorOutput "✓ 打包成功完成！" "Green"
    Write-Host ""
    Write-Host "打包文件: " -NoNewline
    Write-ColorOutput $global:ArchiveName "Cyan"
    Write-Host "包含镜像: " -NoNewline
    Write-ColorOutput "4个" "Cyan"
    Write-Host " (server, web, mysql, redis)"
    Write-Host ""
    Write-ColorOutput "下一步操作:" "Yellow"
    Write-Host "  1. 将 $global:ArchiveName 传输到目标CentOS服务器"
    Write-Host "  2. 在目标服务器上解压并执行 offline-deploy.sh"
    Write-Host "  3. 详细步骤请参考包内的 offline-deployment-guide.md"
    Write-Host ""
    Write-ColorOutput "传输文件示例:" "Green"
    Write-Host "  scp $global:ArchiveName root@target-server:/root/"
    Write-Host ""
}

# 主流程
function Main {
    Print-Title "小智ESP32服务器 - 离线部署包打包工具"

    $global:ProjectRoot = Get-ProjectRoot
    Print-Info "项目根目录: $global:ProjectRoot"

    Test-Requirements
    New-PackageDirectory
    Build-DockerImages
    Get-BaseImages
    Export-DockerImages
    Copy-ConfigFiles
    New-DeploymentManifest
    New-ReadmeFile
    New-Checksum
    Compress-Package
    Remove-TempFiles
    Show-Summary
}

# 执行主流程
try {
    Main
} catch {
    Print-Error "发生错误: $_"
    exit 1
}

exit 0