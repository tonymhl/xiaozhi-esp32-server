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

# 打印函数
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

print_title() {
    echo ""
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}  $1${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo ""
}

# 检查是否为root用户
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "请使用root用户或sudo运行此脚本"
        exit 1
    fi
}

# 检查Docker是否安装
check_docker() {
    print_title "检查Docker环境"
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装！"
        print_info "请先运行: ./install-docker-centos.sh"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose未安装！"
        print_info "请先运行: ./install-docker-centos.sh"
        exit 1
    fi
    
    # 检查Docker服务状态
    if ! systemctl is-active --quiet docker; then
        print_info "启动Docker服务..."
        systemctl start docker
        systemctl enable docker
    fi
    
    print_success "Docker环境检查通过"
    docker --version
    docker-compose --version
}

# 获取脚本所在目录
get_script_dir() {
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    echo "$SCRIPT_DIR"
}

# 加载Docker镜像
load_images() {
    print_title "加载Docker镜像"
    
    IMAGES_DIR="${DEPLOY_DIR}/images"
    
    if [ ! -d "$IMAGES_DIR" ]; then
        print_error "镜像目录不存在: $IMAGES_DIR"
        exit 1
    fi
    
    # 检查镜像文件完整性
    print_info "验证镜像文件完整性..."
    cd "$IMAGES_DIR"
    
    if [ -f "checksums.md5" ]; then
        if md5sum -c checksums.md5 --quiet; then
            print_success "镜像文件校验通过"
        else
            print_error "镜像文件校验失败，文件可能损坏"
            exit 1
        fi
    else
        print_warning "未找到校验文件，跳过完整性验证"
    fi
    
    # 加载镜像
    print_info "加载xiaozhi-esp32-server镜像..."
    docker load -i server.tar
    
    print_info "加载xiaozhi-esp32-server-web镜像..."
    docker load -i web.tar
    
    print_info "加载MySQL镜像..."
    docker load -i mysql.tar
    
    print_info "加载Redis镜像..."
    docker load -i redis.tar
    
    print_success "所有镜像加载完成"
    
    # 显示已加载的镜像
    print_info "已加载的镜像列表:"
    docker images | grep -E "xiaozhi-esp32-server|mysql|redis"
}

# 创建必要的目录结构
create_directories() {
    print_title "创建目录结构"
    
    cd "$DEPLOY_DIR"
    
    print_info "创建数据目录..."
    mkdir -p data
    mkdir -p mysql/data
    mkdir -p uploadfile
    mkdir -p models/SenseVoiceSmall
    
    print_info "设置目录权限..."
    chmod -R 755 data uploadfile models
    chmod -R 777 mysql/data  # MySQL需要写入权限
    
    print_success "目录结构创建完成"
}

# 配置检查
check_configuration() {
    print_title "检查配置文件"
    
    cd "$DEPLOY_DIR"
    
    # 检查docker-compose文件
    if [ ! -f "docker-compose-offline.yml" ]; then
        print_error "docker-compose-offline.yml 文件不存在"
        exit 1
    fi
    print_success "找到 docker-compose-offline.yml"
    
    # 检查配置文件
    if [ -f "data/config.yaml" ]; then
        print_success "找到 data/config.yaml"
    else
        print_warning "未找到 data/config.yaml，将使用默认配置"
    fi
    
    # 检查模型文件
    if [ -f "models/SenseVoiceSmall/model.pt" ]; then
        print_success "找到模型文件 model.pt"
    else
        print_warning "未找到模型文件，某些功能可能无法使用"
        print_info "请将模型文件放置在: models/SenseVoiceSmall/model.pt"
    fi
}

# 配置防火墙
configure_firewall() {
    print_title "配置防火墙"
    
    # 检查防火墙状态
    if systemctl is-active --quiet firewalld; then
        print_info "检测到firewalld正在运行，配置端口..."
        
        firewall-cmd --zone=public --add-port=8000/tcp --permanent
        firewall-cmd --zone=public --add-port=8002/tcp --permanent
        firewall-cmd --zone=public --add-port=8003/tcp --permanent
        firewall-cmd --reload
        
        print_success "防火墙端口配置完成"
    else
        print_info "防火墙未运行，跳过配置"
    fi
}

# 显示部署配置
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
}

# 启动服务
start_services() {
    print_title "启动服务"
    
    cd "$DEPLOY_DIR"
    
    print_info "启动所有容器..."
    docker-compose -f docker-compose-offline.yml up -d
    
    print_success "服务已启动"
    
    print_info "等待服务初始化..."
    sleep 5
    
    # 显示容器状态
    print_info "容器状态："
    docker-compose -f docker-compose-offline.yml ps
}

