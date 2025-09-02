import os
import subprocess
import time
import re

def get_xterm_window_id(target_title):
    """获取指定标题的xterm窗口ID"""
    try:
        result = subprocess.run(
            f'xwininfo -name "{target_title}"',
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        # 从输出中提取窗口ID
        for line in result.stdout.splitlines():
            if "Window id:" in line:
                return line.split()[23]  # 返回窗口ID（如0x60000d）
        print(f"未找到标题为'{target_title}'的窗口")
        return None
    except subprocess.CalledProcessError as e:
        print(f"获取窗口ID失败：{e.stderr}")
        return None

def shutter_capture_xterm(window_id, save_path):
    """使用Shutter截取指定窗口ID的xterm终端"""
    if not window_id:
        return False
    
    try:
        # 确保输出目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Shutter命令解析：
        # -w <窗口ID>：指定截取的窗口
        # -o <路径>：输出文件路径
        # -e：截图后不打开编辑窗口（完全自动化）
        cmd = f'shutter -w {window_id} -o "{save_path}" -e'
        subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        
        # 验证截图文件有效性
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            print(f"Shutter截图成功，保存至：{os.path.abspath(save_path)}")
            return True
        else:
            print("Shutter生成的截图文件无效")
            return False
    
    except subprocess.CalledProcessError as e:
        print(f"Shutter命令执行失败：{e.stderr}")
        return False
    except Exception as e:
        print(f"截图过程出错：{str(e)}")
        return False

def main():
    target_title = "shutter_test"  # xterm窗口标题（与启动时-T参数一致）
    output_dir = "screenshots"
    save_path = os.path.join(output_dir, f"xterm_{target_title}_shutter.png")
    
    # 设置DISPLAY环境变量（适配X服务器）
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
    time.sleep(2)  # 等待窗口完全启动并渲染
    
    # 2. 获取xterm窗口ID
    window_id = get_xterm_window_id(target_title)
    if not window_id:
        print("无法获取窗口ID，截图终止")
        return
    
    # 3. 使用Shutter截图
    shutter_capture_xterm(window_id, save_path)

if __name__ == "__main__":
    main()
