import os
import subprocess
import time
import re
from datetime import datetime
import tempfile
import math

def install_dependency():
    """检查并安装必要依赖（xautomation提供xte，x11-utils提供xdotool备用）"""
    dependencies = {
        "xte": "xautomation",
        "xdotool": "xdotool"
    }
    for cmd, pkg in dependencies.items():
        try:
            subprocess.run(
                f'which {cmd}',
                shell=True,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except:
            print(f"检测到缺少{cmd}工具，正在安装{pkg}...")
            try:
                subprocess.run(
                    f'sudo apt-get update && sudo apt-get install -y {pkg}',
                    shell=True,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print(f"{pkg}安装成功")
            except:
                print(f"安装{pkg}失败，请手动执行：sudo apt install -y {pkg}")
                return False
    return True

def get_xterm_window_id(title):
    """根据标题获取xterm窗口ID"""
    try:
        output = subprocess.check_output(
            f'xwininfo -root -tree | grep "{title}" | grep -o "0x[0-9a-fA-F]\+"',
            shell=True,
            text=True
        )
        return output.strip()
    except Exception as e:
        print(f"获取窗口ID失败：{e}")
        return None

def capture_terminal_region(window_id, output_path):
    """捕获终端截图（X11原生工具链）"""
    temp_xwd = "/tmp/xterm_target_temp.xwd"
    temp_pnm = "/tmp/xterm_target_temp.pnm"
    
    try:
        # xwd截图→xwdtopnm转PNM→pnmtopng转PNG
        subprocess.run(
            f"xwd -id {window_id} -out {temp_xwd}",
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        subprocess.run(
            f"xwdtopnm {temp_xwd} > {temp_pnm}",
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        subprocess.run(
            f"pnmtopng {temp_pnm} > {output_path}",
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # 清理临时文件
        os.remove(temp_xwd)
        os.remove(temp_pnm)
        return True
    except Exception as e:
        print(f"截图失败：{e}")
        # 出错时清理临时文件
        if os.path.exists(temp_xwd):
            os.remove(temp_xwd)
        if os.path.exists(temp_pnm):
            os.remove(temp_pnm)
        return False

def ensure_window_focus(window_id):
    """确保终端窗口聚焦（用xdotool激活，避免xte语法问题）"""
    try:
        # 先用xdotool激活并聚焦窗口（兼容性更好）
        subprocess.run(
            f'xdotool windowactivate {window_id} && xdotool windowfocus {window_id}',
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        time.sleep(1)  # 等待窗口激活
        
        # 发送回车初始化bash环境（确保功能键可响应）
        subprocess.run(
            f'xdotool key Return',  # xte直接发送按键，无需指定窗口（已聚焦）
            shell=True,
            check=True
        )
        time.sleep(0.5)
        return True
    except subprocess.CalledProcessError as e:
        print(f"窗口聚焦失败，错误：{e.stderr}")
        return False
    except Exception as e:
        print(f"窗口聚焦异常：{e}")
        return False

def scroll_terminal_to_line(line_number):
    """使用xdotool发送Shift+Page_Up翻页，按line_number÷20向上取整计算翻页次数（窗口已聚焦）"""
    try:
        # 1. 边界处理：目标行≤0时无需滚动
        if line_number < 20:
            print("目标行号无需滚动")
            return True
        
        # 2. 核心计算：line_number除以20向上取整得到翻页次数, 公式：翻页次数 = ceil(目标行号 / 20)，单次翻页滚动20行
        page_size = 20  # 每页行数（固定为20），因为xterm终端的 Shift+PageUp组合键翻页每次仅向上滚动20行字符
        page_count = math.ceil(line_number / page_size)  # 向上取整计算翻页次数
        
        print(f"目标行号：{line_number}，每页滚动{page_size}行，需向上翻页次数：{page_count}")
        
        # 3. 执行翻页操作（发送Shift+Page_Up，每次翻页间隔延长至0.5秒，确保终端响应）
        for page in range(page_count):
            subprocess.run(
                f'xdotool key Shift+Page_Up',
                shell=True,
                check=True
            )
            # 翻页间隔：第1页后可适当缩短（前1页需等终端加载，后续可加快）
            sleep_time = 0.5 if page == 0 else 0.3
            time.sleep(sleep_time)

        time.sleep(1)  # 等待所有滚动操作完成
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"滚动命令执行失败，错误：{e.stderr}")
        return False
    except Exception as e:
        print(f"滚动异常：{e}")
        return False

def find_target_line_in_output(log_path, target_text):
    """在日志中查找目标文本，返回【倒数行号】、正序行号、目标行内容（行号均从1开始）"""
    try:
        with open(log_path, 'r', errors='ignore') as f:
            lines = f.readlines()  # 读取所有行，按顺序存储
        
        total_lines = len(lines)  # 计算文件总行数
        if total_lines == 0:
            print("日志文件为空，无行可查找")
            return None, None, None  # 倒数行号、正序行号、内容
        
        # 遍历所有行，查找包含目标文本的行（优先匹配最后一次出现的目标文本）
        target_positions = []  # 存储所有包含目标文本的行信息（正序行号、内容）
        for line_idx, line_content in enumerate(lines):
            if target_text in line_content:
                positive_line = line_idx + 1  # 正序行号（从1开始）
                target_positions.append((positive_line, line_content.strip()))
        
        if not target_positions:
            print(f"未在日志中找到目标文本：'{target_text}'")
            return None, None, None
        
        # 优先返回【最后一次出现】的目标文本（更符合“找最近目标”的实际需求）
        last_positive_line, last_line_content = target_positions[-1]

        # 计算倒数行号：总行数 - 正序行号 + 1（例如总行10，正序9 → 倒数2）
        reverse_line = total_lines - last_positive_line + 1
        
        # 返回结果：（倒数行号，正序行号，目标行内容）
        return reverse_line, last_positive_line, last_line_content
    
    except Exception as e:
        print(f"查找目标文本失败：{e}")
        return None, None, None  # 异常时返回空值

def main():
    # 1. 检查依赖（xte和xdotool）
    if not install_dependency():
        return
    
    # 2. 基础配置
    xterm_title = "xwd_native_test"
    target_text = "CST 2025"
    start_time = datetime.now()
    print("="*60)
    print("启动终端前时间：", start_time.strftime("%Y-%m-%d %H:%M:%S.%f"))
    
    os.environ["DISPLAY"] = ":0"
    # 3. 创建临时日志文件（记录终端输出）
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.log') as log_file:
        log_path = log_file.name
    print(f"终端输出日志路径：{log_path}")
    
    # 4. 定义终端执行命令（显式设置TERM确保功能键正常）
    terminal_commands = (
        'export TERM=xterm-256color; '  # 关键：强制终端类型为xterm，解析功能键
        'stty cooked; '  # 强制熟模式
        'ls -lrt;date;pwd; '# 输出含CST 2025的时间
        'ls -lrt;ls -lrt;ls -lrt;ls -lrt;ls -lrt; '
        'echo "xterm已初始化功能键：Shift+Page_Up=向上翻页，Shift+Page_Down=向下翻页"'  # 调试提示
    )
    
    # 5. 启动xterm（同时输出到终端和日志）
    command = (
        f'xterm -T "{xterm_title}" -geometry 120x40 ' # 终端宽度120字符、高度40行字符
        f'-e "bash -c \'{terminal_commands}\' 2>&1 | tee -a {log_path}; '
        f'bash --rcfile ~/.bashrc_no_title --noprofile" &'
    )
    print(f"启动终端命令：{command}")
    subprocess.Popen(command, shell=True, executable='/bin/bash')
    time.sleep(2)  # 延长等待，确保bash完全加载功能键映射
    
    # 6. 验证日志是否有效
    if os.path.getsize(log_path) == 0:
        print("警告：日志文件为空，终端输出未捕获")
        #os.remove(log_path)
        return
    print(f"日志文件大小：{os.path.getsize(log_path)} 字节（捕获成功）")
    
    # 7. 获取目标终端窗口ID
    window_ids = get_xterm_window_id(xterm_title)
    if not window_ids:
        print("未找到目标终端窗口")
        #os.remove(log_path)
        return
    
    # 取第一个匹配的窗口
    window_id = window_ids.split()[0]
    print(f"找到的目标终端窗口ID：{window_ids}，匹配的第一个终端窗口ID：{window_id}")
    
    # 8. 定位目标文本所在行
    target_reverse_line, target_line, target_content = find_target_line_in_output(log_path, target_text)
    if not target_line:
        print(f"未在终端输出中找到目标文本：'{target_text}'")
        #os.remove(log_path)
        return
    print(f"目标文本 '{target_text}' 位置：倒数第 {target_reverse_line} 行，内容：{target_content}")
    
    # 9. 聚焦窗口并滚动到目标行
    print("="*60)
    print("开始执行滚动操作...")
    if not ensure_window_focus(window_id):
        print("窗口聚焦失败，无法滚动")
    else:
        scroll_success = scroll_terminal_to_line(target_reverse_line) #从最底下往上滚动到最后一次出现目标文本
        if scroll_success:
            print("滚动操作完成，目标行已显示在终端中")
        else:
            print("滚动操作失败，将截图当前视图")
    
    # 10. 截图并保存
    output_dir = "screenshots"
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"xterm_target_{timestamp}.png")
    
    if capture_terminal_region(window_id, output_path):
        print(f"截图成功，保存路径：{os.path.abspath(output_path)}")
    else:
        print("截图失败")
    
    # 11. 清理临时文件
    #os.remove(log_path)
    
    # 12. 输出最终结果
    end_time = datetime.now()
    print("="*60)
    print("处理完成时间：", end_time.strftime("%Y-%m-%d %H:%M:%S.%f"))
    print(f"总耗时：{(end_time - start_time).total_seconds():.2f} 秒")
    print("程序运行状态：" + ("成功（找到目标文本并滚动）" if scroll_success else "部分成功（未滚动但捕获输出）"))

if __name__ == "__main__":
    main()