import os
import subprocess
import time
from PIL import Image
import pdb
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
                return line.split()[3]
        print(f"未找到标题为'{target_title}'的窗口")
        return None
    except subprocess.CalledProcessError as e:
        print(f"获取窗口ID失败：{e.stderr}")
        return None

def capture_xterm_with_convert_and_pil(window_id, save_path):
    """用convert转格式后再用PIL处理"""
    if not window_id:
        return False
    
    # 临时文件
    temp_xwd = "/tmp/temp.xwd"
    temp_png = "/tmp/temp.png"
    
    try:
        # 1. xwd抓取窗口到临时文件
        #pdb.set_trace()
        subprocess.run(
            f"xwd -id {window_id} -out /tmp/temp.xwd",
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # 2. 用convert将XWD转PNG（ImageMagick工具）
        subprocess.run(
            f'convert {temp_xwd} {temp_png}',
            shell=True,
            check=True,
            capture_output=True
        )
        
        # 3. PIL读取PNG并处理（此时格式一定兼容）
        with Image.open(temp_png) as img:
            # 这里可以添加PIL的图像处理逻辑（如裁剪、缩放等）
            img.save(save_path)
            print(f"截图成功：{os.path.abspath(save_path)}")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败：{e.stderr.decode('utf-8')}")
    except Exception as e:
        print(f"处理失败：{str(e)}")
    finally:
        # 清理临时文件
        for f in [temp_xwd, temp_png]:
            if os.path.exists(f):
                os.remove(f)
    
    return False

def main():
    target_title = "test"
    output_dir = "screenshots"
    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, f"{target_title}_final.png")
    
    os.environ["DISPLAY"] = ":0"
    
    # 启动xterm
    xterm_cmd = (
        f'xterm -T "{target_title}" -geometry 120x40+50+50 '
        f'-e \'ls -lrt;pwd;date;bash --rcfile ~/.bashrc_no_title --noprofile\' &'
    )
    #os.system(xterm_cmd)

    terminal = subprocess.Popen(
        xterm_cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2)
    
    # 截图
    window_id = get_xterm_window_id(target_title)
    print(f"找到id为：'{window_id}'的窗口")
    if window_id:
        capture_xterm_with_convert_and_pil(window_id, save_path)

if __name__ == "__main__":
    main()
