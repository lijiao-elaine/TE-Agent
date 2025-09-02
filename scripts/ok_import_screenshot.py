import os
import subprocess
import time
import pdb
from datetime import datetime

def get_xterm_window_id(target_title):
    """通过xwininfo获取指定标题的xterm窗口ID"""
    try:
        # 执行xwininfo命令获取窗口信息
        result = subprocess.run(
            f'xwininfo -name "{target_title}"',
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        
        # 从输出中提取窗口ID（line的格式： 'xwininfo: Window id: 0x60000d "test"'）
        for line in result.stdout.splitlines():
            if "Window id:" in line:
                window_id = line.split()[3]  # 取第4个元素（0xe0000d），多个同名终端时，会错乱，只取了第一个同名终端就返回了
                print(f"成功获取xterm窗口ID：{window_id}")
                return window_id
        
        print(f"未在输出中找到窗口ID")
        return None
    
    except subprocess.CalledProcessError as e:
        print(f"获取窗口ID失败：命令执行错误 - {e.stderr}")
        return None
    except Exception as e:
        print(f"获取窗口ID失败：{str(e)}")
        return None

def screenshot_xterm_by_id(window_id, save_path):
    """使用import命令截取指定ID的xterm窗口"""
    if not window_id:
        print("窗口ID为空，无法截图")
        return False
    
    try:
        # 确保输出目录存在
        save_dir = os.path.dirname(save_path)
        if save_dir and not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)
        
        # 执行import命令截图（指定窗口ID）
        cmd = f'import -window {window_id} "{save_path}"'
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        #pdb.set_trace()
        # 验证截图文件是否生成
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            print(f"截图成功，保存至：{os.path.abspath(save_path)}")
            return True
        else:
            print(f"截图失败，未生成有效文件")
            return False
    
    except subprocess.CalledProcessError as e:
        print(f"截图命令执行失败：{e.stderr}")
        return False
    except Exception as e:
        print(f"截图过程出错：{str(e)}")
        return False

def main():
    # 配置参数
    target_title = "import_test"  # xterm窗口标题（与启动时的-T参数一致）
    output_dir = "screenshots"
    save_filename = f"xterm_{target_title}_import.png"
    save_path = os.path.join(output_dir, save_filename)
    
    # 设置DISPLAY环境变量（适配MobaXterm）
    os.environ["DISPLAY"] = ":0"
    
    # 1. 启动xterm窗口
    print("启动 xterm 窗口前的时间：", datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"))
    print(f"启动标题为'{target_title}'的xterm窗口...")
    xterm_cmd = (
        f'xterm -T "{target_title}" -geometry 120x40+50+50 '
        f'-e \'ls -lrt;pwd;date;bash --rcfile ~/.bashrc_no_title --noprofile\' &'
    )
    os.system(xterm_cmd)
    time.sleep(2)  # 等待窗口完全启动
    
    # 2. 获取窗口ID
    window_id = get_xterm_window_id(target_title)
    if not window_id:
        print("无法获取窗口ID，终止截图")
        return
    
    # 3. 截取窗口并保存
    screenshot_xterm_by_id(window_id, save_path)
    print("截图完成后的时间：", datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"))
    
if __name__ == "__main__":
    main()
