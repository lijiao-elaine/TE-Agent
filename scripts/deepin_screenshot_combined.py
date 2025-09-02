import os
import subprocess
import time
import re
import pdb

def get_window_id_by_xwininfo(target_title):
    """使用xwininfo获取指定标题窗口的ID"""
    try:
        # 通过窗口标题精确获取信息
        result = subprocess.run(
            f'xwininfo -name "{target_title}"',
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        
        # 从输出中提取窗口ID（格式如 0x180000d）
        match = re.search(r'Window id:\s+(\w+)', result.stdout)
        if match:
            window_id = match.group(1)
            print(f"xwininfo获取窗口ID成功：{window_id}")
            return window_id
        else:
            print("未在xwininfo输出中找到窗口ID")
            return None
    except subprocess.CalledProcessError:
        print(f"错误：未找到标题为'{target_title}'的窗口")
        return None
    except Exception as e:
        print(f"获取窗口ID失败：{str(e)}")
        return None

def activate_window_by_xdotool(window_id):
    """使用xdotool激活指定ID的窗口（确保在顶层）"""
    if not window_id:
        return False
    
    try:
        # 激活窗口并等待操作完成
        subprocess.run(
            f'xdotool windowactivate --sync {window_id}',
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        # 额外延迟确保窗口完全显示（解决黑屏问题）
        time.sleep(0.8)
        print(f"窗口 {window_id} 已激活")
        return True
    except subprocess.CalledProcessError as e:
        print(f"激活窗口失败：{e.stderr}")
        return False
    except Exception as e:
        print(f"激活窗口出错：{str(e)}")
        return False

def deepin_screenshot_capture(window_id, save_path):
    """使用deepin-screenshot截取指定窗口"""
    if not window_id or not save_path:
        return False
    
    # 确保输出目录存在
    output_dir = os.path.dirname(save_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 构建完整命令（使用绝对路径避免-o参数失效）
        abs_save_path = os.path.abspath(save_path)
        cmd = (
            f'deepin-screenshot '
            f'-w {window_id} '  # 指定窗口ID
            f'-s '             # 静默模式（不显示编辑界面）
            f'-o "{abs_save_path}"'  # 输出路径（绝对路径）
        )
        
        print(f"执行截图命令：{cmd}")
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        pdb.set_trace()
        # 验证截图结果
        if os.path.exists(abs_save_path) and os.path.getsize(abs_save_path) > 0:
            print(f"截图成功，保存至：{abs_save_path}")
            return True
        else:
            print("截图失败：生成的文件为空或不存在")
            return False
    except subprocess.CalledProcessError as e:
        print(f"deepin-screenshot执行失败：{e.stderr}")
        return False
    except Exception as e:
        print(f"截图过程出错：{str(e)}")
        return False

def main():
    # 配置参数
    target_title = "deepin_xterm_test"  # xterm窗口标题（必须唯一）
    save_path = "screenshots/deepin_final_result.png"  # 截图保存路径
    
    # 1. 启动xterm窗口（标题需与target_title一致）
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
    
    # 2. 使用xwininfo获取窗口ID
    window_id = get_window_id_by_xwininfo(target_title)
    if not window_id:
        print("无法获取窗口ID，退出程序")
        return
    
    # 3. 使用xdotool激活窗口
    if not activate_window_by_xdotool(window_id):
        print("无法激活窗口，退出程序")
        return
    
    # 4. 使用deepin-screenshot截图
    deepin_screenshot_capture(window_id, save_path)

if __name__ == "__main__":
    main()
