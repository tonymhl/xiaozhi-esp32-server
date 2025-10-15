#!/bin/bash
##############################################################################
# 小智ESP32服务器 - 离线部署包自动打包脚本 (Linux/Mac)
# 用途: 在有网络的环境中，一键打包所有需要的Docker镜像和配置文件
##############################################################################

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的信息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 打印标题
print_title() {
    echo ""
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}  $1${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo ""
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 未安装，请先安装 $1"
        exit 1
    fi
}

# 检查必要工具
check_requirements() {
    print_title "检查系统环境"
    
    print_info "检查Docker..."
    check_command docker
    
    print_info "检查Docker Compose..."
    check_command docker-compose
    
    print_info "检查tar..."
    check_command tar
    
    print_success "所有必要工具已就绪"
}

# 获取项目根目录
get_project_root() {
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
    echo "$PROJECT_ROOT"
}

# 创建打包目录
create_package_dir() {
    print_title "创建打包目录"
    
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    PACKAGE_NAME="xiaozhi-offline-deployment-${TIMESTAMP}"
    PACKAGE_DIR="${PROJECT_ROOT}/${PACKAGE_NAME}"
    
    print_info "创建目录: ${PACKAGE_DIR}"
    mkdir -p "${PACKAGE_DIR}"
    mkdir -p "${PACKAGE_DIR}/images"
    mkdir -p "${PACKAGE_DIR}/scripts"
    mkdir -p "${PACKAGE_DIR}/data"
    mkdir -p "${PACKAGE_DIR}/mysql/data"
    mkdir -p "${PACKAGE_DIR}/uploadfile"
    mkdir -p "${PACKAGE_DIR}/models/SenseVoiceSmall"
    
    print_success "打包目录创建完成"
}

# 编译Docker镜像
build_images() {
    print_title "编译Docker镜像"
    
    cd "${PROJECT_ROOT}"
    
    print_info "编译xiaozhi-esp32-server镜像..."
    docker build -t xiaozhi-esp32-server:server_custom -f ./Dockerfile-server .
    
    print_info "编译xiaozhi-esp32-server-web镜像..."
    docker build -t xiaozhi-esp32-server:web_custom -f ./Dockerfile-web .
    
    print_success "所有镜像编译完成"
}

# 拉取基础镜像
pull_base_images() {
    print_title "拉取基础镜像"
    
    print_info "拉取MySQL镜像..."
    docker pull mysql:latest
    
    print_info "拉取Redis镜像..."
    docker pull redis:latest
    
    print_success "基础镜像拉取完成"
}

# 导出Docker镜像
export_images() {
    print_title "导出Docker镜像"
    
    print_info "导出xiaozhi-esp32-server镜像..."
    docker save xiaozhi-esp32-server:server_custom -o "${PACKAGE_DIR}/images/server.tar"
    
    print_info "导出xiaozhi-esp32-server-web镜像..."
    docker save xiaozhi-esp32-server:web_custom -o "${PACKAGE_DIR}/images/web.tar"
    
    print_info "导出MySQL镜像..."
    docker save mysql:latest -o "${PACKAGE_DIR}/images/mysql.tar"
    
    print_info "导出Redis镜像..."
    docker save redis:latest -o "${PACKAGE_DIR}/images/redis.tar"
    
    print_success "所有镜像导出完成"
}