# 等待服务就绪
wait_for_services() {
    print_title "等待服务就绪"
    
    print_info "等待数据库初始化（首次启动可能需要1-3分钟）..."
    
    MAX_WAIT=180  # 最多等待3分钟
    WAIT_TIME=0
    
    while [ $WAIT_TIME -lt $MAX_WAIT ]; do
        # 检查MySQL是否就绪
        if docker exec xiaozhi-esp32-server-db mysqladmin ping -h localhost --silent &> /dev/null; then
            print_success "MySQL已就绪"
            break
        fi
        
        echo -n "."
        sleep 5
        WAIT_TIME=$((WAIT_TIME + 5))
    done
    
    echo ""
    
    if [ $WAIT_TIME -ge $MAX_WAIT ]; then
        print_warning "MySQL启动超时，请检查日志"
    fi
    
    # 检查Redis
    if docker exec xiaozhi-esp32-server-redis redis-cli ping &> /dev/null; then
        print_success "Redis已就绪"
    fi
    
    print_info "等待应用服务启动..."
    sleep 10
    
    print_success "所有服务初始化完成"
}

# 健康检查
health_check() {
    print_title "服务健康检查"
    
    cd "$DEPLOY_DIR"
    
    # 检查容器状态
    print_info "检查容器运行状态..."
    
    CONTAINERS=("xiaozhi-esp32-server" "xiaozhi-esp32-server-web" "xiaozhi-esp32-server-db" "xiaozhi-esp32-server-redis")
    
    ALL_RUNNING=true
    for container in "${CONTAINERS[@]}"; do
        if docker ps | grep -q "$container"; then
            print_success "✓ $container 运行中"
        else
            print_error "✗ $container 未运行"
            ALL_RUNNING=false
        fi
    done
    
    if [ "$ALL_RUNNING" = false ]; then
        print_warning "部分容器未正常运行，请查看日志"
        print_info "查看日志命令: docker-compose -f docker-compose-offline.yml logs -f"
        return 1
    fi
    
    # 检查端口监听
    print_info "检查端口监听..."
    
    PORTS=(8000 8002 8003)
    for port in "${PORTS[@]}"; do
        if netstat -tln | grep -q ":$port "; then
            print_success "✓ 端口 $port 正在监听"
        else
            print_warning "✗ 端口 $port 未监听"
        fi
    done
    
    print_success "健康检查完成"
}

# 显示访问信息
show_access_info() {
    print_title "部署成功！"
    
    # 获取本机IP
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
    echo "  查看日志: docker-compose -f docker-compose-offline.yml logs -f"
    echo "  停止服务: docker-compose -f docker-compose-offline.yml down"
    echo "  重启服务: docker-compose -f docker-compose-offline.yml restart"
    echo "  查看状态: docker-compose -f docker-compose-offline.yml ps"
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

# 显示日志
show_logs() {
    print_title "实时日志"
    
    cd "$DEPLOY_DIR"
    
    print_info "显示服务日志（按Ctrl+C退出）..."
    sleep 2
    
    docker-compose -f docker-compose-offline.yml logs -f
}

# 主流程
main() {
    print_title "小智ESP32服务器 - 离线部署工具"
    
    # 检查root权限
    check_root
    
    # 获取部署目录
    DEPLOY_DIR=$(get_script_dir)
    print_info "部署目录: $DEPLOY_DIR"
    
    # 检查Docker
    check_docker
    
    # 显示部署配置
    show_deployment_info
    
    # 询问是否继续
    print_info "是否开始部署? [Y/n]"
    read -r response
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY]|)$ ]]; then
        print_info "部署已取消"
        exit 0
    fi
    
    # 加载镜像
    load_images
    
    # 创建目录
    create_directories
    
    # 检查配置
    check_configuration
    
    # 配置防火墙
    configure_firewall
    
    # 启动服务
    start_services
    
    # 等待服务就绪
    wait_for_services
    
    # 健康检查
    if ! health_check; then
        print_warning "服务健康检查未完全通过，但部署已完成"
        print_info "请检查日志排查问题"
    fi
    
    # 显示访问信息
    show_access_info
    
    # 询问是否查看日志
    print_info "是否查看实时日志? [y/N]"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        show_logs
    fi
}

# 执行主流程
main

exit 0

