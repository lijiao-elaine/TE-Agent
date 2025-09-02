import argparse
import subprocess
import sys
import os
from time import sleep

# 支持的工具列表
SUPPORTED_TOOLS = ["PIL", "mss", "pyautogui", "gnome-screenshot"]

def show_help():
    """显示帮助信息"""
    print("用法: python3 xterm_screenshot.py [选项]")
    print("对xterm终端进行截图")
    print()
    print("选项:")
    print("  --tool TOOL     指定截图工具/库，支持的工具: {}".format(", ".join(SUPPORTED_TOOLS)))
    print("  --help          显示此帮助信息并退出")
    print("  --output FILE   指定输出文件路径，默认为screenshot.png")
    print()
    print("示例:")
    print("  python3 xterm_screenshot.py --tool PIL --output xterm.png")
    print("  python3 xterm_screenshot.py --tool gnome-screenshot")

def check_dependency(tool):
    """检查依赖是否安装"""
    try:
        if tool == "PIL":
            import PIL.Image
        elif tool == "mss":
            import mss
        elif tool == "pyautogui":
            import pyautogui
        elif tool == "gnome-screenshot":
            # 检查系统是否安装了gnome-screenshot
            subprocess.run(["gnome-screenshot", "--version"], check=True, 
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            print(f"错误: 不支持的工具 '{tool}'")
            sys.exit(1)
    except ImportError:
        print(f"错误: Python库 '{tool.lower()}' 未安装。")
        print(f"安装命令: pip install {tool.lower()}")
        sys.exit(1)
    except subprocess.CalledProcessError:
        print(f"错误: 工具 '{tool}' 未安装。")
        print("安装命令: sudo apt install gnome-screenshot")
        sys.exit(1)

def find_xterm_window():
    """查找xterm窗口的位置和大小"""
    try:
        # 使用wmctrl获取窗口信息
        result = subprocess.run(["wmctrl", "-lG"], capture_output=True, text=True, check=True)
        lines = result.stdout.splitlines()
        
        # 查找包含xterm的窗口
        xterm_line = None
        for line in lines:
            if "xterm" in line.lower():
                xterm_line = line
                break
        
        if not xterm_line:
            print("错误: 未找到xterm终端窗口")
            sys.exit(1)
        
        # 解析窗口信息
        parts = xterm_line.split()
        window_id = parts[0]
        x = int(parts[2])
        y = int(parts[3])
        width = int(parts[4])
        height = int(parts[5])
        
        print(f"找到xterm窗口，位置: ({x}, {y}), 大小: {width}x{height}")
        return x, y, width, height
        
    except subprocess.CalledProcessError:
        print("错误: 无法获取窗口信息，请确保wmctrl已安装")
        print("安装命令: sudo apt install wmctrl")
        sys.exit(1)
    except Exception as e:
        print(f"错误: 查找xterm窗口时发生错误: {str(e)}")
        sys.exit(1)

def capture_with_pil(x, y, width, height, output_file):
    """使用PIL进行截图"""
    from PIL import ImageGrab
    
    # 截取指定区域
    screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
    screenshot.save(output_file)
    print(f"截图已保存至 {output_file}")

def capture_with_mss(x, y, width, height, output_file):
    """使用mss进行截图"""
    from mss import mss
    import mss.tools
    
    # 定义截图区域
    monitor = {
        "top": y,
        "left": x,
        "width": width,
        "height": height
    }
    
    with mss() as sct:
        # 捕获区域
        sct_img = sct.grab(monitor)
        # 保存截图
        mss.tools.to_png(sct_img.rgb, sct_img.size, output=output_file)
    
    print(f"截图已保存至 {output_file}")

def capture_with_pyautogui_old(x, y, width, height, output_file):
    """使用pyautogui进行截图"""
    import pyautogui
    
    # 截取指定区域
    screenshot = pyautogui.screenshot(region=(x, y, width, height))
    screenshot.save(output_file)
    print(f"截图已保存至 {output_file}")

def capture_with_pyautogui():
    """使用pyautogui进行截图"""
    import pyautogui
    import time

    # 等待 xterm 启动
    time.sleep(2)

    # 方法 1：直接截取全屏（适合后续手动裁剪，或已知窗口位置）
    # screenshot = pyautogui.screenshot(region=(200, 200, 800, 600))  # (left, top, width, height)
    # screenshot.save("xterm_screenshot.png")

    # 方法 2：通过图像识别定位 xterm 窗口（更智能）
    # 提前截取 xterm 窗口的特征图（如标题栏的一部分），保存为 xterm_title.png
    try:
        # 查找特征图在屏幕中的位置（返回左上角坐标）
        xterm_location = pyautogui.locateOnScreen("xterm_title.png", confidence=0.8)
        if xterm_location:
            # 获取窗口中心坐标，模拟点击（可选，确保窗口在前台）
            x, y = pyautogui.center(xterm_location)
            pyautogui.click(x, y)
            # 截取整个窗口（假设特征图位置为窗口左上角，根据实际调整宽高）
            screenshot = pyautogui.screenshot(region=(
                xterm_location.left,
                xterm_location.top,
                800,  # 窗口宽度
                600   # 窗口高度
            ))
            screenshot.save("xterm_screenshot.png")
            print("截图完成")
        else:
            print("未找到 xterm 窗口")
    except Exception as e:
        print(f"截图失败：{e}")


def capture_with_gnome_screenshot(x, y, width, height, output_file):
    """使用gnome-screenshot进行截图"""
    try:
        # 构建截图命令
        cmd = [
            "gnome-screenshot",
            "--area", f"{x},{y},{width},{height}",
            "--file", output_file
        ]
        
        # 执行命令
        subprocess.run(cmd, check=True)
        print(f"截图已保存至 {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"错误: 使用gnome-screenshot截图失败: {str(e)}")
        sys.exit(1)

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--tool", help="指定截图工具")
    parser.add_argument("--help", action="store_true", help="显示帮助信息")
    parser.add_argument("--output", default="screenshot.png", help="指定输出文件路径")
    
    args = parser.parse_args()
    
    # 显示帮助信息
    if args.help:
        show_help()
        sys.exit(0)
    
    # 检查是否指定了工具
    if not args.tool:
        print("错误: 必须使用 --tool 指定截图工具")
        print("使用 --help 查看帮助信息")
        sys.exit(1)
    
    # 检查工具是否在支持的列表中
    if args.tool not in SUPPORTED_TOOLS:
        print(f"错误: 不支持的工具 '{args.tool}'，支持的工具: {', '.join(SUPPORTED_TOOLS)}")
        sys.exit(1)
    
    # 检查依赖
    check_dependency(args.tool)
    
    # 检查wmctrl是否安装
    try:
        subprocess.run(["wmctrl", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        print("错误: wmctrl未安装，无法查找xterm窗口")
        print("安装命令: sudo apt install wmctrl")
        sys.exit(1)
    
    # 查找xterm窗口
    #x, y, width, height = find_xterm_window()
    
    # 根据选择的工具进行截图
    if args.tool == "PIL":
        capture_with_pil(x, y, width, height, args.output)
    elif args.tool == "mss":
        capture_with_mss(x, y, width, height, args.output)
    elif args.tool == "pyautogui":
        #capture_with_pyautogui(x, y, width, height, args.output)
        capture_with_pyautogui()
    elif args.tool == "gnome-screenshot":
        capture_with_gnome_screenshot(x, y, width, height, args.output)

if __name__ == "__main__":
    main()
