#!/bin/bash
# 文件名: resource_stress_test_v2.sh
# 描述: 改进的CPU和内存压力测试脚本

STRESS_PID_FILE="/tmp/resource_stress.pid"
MEMORY_USAGE_PERCENT=80
CPU_USAGE_PERCENT=90
DURATION=300

usage() {
    echo "用法: $0 {start|stop|status|restart}"
    echo "环境变量:"
    echo "  MEMORY_USAGE_PERCENT - 内存使用百分比 (默认: 80)"
    echo "  CPU_USAGE_PERCENT - CPU使用百分比 (默认: 90)" 
    echo "  DURATION - 运行时间(秒) (默认: 300)"
    exit 1
}

calculate_memory_usage() {
    local total_mem=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    local mem_to_use=$((total_mem * MEMORY_USAGE_PERCENT / 100 / 1024))
    echo $mem_to_use
}

# 更高效的CPU压力测试函数
cpu_stress() {
    local cpu_usage=$1
    local num_cores=$(nproc)
    
    echo "启动CPU压力测试，目标使用率: ${cpu_usage}%"
    
    # 方法1: 使用数学计算密集型任务
    for ((i=0; i<num_cores; i++)); do
        {
            while true; do
                # 计算密集型任务 - 计算平方根
                for ((j=0; j<100000; j++)); do
                    echo "scale=100; 4*a(1)" | bc -l > /dev/null 2>&1
                done
                # 根据目标CPU使用率调整休息时间
                sleep $((100 - cpu_usage))e-2
            done
        } &
        echo $! >> "$STRESS_PID_FILE"
    done
    
    # 方法2: 备用CPU压力测试
    for ((i=0; i<num_cores; i++)); do
        {
            while true; do
                # 另一种计算密集型任务
                awk 'BEGIN {for(i=0;i<1000000;i++){}}' > /dev/null 2>&1
                sleep $((100 - cpu_usage))e-2
            done
        } &
        echo $! >> "$STRESS_PID_FILE"
    done
}

# 改进的内存压力测试
memory_stress() {
    local mem_mb=$1
    echo "启动内存压力测试，目标使用: ${mem_mb}MB"
    
    # 计算每个进程分配的内存大小（分成多个进程）
    local chunks=4
    local chunk_size=$((mem_mb / chunks))
    
    for ((i=0; i<chunks; i++)); do
        {
            # 分配内存并保持
            if command -v python3 >/dev/null 2>&1; then
                python3 -c "
import time
# 分配内存块 (每个约 chunk_size MB)
memory_block = bytearray(1024 * 1024 * $chunk_size)
print('分配了 $chunk_size MB 内存')
while True:
    time.sleep(3600)  # 保持1小时或直到被杀死
"
            else
                # 使用dd作为备选方案
                dd if=/dev/zero of=/dev/shm/stress_mem_$i bs=1M count=$chunk_size status=none
                # 保持文件存在
                while true; do
                    sleep 3600
                done
            fi
        } &
        echo $! >> "$STRESS_PID_FILE"
    done
}

start_stress() {
    if [ -f "$STRESS_PID_FILE" ]; then
        echo "压力测试已经在运行中 (PID: $(cat $STRESS_PID_FILE | head -1))"
        return 1
    fi
    
    echo "开始资源压力测试..."
    echo "内存使用: ${MEMORY_USAGE_PERCENT}%"
    echo "CPU使用: ${CPU_USAGE_PERCENT}%"
    echo "持续时间: ${DURATION}秒"
    
    # 清空PID文件
    > "$STRESS_PID_FILE"
    
    # 计算内存使用量
    local mem_mb=$(calculate_memory_usage)
    echo "将使用大约 ${mem_mb}MB 内存"
    
    # 启动压力测试
    {
        # 启动CPU压力测试
        cpu_stress $CPU_USAGE_PERCENT
        
        # 启动内存压力测试  
        memory_stress $mem_mb
        
        echo "所有压力测试进程已启动"
        
        # 设置超时停止
        sleep $DURATION
        echo "压力测试已自动停止（超时: ${DURATION}秒）"
        stop_stress
    } &
    
    local main_pid=$!
    echo $main_pid >> "$STRESS_PID_FILE"
    echo "压力测试已启动，主PID: $main_pid"
    echo "使用 '$0 stop' 来停止测试"
    
    # 等待一下让进程启动
    sleep 2
    status_stress
}

stop_stress() {
    if [ ! -f "$STRESS_PID_FILE" ]; then
        echo "没有运行的压力测试"
        return 1
    fi
    
    echo "停止压力测试..."
    
    # 杀死所有子进程
    while read pid; do
        if [ -n "$pid" ] && kill -0 $pid 2>/dev/null; then
            # 先尝试温和终止
            kill -TERM $pid 2>/dev/null
        fi
    done < "$STRESS_PID_FILE"
    
    sleep 2
    
    # 强制杀死剩余进程
    while read pid; do
        if [ -n "$pid" ] && kill -0 $pid 2>/dev/null; then
            kill -KILL $pid 2>/dev/null
        fi
    done < "$STRESS_PID_FILE"
    
    # 清理临时文件
    rm -f /dev/shm/stress_mem_*
    rm -f "$STRESS_PID_FILE"
    
    echo "压力测试已停止"
    echo "当前资源状态:"
    free -h
    echo "负载: $(uptime)"
}

status_stress() {
    if [ -f "$STRESS_PID_FILE" ]; then
        local main_pid=$(head -1 "$STRESS_PID_FILE" 2>/dev/null)
        if [ -n "$main_pid" ] && kill -0 $main_pid 2>/dev/null; then
            echo "压力测试正在运行 (主PID: $main_pid)"
            echo -e "\n当前系统资源使用情况:"
            
            # 显示详细的资源信息
            echo "CPU使用率:"
            top -bn1 | grep "Cpu(s)" | head -1
            echo -e "\n内存使用情况:"
            free -h
            echo -e "\n负载情况:"
            uptime
            echo -e "\n压力测试进程:"
            ps -p $(grep -v '^$' "$STRESS_PID_FILE" | tr '\n' ',' | sed 's/,$//') -o pid,pcpu,pmem,comm 2>/dev/null || echo "无法获取进程信息"
        else
            echo "压力测试PID文件存在但进程未运行，清理中..."
            stop_stress
        fi
    else
        echo "压力测试未运行"
    fi
}

# 检查必要工具
check_dependencies() {
    local missing=()
    
    if ! command -v bc >/dev/null 2>&1; then
        missing+=("bc")
    fi
    
    if ! command -v awk >/dev/null 2>&1; then
        missing+=("awk")
    fi
    
    if [ ${#missing[@]} -ne 0 ]; then
        echo "警告: 缺少以下工具: ${missing[*]}"
        echo "部分功能可能无法正常工作"
        return 1
    fi
    return 0
}

# 主程序
if [ $# -lt 1 ]; then
    usage
fi

# 检查依赖
check_dependencies

# 读取环境变量
[ ! -z "$MEMORY_USAGE_PERCENT" ] && MEMORY_USAGE_PERCENT=$MEMORY_USAGE_PERCENT
[ ! -z "$CPU_USAGE_PERCENT" ] && CPU_USAGE_PERCENT=$CPU_USAGE_PERCENT  
[ ! -z "$DURATION" ] && DURATION=$DURATION

case "$1" in
    start)
        start_stress
        ;;
    stop)
        stop_stress
        ;;
    status)
        status_stress
        ;;
    restart)
        stop_stress
        sleep 3
        start_stress
        ;;
    *)
        usage
        ;;
esac