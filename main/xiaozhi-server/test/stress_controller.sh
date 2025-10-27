#!/bin/bash
# 文件名: stress_controller.sh
# 描述: 压力测试控制器 - 更简单的接口

STRESS_SCRIPT="./resource_stress_test.sh"

if [ ! -f "$STRESS_SCRIPT" ]; then
    echo "错误: 找不到压力测试脚本 $STRESS_SCRIPT"
    exit 1
fi

case "$1" in
    "start")
        # 可选的参数设置
        export MEMORY_USAGE_PERCENT=${2:-85}
        export CPU_USAGE_PERCENT=${3:-95}
        export DURATION=${4:-600}  # 10分钟默认
        
        echo "启动压力测试: 内存${MEMORY_USAGE_PERCENT}% CPU${CPU_USAGE_PERCENT}% 持续时间${DURATION}秒"
        bash "$STRESS_SCRIPT" start
        ;;
    "stop")
        bash "$STRESS_SCRIPT" stop
        ;;
    "status")
        bash "$STRESS_SCRIPT" status
        ;;
    "quick")
        # 快速测试 - 2分钟，70%资源
        echo "启动快速压力测试 (2分钟, 70%资源)"
        export MEMORY_USAGE_PERCENT=70
        export CPU_USAGE_PERCENT=70
        export DURATION=120
        bash "$STRESS_SCRIPT" start
        ;;
    *)
        echo "用法: $0 {start [mem% cpu% duration]|stop|status|quick}"
        echo "示例:"
        echo "  $0 start           # 使用默认参数"
        echo "  $0 start 80 90 300 # 内存80%, CPU90%, 5分钟"
        echo "  $0 quick           # 快速测试"
        echo "  $0 stop            # 停止测试"
        echo "  $0 status          # 查看状态"
        ;;
esac
