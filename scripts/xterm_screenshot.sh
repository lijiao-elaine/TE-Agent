#!/bin/bash

# 支持的工具列表
SUPPORTED_TOOLS="flameshot shutter kazam deepin-screenshot"

# 显示帮助信息
show_help() {
    echo "用法: $0 [选项]"
    echo "对xterm终端进行截图"
    echo
    echo "选项:"
    echo "  --tool TOOL     指定截图工具，支持的工具: $SUPPORTED_TOOLS"
    echo "  --help          显示此帮助信息并退出"
    echo
    echo "示例:"
    echo "  $0 --tool flameshot   使用flameshot对xterm终端截图"
    echo "  $0 --tool shutter     使用shutter对xterm终端截图"
}

# 检查工具是否安装
check_dependency() {
    local tool=$1
    if ! command -v "$tool" &> /dev/null; then
        echo "错误: 工具 '$tool' 未安装。请先安装它。"
        echo "安装命令: sudo apt install $tool"
        exit 1
    fi
}

# 查找xterm窗口ID
find_xterm_window() {
    local window_id
    # 使用wmctrl查找xterm窗口
    window_id=$(wmctrl -l | grep -i "xterm" | head -n 1 | awk '{print $1}')
    
    if [ -z "$window_id" ]; then
        echo "错误: 未找到xterm终端窗口"
        exit 1
    fi
    
    echo "$window_id"
}

# 主函数
main() {
    local tool=""
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --tool)
                tool="$2"
                shift 2
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                echo "错误: 未知选项 '$1'"
                echo "使用 --help 查看帮助信息"
                exit 1
                ;;
        esac
    done
    
    # 检查是否指定了工具
    if [ -z "$tool" ]; then
        echo "错误: 必须使用 --tool 指定截图工具"
        echo "使用 --help 查看帮助信息"
        exit 1
    fi
    
    # 检查工具是否在支持的列表中
    if ! echo "$SUPPORTED_TOOLS" | grep -qw "$tool"; then
        echo "错误: 不支持的工具 '$tool'，支持的工具: $SUPPORTED_TOOLS"
        exit 1
    fi
    
    # 检查依赖
    check_dependency "$tool"
    
    # 对于wmctrl也是一个依赖
    check_dependency "wmctrl"
    
    # 查找xterm窗口
    local xterm_window_id=$(find_xterm_window)
    echo "找到xterm窗口，ID: $xterm_window_id"
    
    # 根据不同工具执行截图
    case "$tool" in
        flameshot)
            echo "使用flameshot对xterm终端截图..."
            flameshot gui --region=$(xdotool getwindowgeometry --shell "$xterm_window_id" | awk -F'=' '/X|Y|WIDTH|HEIGHT/ {print $2}' | tr '\n' ' ' | awk '{print $1","$2","$3","$4}')
            ;;
        shutter)
            echo "使用shutter对xterm终端截图..."
            shutter -w "$xterm_window_id" -e
            ;;
        kazam)
            echo "使用kazam对xterm终端截图..."
            # Kazam主要用于录屏，但也支持截图
            # 先启动kazam，然后延迟2秒，再截图，最后关闭kazam
            kazam --screenshot --delay 2 &
            sleep 3
            pkill kazam
            ;;
        deepin-screenshot)
            echo "使用deepin-screenshot对xterm终端截图..."
            deepin-screenshot -g "$(xdotool getwindowgeometry --shell "$xterm_window_id" | awk -F'=' '/X|Y|WIDTH|HEIGHT/ {print $2}' | tr '\n' ' ' | awk '{print $1","$2" "$3"x"$4}')"
            ;;
        *)
            echo "错误: 未实现的工具 '$tool'"
            exit 1
            ;;
    esac
    
    echo "截图完成"
}

# 执行主函数
main "$@"
