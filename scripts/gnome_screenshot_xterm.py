import os
import subprocess
import time
import re

def get_xterm_window_id(target_title):
    """获取xterm窗口ID"""
    try:
        result = subprocess.run(
            f'xwininfo -name "{target_title}"',
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        for line in result.stdout.splitlines():
            if "Window id:" in line:
                return line.split()[2]  # 提取窗口ID（如0x60000d）
        print(f"未找到标题为'{target_title}'的窗口")
        return None
    except Exception as e:
        print(f"获取窗口ID失败：{e}")
        return None

def gnome_screenshot_xterm(window_id, save_path):
    """使用gnome-screenshot截取指定窗口"""
    if not window_id:
        return False
    
    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # 命令解析：
        # -w：指定窗口截图（需窗口ID）
        # -f：输出文件路径
        cmd = f'gnome-screenshot -w -f "{save_path}" --window-id {window_id}'
        subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            print(f"截图成功，保存至：{os.path.abspath(save_path)}")
            return True
        else:
            print("截图文件无效")
            return False
    
    except subprocess.CalledProcessError as e:
        print(f"截图命令失败：{e.stderr}")
        return False
    except Exception as e:
        print(f"处理失败：{e}")
        return False

def main():
    target_title = "gnome-screenshot_test"
    output_dir = "screenshots"
    save_path = os.path.join(output_dir, f"{target_title}_gnome.png")
    
    os.environ["DISPLAY"] = ":0"
    
    # 启动xterm
    xterm_cmd = (
        f'xterm -T "{target_title}" -geometry 120x40+50+50 '
        f'-e \'ls -lrt;pwd;date;bash --rcfile ~/.bashrc_no_title --noprofile\' &'
    )
    terminal = subprocess.Popen(
        xterm_cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2)  # 等待窗口启动
    
    # 获取窗口ID并截图
    window_id = get_xterm_window_id(target_title)
    if window_id:
        gnome_screenshot_xterm(window_id, save_path)

if __name__ == "__main__":
    main()