# 复制配置文件
copy_configs() {
    print_title "复制配置文件"
    
    print_info "复制docker-compose配置..."
    cp "${PROJECT_ROOT}/main/xiaozhi-server/docker-compose_all.yml" "${PACKAGE_DIR}/docker-compose-offline.yml"
    
    # 修改docker-compose配置，使用自定义镜像
    sed -i.bak 's|ghcr.nju.edu.cn/xinnan-tech/xiaozhi-esp32-server:server_latest|xiaozhi-esp32-server:server_custom|g' "${PACKAGE_DIR}/docker-compose-offline.yml"
    sed -i.bak 's|ghcr.nju.edu.cn/xinnan-tech/xiaozhi-esp32-server:web_latest|xiaozhi-esp32-server:web_custom|g' "${PACKAGE_DIR}/docker-compose-offline.yml"
    rm -f "${PACKAGE_DIR}/docker-compose-offline.yml.bak"
    
    print_info "复制应用配置文件..."
    if [ -f "${PROJECT_ROOT}/main/xiaozhi-server/config.yaml" ]; then
        cp "${PROJECT_ROOT}/main/xiaozhi-server/config.yaml" "${PACKAGE_DIR}/data/"
    fi
    
    if [ -f "${PROJECT_ROOT}/main/xiaozhi-server/config_from_api.yaml" ]; then
        cp "${PROJECT_ROOT}/main/xiaozhi-server/config_from_api.yaml" "${PACKAGE_DIR}/data/"
    fi
    
    print_info "复制部署脚本..."
    cp "${PROJECT_ROOT}/scripts/offline-deploy.sh" "${PACKAGE_DIR}/"
    cp "${PROJECT_ROOT}/scripts/install-docker-centos.sh" "${PACKAGE_DIR}/"
    cp "${PROJECT_ROOT}/scripts/backup.sh" "${PACKAGE_DIR}/scripts/"
    chmod +x "${PACKAGE_DIR}/offline-deploy.sh"
    chmod +x "${PACKAGE_DIR}/install-docker-centos.sh"
    chmod +x "${PACKAGE_DIR}/scripts/backup.sh"
    
    print_info "复制文档..."
    cp "${PROJECT_ROOT}/docs/offline-deployment-guide.md" "${PACKAGE_DIR}/"
    
    print_info "复制模型文件..."
    if [ -d "${PROJECT_ROOT}/main/xiaozhi-server/models" ]; then
        cp -r "${PROJECT_ROOT}/main/xiaozhi-server/models/"* "${PACKAGE_DIR}/models/" 2>/dev/null || print_warning "没有找到模型文件，请手动添加"
    fi
    
    print_success "配置文件复制完成"
}

# 生成部署清单
generate_manifest() {
    print_title "生成部署清单"
    
    MANIFEST_FILE="${PACKAGE_DIR}/DEPLOYMENT-MANIFEST.txt"
    
    cat > "${MANIFEST_FILE}" << EOF
========================================
小智ESP32服务器 - 离线部署包清单
========================================

打包时间: $(date '+%Y-%m-%d %H:%M:%S')
打包环境: $(uname -s) $(uname -r)

========================================
镜像列表
========================================

1. xiaozhi-esp32-server:server_custom
   文件: images/server.tar
   大小: $(du -h "${PACKAGE_DIR}/images/server.tar" | cut -f1)
   说明: Python服务，包含所有工具函数

2. xiaozhi-esp32-server:web_custom
   文件: images/web.tar
   大小: $(du -h "${PACKAGE_DIR}/images/web.tar" | cut -f1)
   说明: Vue前端 + Java后端管理控制台

3. mysql:latest
   文件: images/mysql.tar
   大小: $(du -h "${PACKAGE_DIR}/images/mysql.tar" | cut -f1)
   说明: MySQL数据库

4. redis:latest
   文件: images/redis.tar
   大小: $(du -h "${PACKAGE_DIR}/images/redis.tar" | cut -f1)
   说明: Redis缓存服务

========================================
配置文件
========================================

- docker-compose-offline.yml     : Docker Compose配置
- data/config.yaml               : 主配置文件
- data/config_from_api.yaml      : API配置文件
- offline-deploy.sh              : 自动部署脚本
- install-docker-centos.sh       : Docker安装脚本
- scripts/backup.sh              : 数据备份脚本
- offline-deployment-guide.md    : 详细部署指南

========================================
目录结构
========================================

$(tree -L 2 "${PACKAGE_DIR}" 2>/dev/null || find "${PACKAGE_DIR}" -maxdepth 2 -type d | sed 's|[^/]*/| |g')

========================================
快速部署步骤
========================================

1. 传输本压缩包到目标CentOS服务器

2. 解压：
   tar -xzf $(basename ${PACKAGE_NAME}).tar.gz
   cd $(basename ${PACKAGE_NAME})

3. 安装Docker（如未安装）：
   chmod +x install-docker-centos.sh
   ./install-docker-centos.sh

4. 执行自动部署：
   chmod +x offline-deploy.sh
   ./offline-deploy.sh

5. 访问服务：
   Web管理界面: http://服务器IP:8002
   WebSocket服务: ws://服务器IP:8000
   HTTP服务: http://服务器IP:8003

========================================
注意事项
========================================

- 确保目标服务器有至少8GB内存和50GB磁盘空间
- 首次启动需要1-3分钟初始化数据库
- 如需修改配置，请编辑data/config.yaml
- 详细部署说明请参考offline-deployment-guide.md

========================================
技术支持
========================================

项目地址: https://github.com/xinnan-tech/xiaozhi-esp32-server
文档地址: https://github.com/xinnan-tech/xiaozhi-esp32-server/tree/main/docs

========================================
EOF

    print_success "部署清单生成完成"
}

