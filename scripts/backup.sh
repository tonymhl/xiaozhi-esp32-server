#!/bin/bash
##############################################################################
# 小智ESP32服务器 - 数据备份脚本
# 用途: 定期备份配置文件、数据库和上传文件
##############################################################################

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 配置
BACKUP_ROOT="/backup/xiaozhi-esp32-server"
DEPLOY_DIR="/root/offline-package"  # 根据实际部署目录修改
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_DIR=$(date +%Y%m)

# 创建备份根目录
mkdir -p "${BACKUP_ROOT}/${DATE_DIR}"
BACKUP_DIR="${BACKUP_ROOT}/${DATE_DIR}/${TIMESTAMP}"
mkdir -p "$BACKUP_DIR"

print_info "开始备份到: $BACKUP_DIR"

# 备份配置文件
backup_configs() {
    print_info "备份配置文件..."
    
    if [ -d "${DEPLOY_DIR}/data" ]; then
        tar -czf "${BACKUP_DIR}/config_${TIMESTAMP}.tar.gz" \
            -C "${DEPLOY_DIR}" data/
        print_success "配置文件备份完成"
    else
        print_error "配置目录不存在"
    fi
}

# 备份数据库
backup_database() {
    print_info "备份数据库..."
    
    # 检查容器是否运行
    if docker ps | grep -q "xiaozhi-esp32-server-db"; then
        docker exec xiaozhi-esp32-server-db mysqldump \
            -uroot -p123456 \
            --single-transaction \
            --quick \
            --lock-tables=false \
            xiaozhi_esp32_server > "${BACKUP_DIR}/database_${TIMESTAMP}.sql"
        
        # 压缩SQL文件
        gzip "${BACKUP_DIR}/database_${TIMESTAMP}.sql"
        print_success "数据库备份完成"
    else
        print_error "数据库容器未运行"
    fi
}

# 备份上传文件
backup_uploads() {
    print_info "备份上传文件..."
    
    if [ -d "${DEPLOY_DIR}/uploadfile" ]; then
        # 只备份有文件的目录
        if [ "$(ls -A ${DEPLOY_DIR}/uploadfile)" ]; then
            tar -czf "${BACKUP_DIR}/uploadfile_${TIMESTAMP}.tar.gz" \
                -C "${DEPLOY_DIR}" uploadfile/
            print_success "上传文件备份完成"
        else
            print_info "上传目录为空，跳过备份"
        fi
    else
        print_error "上传目录不存在"
    fi
}

# 创建备份清单
create_manifest() {
    print_info "创建备份清单..."
    
    cat > "${BACKUP_DIR}/BACKUP_MANIFEST.txt" <<EOF
========================================
小智ESP32服务器 - 备份清单
========================================

备份时间: $(date '+%Y-%m-%d %H:%M:%S')
备份目录: ${BACKUP_DIR}

========================================
备份内容
========================================

$(ls -lh "${BACKUP_DIR}" | grep -v "^total" | grep -v "BACKUP_MANIFEST")

========================================
备份大小统计
========================================

总大小: $(du -sh "${BACKUP_DIR}" | cut -f1)

========================================
恢复方法
========================================

1. 恢复配置文件:
   tar -xzf config_${TIMESTAMP}.tar.gz -C ${DEPLOY_DIR}/

2. 恢复数据库:
   gunzip database_${TIMESTAMP}.sql.gz
   docker exec -i xiaozhi-esp32-server-db mysql -uroot -p123456 xiaozhi_esp32_server < database_${TIMESTAMP}.sql

3. 恢复上传文件:
   tar -xzf uploadfile_${TIMESTAMP}.tar.gz -C ${DEPLOY_DIR}/

========================================
EOF

    print_success "备份清单创建完成"
}

# 清理旧备份（保留最近30天）
cleanup_old_backups() {
    print_info "清理旧备份..."
    
    find "${BACKUP_ROOT}" -type d -mtime +30 -exec rm -rf {} + 2>/dev/null || true
    
    print_success "旧备份清理完成"
}

# 主流程
main() {
    echo ""
    echo "========================================="
    echo "小智ESP32服务器 - 数据备份"
    echo "========================================="
    echo ""
    
    # 执行备份
    backup_configs
    backup_database
    backup_uploads
    create_manifest
    cleanup_old_backups
    
    # 显示结果
    echo ""
    print_success "备份完成！"
    echo ""
    echo "备份位置: ${BACKUP_DIR}"
    echo "备份大小: $(du -sh "${BACKUP_DIR}" | cut -f1)"
    echo ""
    echo "备份文件列表:"
    ls -lh "${BACKUP_DIR}"
    echo ""
}

# 执行
main

exit 0

