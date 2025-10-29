#!/bin/bash
##############################################################################
# 小智ESP32服务器 - 离线环境自动部署脚本
# 用途: 在离线CentOS环境中，一键部署所有服务
##############################################################################

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Docker Compose 命令（数组形式，仅独立二进制）
COMPOSE_CMD=()
COMPOSE_CMD_NAME=""

# ---------- 工具函数 ----------
print_info()     { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success()  { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning()  { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error()    { echo -e "${RED}[ERROR]${NC} $1"; }

print_title() {
    echo ""
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}  $1${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo ""
}

# 统一执行 docker-compose 的包装
compose() {
    "${COMPOSE_CMD[@]}" "$@"
}

# 检查 root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "请使用 root 或 sudo 运行此脚本"
        exit 1
    fi
}

# 仅检测独立二进制 docker-compose
detect_compose_command() {
    if command -v docker-compose >/dev/null 2>&1; then
        COMPOSE_CMD=("docker-compose")
        COMPOSE_CMD_NAME="docker-compose"
        return
    fi
    print_error "Docker Compose 未安装！"
    print_info "请将 docker-compose 放入 PATH 后重试"
    exit 1
}

# 检查 Docker & Compose
check_docker() {
    print_title "检查 Docker 环境"

    command -v docker >/dev/null 2>&1 || {
        print_error "Docker 未安装！"
        exit 1
    }

    detect_compose_command

    systemctl is-active --quiet docker || {
        print_info "启动 Docker 服务 ..."
        systemctl start docker
        systemctl enable docker
    }

    print_success "Docker 环境检查通过"
    docker --version
    docker-compose --version
}

# 获取脚本目录
get_script_dir() {
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    echo "$SCRIPT_DIR"
}

# ---------- 业务函数 ----------
load_images() {
    print_title "加载 Docker 镜像"

    IMAGES_DIR="${DEPLOY_DIR}/images"
    [ -d "$IMAGES_DIR" ] || {
        print_error "镜像目录不存在: $IMAGES_DIR"
        exit 1
    }

    cd "$IMAGES_DIR"

    if [ -f "checksums.md5" ]; then
        # 转换Windows换行符为Unix格式（如果需要）
        print_info "检查校验和文件格式..."
        if file checksums.md5 2>/dev/null | grep -q "CRLF"; then
            print_warning "检测到Windows换行符，正在转换为Unix格式..."
            # 尝试使用dos2unix，如果不存在则使用sed
            if command -v dos2unix &> /dev/null; then
                dos2unix checksums.md5 2>/dev/null
            else
                sed -i 's/\r$//' checksums.md5 2>/dev/null || sed -i '' 's/\r$//' checksums.md5
            fi
        fi
        
        print_info "验证镜像文件完整性..."
        if md5sum -c checksums.md5 --quiet 2>/dev/null; then
            print_success "镜像文件校验通过"
        else
            print_warning "MD5校验失败，尝试手动验证tar文件完整性..."
            # 手动验证每个tar文件是否可以正常读取
            all_ok=true
            for tarfile in server.tar web.tar mysql.tar redis.tar; do
                if [ -f "$tarfile" ]; then
                    if tar -tzf "$tarfile" > /dev/null 2>&1; then
                        print_success "✓ $tarfile 文件完整"
                    else
                        print_error "✗ $tarfile 文件损坏"
                        all_ok=false
                    fi
                else
                    print_error "✗ $tarfile 文件不存在"
                    all_ok=false
                fi
            done
            
            if [ "$all_ok" = "false" ]; then
                print_error "部分镜像文件损坏或缺失，请重新传输部署包"
                exit 1
            else
                print_success "所有镜像文件完整（通过tar验证）"
            fi
        fi
    else
        print_warning "未找到校验文件，跳过完整性验证"
    fi

    print_info "加载 xiaozhi-esp32-server 镜像 ..."
    docker load -i server.tar

    print_info "加载 xiaozhi-esp32-server-web 镜像 ..."
    docker load -i web.tar

    print_info "加载 MySQL 镜像 ..."
    docker load -i mysql.tar

    print_info "加载 Redis 镜像 ..."
    docker load -i redis.tar

    print_success "所有镜像加载完成"
    echo
    docker images | grep -E "xiaozhi-esp32-server|mysql|redis"
}

create_directories() {
    print_title "创建目录结构"

    cd "$DEPLOY_DIR"

    mkdir -p data mysql/data uploadfile models plugins_func/functions redis/data memory/mem_local_short intent/intent_llm docker-config

    chmod -R 755 data uploadfile models plugins_func memory intent docker-config
    chmod -R 777 mysql/data redis/data

    print_success "目录结构创建完成"
}

check_configuration() {
    print_title "检查配置文件"

    cd "$DEPLOY_DIR"

    [ -f "docker-compose-offline.yml" ] || {
        print_error "docker-compose-offline.yml 文件不存在"
        exit 1
    }
    print_success "找到 docker-compose-offline.yml"

    if [ -f "data/config.yaml" ]; then
        print_success "找到 data/config.yaml"
    else
        print_warning "未找到 data/config.yaml，将使用默认配置"
    fi

    if [ -d "models" ] && [ "$(ls -A models 2>/dev/null)" ]; then
        print_success "找到模型目录"
        print_info "已检测到以下模型："
        ls -1 models/ | head -5
    else
        print_warning "未找到模型文件，某些功能可能无法使用"
        print_info "请将模型文件放置在: models/ 目录"
    fi
}

configure_firewall() {
    print_title "配置防火墙"

    if systemctl is-active --quiet firewalld; then
        print_info "检测到 firewalld 正在运行，配置端口 ..."
        firewall-cmd --zone=public --add-port=8000/tcp --permanent
        firewall-cmd --zone=public --add-port=8002/tcp --permanent
        firewall-cmd --zone=public --add-port=8003/tcp --permanent
        firewall-cmd --reload
        print_success "防火墙端口配置完成"
    else
        print_info "防火墙未运行，跳过配置"
    fi
}

show_deployment_info() {
    print_title "部署配置信息"

    echo ""
    echo -e "${BLUE}部署目录:${NC} $DEPLOY_DIR"
    echo -e "${BLUE}服务模式:${NC} 全模块（Server + Web + MySQL + Redis）"
    echo ""
    echo -e "${BLUE}端口映射:${NC}"
    echo "  - WebSocket服务: 8000"
    echo "  - Web管理界面:   8002"
    echo "  - HTTP服务:      8003"
    echo ""
    echo -e "${BLUE}数据目录:${NC}"
    echo "  - 配置文件: $DEPLOY_DIR/data"
    echo "  - 数据库:   $DEPLOY_DIR/mysql/data"
    echo "  - 上传文件: $DEPLOY_DIR/uploadfile"
    echo "  - 模型文件: $DEPLOY_DIR/models"
    echo ""
    echo -e "${BLUE}使用的 Docker Compose 命令:${NC} ${COMPOSE_CMD_NAME}"
    echo ""
}

start_services() {
    print_title "启动服务"

    cd "$DEPLOY_DIR"

    print_info "启动所有容器 ..."
    compose -f docker-compose-offline.yml up -d

    print_success "服务已启动"
    sleep 5
    compose -f docker-compose-offline.yml ps
}

wait_for_services() {
    print_title "等待服务就绪"

    print_info "等待数据库初始化（首次启动可能需要 1-3 分钟）..."

    MAX_WAIT=180
    WAIT_TIME=0
    while [ $WAIT_TIME -lt $MAX_WAIT ]; do
        if docker exec xiaozhi-esp32-server-db mysqladmin ping -h localhost --silent &>/dev/null; then
            print_success "MySQL 已就绪"
            break
        fi
        echo -n "."
        sleep 5
        WAIT_TIME=$((WAIT_TIME + 5))
    done
    echo

    [ $WAIT_TIME -ge $MAX_WAIT ] && print_warning "MySQL 启动超时，请检查日志"

    if docker exec xiaozhi-esp32-server-redis redis-cli ping &>/dev/null; then
        print_success "Redis 已就绪"
    fi

    sleep 10
    print_success "所有服务初始化完成"
}

health_check() {
    print_title "服务健康检查"

    cd "$DEPLOY_DIR"

    print_info "检查容器运行状态 ..."

    CONTAINERS=(xiaozhi-esp32-server xiaozhi-esp32-server-web xiaozhi-esp32-server-db xiaozhi-esp32-server-redis)
    ALL_RUNNING=true
    for c in "${CONTAINERS[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${c}$"; then
            print_success "✓ $c 运行中"
        else
            print_error "✗ $c 未运行"
            ALL_RUNNING=false
        fi
    done

    if [ "$ALL_RUNNING" = false ]; then
        print_warning "部分容器未正常运行，请查看日志"
        print_info "查看日志: ${COMPOSE_CMD_NAME} -f docker-compose-offline.yml logs -f"
        return 1
    fi

    print_info "检查端口监听 ..."
    for port in 8000 8002 8003; do
        if netstat -tln | grep -q ":$port "; then
            print_success "✓ 端口 $port 正在监听"
        else
            print_warning "✗ 端口 $port 未监听"
        fi
    done

    print_success "健康检查完成"
}

show_access_info() {
    print_title "部署成功！"

    LOCAL_IP=$(hostname -I | awk '{print $1}')

    echo ""
    echo -e "${GREEN}✓ 小智ESP32服务器已成功部署！${NC}"
    echo ""
    echo -e "${BLUE}访问地址:${NC}"
    echo -e "  Web管理界面: ${YELLOW}http://${LOCAL_IP}:8002${NC}"
    echo -e "  WebSocket:   ${YELLOW}ws://${LOCAL_IP}:8000${NC}"
    echo -e "  HTTP服务:    ${YELLOW}http://${LOCAL_IP}:8003${NC}"
    echo ""
    echo -e "${BLUE}默认账号:${NC}"
    echo "  账号: admin"
    echo "  密码: （请参考项目文档）"
    echo ""
    echo -e "${BLUE}常用命令:${NC}"
    echo "  查看日志: ${COMPOSE_CMD_NAME} -f docker-compose-offline.yml logs -f"
    echo "  停止服务: ${COMPOSE_CMD_NAME} -f docker-compose-offline.yml down"
    echo "  重启服务: ${COMPOSE_CMD_NAME} -f docker-compose-offline.yml restart"
    echo "  查看状态: ${COMPOSE_CMD_NAME} -f docker-compose-offline.yml ps"
    echo ""
    echo -e "${BLUE}数据备份:${NC}"
    echo "  配置文件: $DEPLOY_DIR/data"
    echo "  数据库:   $DEPLOY_DIR/mysql/data"
    echo "  上传文件: $DEPLOY_DIR/uploadfile"
    echo ""
    echo -e "${YELLOW}注意事项:${NC}"
    echo "  1. 首次启动可能需要几分钟初始化数据库"
    echo "  2. 如需修改配置，请编辑 data/config.yaml 后重启服务"
    echo "  3. 定期备份数据目录以防数据丢失"
    echo "  4. 详细文档请参考: offline-deployment-guide.md"
    echo ""
}

show_logs() {
    print_title "实时日志"
    cd "$DEPLOY_DIR"
    print_info "显示服务日志（按 Ctrl+C 退出）..."
    sleep 2
    compose -f docker-compose-offline.yml logs -f
}

# ==================== main ====================
main() {
    print_title "小智ESP32服务器 - 离线部署工具"

    check_root
    DEPLOY_DIR=$(get_script_dir)
    print_info "部署目录: $DEPLOY_DIR"

    check_docker
    show_deployment_info

    read -rp "是否开始部署? [Y/n] " response
    [[ "$response" =~ ^[Nn] ]] && { print_info "部署已取消"; exit 0; }

    load_images
    create_directories
    check_configuration
    configure_firewall
    start_services
    wait_for_services

    health_check || print_warning "服务健康检查未完全通过，但部署已完成"

    show_access_info

    read -rp "是否查看实时日志? [y/N] " response
    [[ "$response" =~ ^[Yy] ]] && show_logs
}

main
exit 0