import os
import subprocess
import time
import re

def get_xterm_window_id(target_title):
    """获取xterm窗口的ID"""
    try:
        result = subprocess.run(
            f'xwininfo -name "{target_title}"',
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        # 提取窗口ID（格式如：0x60000d）
        for line in result.stdout.splitlines():
            if "Window id:" in line:
                return line.split()[3]
        print(f"未找到标题为'{target_title}'的窗口")
        return None
    except Exception as e:
        print(f"获取窗口ID失败：{e}")
        return None

def deepin_screenshot_xterm(window_id, save_path):
    """使用deepin-screenshot截取指定窗口ID的xterm终端"""
    if not window_id:
        return False
    
    try:
        # 确保输出目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # deepin-screenshot命令解析：
        # -w <窗口ID>：指定截取的窗口
        # -s：静默模式（不显示编辑界面）
        # -o <路径>：输出文件路径
        cmd = f'deepin-screenshot -w {window_id} -s -o "{save_path}"'
        subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        
        # 验证截图有效性
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            print(f"deepin-screenshot截图成功，保存至：{os.path.abspath(save_path)}")
            return True
        else:
            print("生成的截图文件无效")
            return False
    
    except subprocess.CalledProcessError as e:
        print(f"截图命令执行失败：{e.stderr}")
        return False
    except Exception as e:
        print(f"处理过程出错：{str(e)}")
        return False

def main():
    target_title = "deepin_test"  # xterm窗口标题
    output_dir = "screenshots"
    save_path = os.path.join(output_dir, f"{target_title}_deepin.png")
    
    # 设置显示环境（适用于远程或WSL环境）
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
    time.sleep(2)  # 等待窗口完全启动
    
    # 2. 获取xterm窗口ID
    window_id = get_xterm_window_id(target_title)
    print(f"获取的窗口ID为：{window_id}")
    if not window_id:
        print("无法获取窗口ID，截图终止")
        return
    
    # 3. 使用deepin-screenshot截图
    deepin_screenshot_xterm(window_id, save_path)

if __name__ == "__main__":
    main()
