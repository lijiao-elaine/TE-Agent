import os
import subprocess
import time
import re
import pdb

def get_xterm_window_geometry(target_title):
    """获取xterm窗口的坐标和尺寸（格式：x,y,width,height）"""
    try:
        # 使用xwininfo获取窗口几何信息
        result = subprocess.run(
            f'xwininfo -name "{target_title}"',
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        
        
        # 提取关键信息
        x = re.search(r'Absolute upper-left X:\s+(\d+)', result.stdout).group(1)
        y = re.search(r'Absolute upper-left Y:\s+(\d+)', result.stdout).group(1)
        width = re.search(r'Width:\s+(\d+)', result.stdout).group(1)
        height = re.search(r'Height:\s+(\d+)', result.stdout).group(1)
        
        print(f"xterm窗口几何信息：x={x}, y={y}, 宽={width}, 高={height}")
        return f"{x},{y},{width},{height}"  # Flameshot需要的格式
    
    except subprocess.CalledProcessError as e:
        print(f"获取窗口信息失败：{e.stderr}")
        return None
    except (AttributeError, re.error):
        print("无法解析窗口几何信息")
        return None

def flameshot_capture_xterm(geometry, save_path):
    """使用Flameshot截取指定区域（xterm窗口）"""
    if not geometry:
        return False
    
    try:
        # 确保输出目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Flameshot命令：-g指定区域，-p指定保存路径
        #cmd = f'flameshot capture -g {geometry} -p "{save_path}"'
        cmd = f'flameshot -r {geometry} -p "{save_path}"'
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        #pdb.set_trace()
        # 验证截图
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            print(f"Flameshot截图成功，保存至：{os.path.abspath(save_path)}")
            return True
        else:
            print("Flameshot生成的截图文件无效")
            return False
    
    except subprocess.CalledProcessError as e:
        print(f"Flameshot执行失败：{e.stderr}")
        return False

def main():
    target_title = "flameshot_test"  # xterm窗口标题
    output_dir = "screenshots"
    save_path = os.path.join(output_dir, f"xterm_{target_title}_flameshot.png")
    
    # 设置显示环境
    os.environ["DISPLAY"] = ":0"
    
    # 1. 启动xterm窗口
    print(f"启动标题为'{target_title}'的xterm窗口...")

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
    
    # 2. 获取窗口几何信息
    geometry = get_xterm_window_geometry(target_title)
    if not geometry:
        print("无法获取窗口信息，截图终止")
        return
    
    # 3. 用Flameshot截图
    flameshot_capture_xterm(geometry, save_path)

if __name__ == "__main__":
    main()
