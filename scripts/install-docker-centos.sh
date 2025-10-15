#!/bin/bash
##############################################################################
# Docker & Docker Compose 安装脚本 (CentOS 7/8/Stream)
# 用途: 在离线或在线CentOS环境中安装Docker
##############################################################################

set -e

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

# 检查是否为root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "请使用root用户或sudo运行此脚本"
        exit 1
    fi
}

# 检测系统版本
detect_os() {
    print_title "检测系统信息"
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VER=$VERSION_ID
        print_info "操作系统: $OS"
        print_info "版本: $VER"
    else
        print_error "无法检测系统版本"
        exit 1
    fi
    
    # 检查是否为CentOS
    if [[ "$OS" != "centos" ]] && [[ "$OS" != "rhel" ]] && [[ "$OS" != "rocky" ]] && [[ "$OS" != "almalinux" ]]; then
        print_warning "此脚本专为CentOS/RHEL系列设计，您的系统可能不兼容"
    fi
}

# 检查Docker是否已安装
check_docker_installed() {
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        print_warning "Docker已安装: $DOCKER_VERSION"
        print_info "是否重新安装? [y/N]"
        read -r response
        if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            print_info "跳过Docker安装"
            return 0
        else
            print_info "将重新安装Docker"
            uninstall_docker
        fi
    fi
    return 1
}

# 卸载旧版本Docker
uninstall_docker() {
    print_title "卸载旧版本Docker"
    
    print_info "移除旧版本Docker..."
    yum remove -y docker \
                  docker-client \
                  docker-client-latest \
                  docker-common \
                  docker-latest \
                  docker-latest-logrotate \
                  docker-logrotate \
                  docker-engine \
                  podman \
                  runc 2>/dev/null || true
    
    print_success "旧版本清理完成"
}

# 安装依赖
install_dependencies() {
    print_title "安装依赖包"
    
    print_info "更新yum缓存..."
    yum makecache fast || yum makecache
    
    print_info "安装必要工具..."
    yum install -y yum-utils \
                   device-mapper-persistent-data \
                   lvm2 \
                   wget \
                   curl \
                   net-tools
    
    print_success "依赖包安装完成"
}

# 配置Docker仓库
configure_docker_repo() {
    print_title "配置Docker仓库"
    
    # 备份现有repo文件
    if [ -f /etc/yum.repos.d/docker-ce.repo ]; then
        mv /etc/yum.repos.d/docker-ce.repo /etc/yum.repos.d/docker-ce.repo.bak
    fi
    
    print_info "添加阿里云Docker仓库..."
    yum-config-manager \
        --add-repo \
        https://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
    
    # 更新缓存
    yum makecache fast || yum makecache
    
    print_success "Docker仓库配置完成"
}

# 安装Docker
install_docker() {
    print_title "安装Docker"
    
    print_info "安装Docker CE..."
    yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    print_success "Docker安装完成"
    
    # 显示版本
    docker --version
}

# 配置Docker
configure_docker() {
    print_title "配置Docker"
    
    print_info "创建Docker配置目录..."
    mkdir -p /etc/docker
    
    print_info "配置Docker镜像加速..."
    cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check=true"
  ]
}
EOF
    
    print_success "Docker配置完成"
}

# 启动Docker
start_docker() {
    print_title "启动Docker服务"
    
    print_info "启动Docker..."
    systemctl daemon-reload
    systemctl start docker
    systemctl enable docker
    
    print_success "Docker服务已启动"
    
    # 验证Docker运行状态
    if systemctl is-active --quiet docker; then
        print_success "Docker运行正常"
    else
        print_error "Docker启动失败"
        exit 1
    fi
}

# 安装Docker Compose
install_docker_compose() {
    print_title "安装Docker Compose"
    
    # Docker Compose已作为插件安装，创建软链接
    if [ -f /usr/libexec/docker/cli-plugins/docker-compose ]; then
        print_info "创建docker-compose命令软链接..."
        ln -sf /usr/libexec/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        print_success "Docker Compose安装完成"
        docker-compose --version
    else
        print_warning "Docker Compose插件未找到，尝试手动安装..."
        
        # 手动下载安装
        COMPOSE_VERSION="v2.24.0"
        print_info "下载Docker Compose ${COMPOSE_VERSION}..."
        curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
             -o /usr/local/bin/docker-compose
        
        chmod +x /usr/local/bin/docker-compose
        
        if docker-compose --version &> /dev/null; then
            print_success "Docker Compose安装完成"
            docker-compose --version
        else
            print_error "Docker Compose安装失败"
            exit 1
        fi
    fi
}

# 配置用户组
configure_user_group() {
    print_title "配置Docker用户组"
    
    print_info "添加当前用户到docker组（可选）..."
    
    if [ -n "$SUDO_USER" ]; then
        usermod -aG docker $SUDO_USER
        print_success "用户 $SUDO_USER 已添加到docker组"
        print_info "请注销后重新登录以使用户组生效"
    else
        print_info "以root用户运行，跳过用户组配置"
    fi
}

# 测试Docker
test_docker() {
    print_title "测试Docker安装"
    
    print_info "运行测试容器..."
    docker run --rm hello-world
    
    if [ $? -eq 0 ]; then
        print_success "Docker测试通过"
    else
        print_error "Docker测试失败"
        exit 1
    fi
}

# 显示安装信息
show_installation_info() {
    print_title "安装完成"
    
    echo ""
    echo -e "${GREEN}✓ Docker和Docker Compose已成功安装！${NC}"
    echo ""
    echo -e "${BLUE}版本信息:${NC}"
    docker --version
    docker-compose --version
    echo ""
    echo -e "${BLUE}常用命令:${NC}"
    echo "  查看Docker状态:   systemctl status docker"
    echo "  启动Docker:       systemctl start docker"
    echo "  停止Docker:       systemctl stop docker"
    echo "  重启Docker:       systemctl restart docker"
    echo "  查看容器:         docker ps"
    echo "  查看镜像:         docker images"
    echo ""
    echo -e "${BLUE}下一步:${NC}"
    echo "  您现在可以运行部署脚本来部署小智ESP32服务器"
    echo "  执行: ./offline-deploy.sh"
    echo ""
}

# 主流程
main() {
    print_title "Docker & Docker Compose 安装工具"
    
    # 检查root权限
    check_root
    
    # 检测系统
    detect_os
    
    # 检查是否已安装
    if check_docker_installed; then
        print_success "Docker已安装，无需重复安装"
        show_installation_info
        exit 0
    fi
    
    # 卸载旧版本
    uninstall_docker
    
    # 安装依赖
    install_dependencies
    
    # 配置仓库
    configure_docker_repo
    
    # 安装Docker
    install_docker
    
    # 配置Docker
    configure_docker
    
    # 启动Docker
    start_docker
    
    # 安装Docker Compose
    install_docker_compose
    
    # 配置用户组
    configure_user_group
    
    # 测试安装
    test_docker
    
    # 显示信息
    show_installation_info
}

# 执行主流程
main

exit 0

