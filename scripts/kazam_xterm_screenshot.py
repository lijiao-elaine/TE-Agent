import os
import subprocess
import time
import re

def get_xterm_window_geometry(target_title):
    """获取xterm窗口坐标和尺寸"""
    try:
        result = subprocess.run(
            f'xwininfo -name "{target_title}"',
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        
        x = re.search(r'Absolute upper-left X:\s+(\d+)', result.stdout).group(1)
        y = re.search(r'Absolute upper-left Y:\s+(\d+)', result.stdout).group(1)
        width = re.search(r'Width:\s+(\d+)', result.stdout).group(1)
        height = re.search(r'Height:\s+(\d+)', result.stdout).group(1)
        
        return (int(x), int(y), int(width), int(height))
    except Exception as e:
        print(f"获取窗口信息失败：{e}")
        return None

def kazam_capture_xterm(save_path):
    """使用Kazam图形界面延迟截图（绕开Python GTK依赖）"""
    try:
        # 确保输出目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # 命令解析：
        # --screenshot：截图模式
        # --delay 3：延迟3秒（足够手动选择xterm窗口）
        # --filename：保存路径
        cmd = f'kazam --screenshot --delay 3 --filename "{save_path}"'
        subprocess.Popen(cmd, shell=True)  # 非阻塞运行，避免等待
        
        print(f"请在3秒内用鼠标框选xterm窗口...")
        time.sleep(5)  # 等待截图完成
        
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            print(f"Kazam截图成功，保存至：{os.path.abspath(save_path)}")
            return True
        else:
            print("截图失败，请检查操作")
            return False
    
    except Exception as e:
        print(f"执行失败：{e}")
        return False

def main():
    target_title = "kazam_test"
    output_dir = "screenshots"
    save_path = os.path.join(output_dir, f"{target_title}_kazam.png")
    
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
    time.sleep(2)
    
    # 获取窗口信息（仅用于提示位置）
    geometry = get_xterm_window_geometry(target_title)
    if geometry:
        x, y, w, h = geometry
        print(f"xterm窗口位置：左上角({x},{y})，宽{w}，高{h}")
    
    # 截图（手动框选模式）
    kazam_capture_xterm(save_path)

if __name__ == "__main__":
    main()
