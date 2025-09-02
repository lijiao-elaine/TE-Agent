# 脚本最顶部：禁用 MouseInfo，避免 tkinter 警告
import os
os.environ["PYAUTOGUI_DONT_USE_MOUSEINFO"] = "1"
os.environ["DISPLAY"] = ":0"

# 导入依赖
import pyautogui
import subprocess
import re
import time
from PIL import Image  # 用于图片处理

def get_xterm_windows():
    """解析 xwininfo -root -tree，提取所有 xterm 窗口的信息（坐标、尺寸、标题）"""
    try:
        # 执行命令：获取根窗口下所有子窗口的树状信息
        output = subprocess.check_output(
            'xwininfo -root -tree',
            shell=True,
            text=True
        )
        
        # 正则表达式：匹配 xterm 窗口的关键信息
        # 匹配格式示例："  0xe0000d "test": ("xterm" "XTerm")  724x524+100+100  +100+100"
        # 分组说明：1.空格 2.窗口ID 3.标题 4.宽度 5.高度 6.X坐标 7.Y坐标
        pattern = r'\s+(0x[0-9a-fA-F]+)\s+"([^"]+)"\s*:\s*\("xterm" "XTerm"\)\s+(\d+)x(\d+)\+(\d+)\+(\d+)'
        matches = re.findall(pattern, output)
        
        xterm_windows = []
        for match in matches:
            window_id, title, width, height, x, y = match
            xterm_windows.append({
                "id": window_id.strip(),
                "title": title.strip(),
                "width": int(width),    # 窗口宽度（像素）
                "height": int(height),  # 窗口高度（像素）
                "x": int(x),            # 窗口左上角X坐标（绝对坐标，相对于屏幕）
                "y": int(y)             # 窗口左上角Y坐标（绝对坐标，相对于屏幕）
            })
        return xterm_windows
    except Exception as e:
        print(f"解析 xterm 窗口信息失败：{e}")
        return []

def get_target_xterm_position(target_title):
    """从所有 xterm 窗口中，按标题精确匹配目标窗口的坐标和尺寸"""
    xterm_windows = get_xterm_windows()
    if not xterm_windows:
        print("未找到任何 xterm 窗口")
        return None
    
    # 精确匹配标题（避免模糊匹配导致的错误）
    target_window = next(
        (win for win in xterm_windows if win["title"] == target_title),
        None
    )
    
    if not target_window:
        print(f"未找到标题为 '{target_title}' 的 xterm 窗口（已找到的标题：{[win['title'] for win in xterm_windows]}）")
        return None
    
    # 返回坐标和尺寸（left=x, top=y, width=width, height=height）
    return (
        target_window["x"],
        target_window["y"],
        target_window["width"],
        target_window["height"]
    )

def screenshot_xterm(target_title, save_path="xterm_screenshot.png"):
    """用 scrot 命令精准截图目标 xterm 窗口（避免坐标错误）"""
    # 获取目标窗口的正确坐标和尺寸
    pos = get_target_xterm_position(target_title)
    if not pos:
        return False
    left, top, width, height = pos
    print(f"找到目标 xterm 窗口：坐标({left}, {top})，尺寸({width}x{height})")
    
    # 验证坐标和尺寸有效性（避免截取空白区域）
    if width <= 0 or height <= 0:
        print(f"无效的窗口尺寸：{width}x{height}（宽高必须大于0）")
        return False
    if left < 0 or top < 0:
        print(f"窗口坐标超出屏幕范围：({left}, {top})")
        return False
    
    # 直接调用 scrot 命令截图（最可靠的方式，避开 pyautogui 封装问题）
    try:
        temp_png = "/tmp/xterm_scrot_temp.png"
        # scrot -a 左,上,宽,高 输出路径：-a 参数指定截取区域
        subprocess.run(
            f"scrot -a {left},{top},{width},{height} {temp_png}",
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # 验证截图文件有效性（避免黑色/空文件）
        if not os.path.exists(temp_png) or os.path.getsize(temp_png) < 100:
            print(f"生成的截图文件无效（大小：{os.path.getsize(temp_png) if os.path.exists(temp_png) else 0} 字节）")
            return False
        
        # 保存截图到目标路径
        with Image.open(temp_png) as img:
            img.save(save_path)
        os.remove(temp_png)  # 清理临时文件
        print(f"截图成功！已保存至：{save_path}")
        return True
    except Exception as e:
        print(f"scrot 截图失败：{e}")
        # 清理临时文件（避免残留）
        if os.path.exists(temp_png):
            os.remove(temp_png)
        return False

def main():
    target_title = "test"  # 与 xterm 启动时的 -T 参数完全一致
    output_dir = "screenshots"
    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, f"xterm_pyautogui_{target_title}_screenshot.png")

    # 1. 启动 xterm 窗口（指定标题和位置，避免超出屏幕）
    print(f"启动 xterm 窗口（标题：{target_title}）...")
    # -geometry 120x40+100+100：120列宽、40行高，左上角坐标(100,100)
    command = f'xterm -T "{target_title}" -geometry 120x40+100+100 -e \'ls -lrt;pwd;bash --rcfile ~/.bashrc_no_title --noprofile\' &'
    os.system(command)
    time.sleep(2)  # 等待窗口完全渲染（关键：避免窗口未启动就截图）

    # 2. 精准截图目标 xterm 窗口
    screenshot_xterm(target_title, save_path)

if __name__ == "__main__":
    main()