# 生成快速README
generate_readme() {
    README_FILE="${PACKAGE_DIR}/README.txt"
    
    cat > "${README_FILE}" << EOF
========================================
小智ESP32服务器 - 离线部署包
========================================

快速部署步骤：

1. 解压本包：
   tar -xzf xiaozhi-offline-deployment-*.tar.gz

2. 进入目录：
   cd xiaozhi-offline-deployment-*/

3. 安装Docker（如未安装）：
   chmod +x install-docker-centos.sh
   sudo ./install-docker-centos.sh

4. 执行自动部署：
   chmod +x offline-deploy.sh
   sudo ./offline-deploy.sh

5. 访问服务：
   http://服务器IP:8002

详细部署指南请查看：
offline-deployment-guide.md

打包时间: $(date '+%Y-%m-%d %H:%M:%S')
EOF

    print_success "README生成完成"
}

# 创建校验和
create_checksum() {
    print_title "生成校验和"
    
    cd "${PACKAGE_DIR}/images"
    
    print_info "计算镜像文件校验和..."
    md5sum *.tar > checksums.md5
    
    print_success "校验和生成完成"
}

# 压缩打包
compress_package() {
    print_title "压缩打包"
    
    cd "${PROJECT_ROOT}"
    
    ARCHIVE_NAME="${PACKAGE_NAME}.tar.gz"
    
    print_info "压缩中，请稍候..."
    tar -czf "${ARCHIVE_NAME}" "$(basename ${PACKAGE_DIR})"
    
    ARCHIVE_SIZE=$(du -h "${ARCHIVE_NAME}" | cut -f1)
    
    print_success "打包完成: ${ARCHIVE_NAME} (${ARCHIVE_SIZE})"
}

# 清理临时文件
cleanup() {
    print_title "清理临时文件"
    
    print_info "是否删除临时打包目录? [y/N]"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        rm -rf "${PACKAGE_DIR}"
        print_success "临时文件已清理"
    else
        print_info "保留临时目录: ${PACKAGE_DIR}"
    fi
}

# 显示总结
show_summary() {
    print_title "打包完成总结"
    
    echo ""
    echo -e "${GREEN}✓ 打包成功完成！${NC}"
    echo ""
    echo -e "打包文件: ${BLUE}${ARCHIVE_NAME}${NC}"
    echo -e "文件大小: ${BLUE}${ARCHIVE_SIZE}${NC}"
    echo -e "包含镜像: ${BLUE}4个${NC} (server, web, mysql, redis)"
    echo ""
    echo -e "${YELLOW}下一步操作:${NC}"
    echo -e "  1. 将 ${ARCHIVE_NAME} 传输到目标CentOS服务器"
    echo -e "  2. 在目标服务器上解压并执行 offline-deploy.sh"
    echo -e "  3. 详细步骤请参考包内的 offline-deployment-guide.md"
    echo ""
    echo -e "${GREEN}传输文件示例:${NC}"
    echo -e "  scp ${ARCHIVE_NAME} root@target-server:/root/"
    echo ""
}

# 主流程
main() {
    print_title "小智ESP32服务器 - 离线部署包打包工具"
    
    # 获取项目根目录
    PROJECT_ROOT=$(get_project_root)
    print_info "项目根目录: ${PROJECT_ROOT}"
    
    # 检查环境
    check_requirements
    
    # 创建打包目录
    create_package_dir
    
    # 编译镜像
    build_images
    
    # 拉取基础镜像
    pull_base_images
    
    # 导出镜像
    export_images
    
    # 复制配置文件
    copy_configs
    
    # 生成清单
    generate_manifest
    generate_readme
    
    # 创建校验和
    create_checksum
    
    # 压缩打包
    compress_package
    
    # 清理临时文件
    cleanup
    
    # 显示总结
    show_summary
}

# 执行主流程
main

exit 0

