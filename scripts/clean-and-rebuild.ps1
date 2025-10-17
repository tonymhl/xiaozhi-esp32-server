##############################################################################
# Docker构建清理脚本
# 用途: 清理构建缓存和临时文件，为重新打包做准备
##############################################################################

Write-Host "================================================" -ForegroundColor Green
Write-Host "  Docker构建清理工具" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""

# 停止所有正在运行的容器
Write-Host "[INFO] 停止本地容器..." -ForegroundColor Cyan
docker-compose -f main/xiaozhi-server/docker-compose_all.yml down 2>$null

# 清理构建缓存
Write-Host "[INFO] 清理Docker构建缓存..." -ForegroundColor Cyan
docker builder prune -f

# 清理悬空镜像
Write-Host "[INFO] 清理悬空镜像..." -ForegroundColor Cyan
docker image prune -f

# 清理临时打包目录
Write-Host "[INFO] 清理临时打包目录..." -ForegroundColor Cyan
Get-ChildItem -Path . -Filter "xiaozhi-offline-deployment-*" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "[SUCCESS] 清理完成！现在可以重新运行打包脚本了。" -ForegroundColor Green
Write-Host ""
Write-Host "执行以下命令开始打包：" -ForegroundColor Yellow
Write-Host "  .\scripts\offline-package.ps1" -ForegroundColor Cyan
Write-Host ""

