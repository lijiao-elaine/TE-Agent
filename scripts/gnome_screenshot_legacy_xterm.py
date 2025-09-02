import os
import subprocess
import time
import re
import pyautogui  # 用于激活窗口

def get_xterm_window_geometry(target_title):
    """获取xterm窗口的坐标和尺寸"""
    try:
        result = subprocess.run(
            f'xwininfo -name "{target_title}"',
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        
        x = int(re.search(r'Absolute upper-left X:\s+(\d+)', result.stdout).group(1))
        y = int(re.search(r'Absolute upper-left Y:\s+(\d+)', result.stdout).group(1))
        width = int(re.search(r'Width:\s+(\d+)', result.stdout).group(1))
        height = int(re.search(r'Height:\s+(\d+)', result.stdout).group(1))
        
        return (x, y, width, height)
    except Exception as e:
        print(f"获取窗口信息失败：{e}")
        return None

def gnome_screenshot_xterm(geometry, save_path):
    """使用旧版本gnome-screenshot截图（无--window-id参数）"""
    if not geometry:
        return False
    
    x, y, width, height = geometry
    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # 1. 移动鼠标到窗口内激活（确保窗口在最上层）
        pyautogui.moveTo(x + 10, y + 10, duration=0.5)  # 移动到窗口内10px位置
        pyautogui.click()  # 点击激活窗口
        time.sleep(0.5)
        
        # 2. 截取整个屏幕
        temp_fullscreen = "/tmp/fullscreen_temp.png"
        subprocess.run(
            f'gnome-screenshot -f "{temp_fullscreen}"',
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        
        # 3. 裁剪出xterm窗口区域
        from PIL import Image
        with Image.open(temp_fullscreen) as img:
            # 裁剪区域：(左, 上, 右, 下)
            crop_area = (x, y, x + width, y + height)
            cropped_img = img.crop(crop_area)
            cropped_img.save(save_path)
        
        # 清理临时文件
        os.remove(temp_fullscreen)
        print(f"截图成功，保存至：{os.path.abspath(save_path)}")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"截图命令失败：{e.stderr}")
        return False
    except Exception as e:
        print(f"处理失败：{e}")
        return False

def main():
    target_title = "gnome_legacy_test"
    output_dir = "screenshots"
    save_path = os.path.join(output_dir, f"{target_title}_gnome_legacy.png")
    
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
    
    # 获取窗口几何信息并截图
    geometry = get_xterm_window_geometry(target_title)
    if geometry:
        gnome_screenshot_xterm(geometry, save_path)

if __name__ == "__main__":
    main()
