import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Tuple, List
import math
from utils.command_executor import CommandExecutor
import pdb

class ScreenshotHandler:
    """处理测试过程中的截图捕获与保存"""
    
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

    @staticmethod
    def ensure_window_focus(window_id):
        """增强版窗口聚焦：组合多种方法确保窗口激活"""
        # 1. 先尝试基础激活（windowactivate会将窗口前置）
        try:
            # windowactivate：激活并前置窗口（比windowfocus更优先）
            result = subprocess.run(
                f'xdotool windowactivate {window_id}',
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            time.sleep(0.5)  # 等待窗口前置
            print(f"窗口xdotool windowactivate 前置成功，window_id：{window_id}，返回码：{result.returncode}, stdout：{result.stdout}, stderr:{result.stderr}")
        except subprocess.CalledProcessError as e:
            print(f"windowactivate 失败：{e.stderr}")
            return False

        # 2. 强制设置焦点（解决激活但未获焦的情况）
        try:
            result = subprocess.run(
                f'xdotool windowfocus {window_id}',
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            time.sleep(0.5)  # 等待焦点生效
            print(f"窗口xdotool windowfocus 聚焦成功，window_id：{window_id}，返回码：{result.returncode}, stdout：{result.stdout}, stderr:{result.stderr}")
        except subprocess.CalledProcessError as e:
            print(f"windowfocus失败：{e.stderr}")
            return False

        # 3. 发送WM_COMMAND请求（针对顽固窗口，强制唤醒）
        try:
            # 使用wmctrl发送窗口激活命令（依赖wmctrl工具，需先安装）
            result = subprocess.run(
                f'wmctrl -i -a {window_id}',  # -i：指定window_id为数字格式；-a：激活窗口
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            time.sleep(0.5)
            print(f"窗口wmctrl激活成功，window_id：{window_id}，返回码：{result.returncode}, stdout：{result.stdout}, stderr:{result.stderr}")
        except subprocess.CalledProcessError as e:
            print(f"wmctrl激活窗口失败（非致命，继续）：{e.stderr}")
        except FileNotFoundError:
            print("未安装wmctrl，跳过此步骤（可选安装：sudo apt install wmctrl）")

        # 4. 验证焦点是否真正生效
        try:
            current_focus = subprocess.run(
                'xdotool getwindowfocus',
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            ).stdout.strip()  # 获取当前焦点窗口ID
            
            # 窗口ID可能以十六进制（0x开头）或十进制表示，统一转为十六进制对比
            if hex(int(window_id, 16)) == hex(int(current_focus, 16)):
                print(f"焦点验证成功，当前焦点窗口：{window_id}")
                return True
            else:
                print(f"焦点验证失败！当前焦点窗口：{current_focus}，目标窗口：{window_id}")
                return False
        except subprocess.CalledProcessError as e:
            print(f"获取当前焦点窗口失败：{e.stderr}")
            return False

    def force_window_above_and_focus(window_id):
        """
        强制窗口置顶并获取焦点，绕过窗口管理器的策略限制
        window_id: 窗口ID（十六进制，如"0x80000d"）
        """
        # 1. 确保环境变量正确
        env = {
            "DISPLAY": os.environ.get("DISPLAY", ":0"),  # 当前显示
            "XAUTHORITY": os.path.expanduser("~/.Xauthority")  # X11权限文件
        }

        try:
            # 2. 清除窗口可能的"隐藏/最小化"状态
            subprocess.run(
                f"wmctrl -i -r {window_id} -b remove,hidden,minimized",
                shell=True,
                check=True,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT
            )

            # 获取窗口位置（左上角坐标）
            pos_result = subprocess.run(
                f"xwininfo -id {window_id} | grep 'Absolute upper-left' | awk '{{print $4, $6}}'",
                shell=True,
                capture_output=True,
                text=True
            ).stdout.strip()
            x, y = map(int, pos_result.split())
            
            # 移动鼠标到窗口标题栏（y+20像素位置）并点击
            subprocess.run(
                f"xdotool mousemove {x+50} {y+20} click 1",  # 点击标题栏中间位置
                shell=True,
                check=True
            )
            time.sleep(0.5)

            # 3. 强制设置窗口为"永远置顶"（_NET_WM_STATE_ABOVE属性）
            # 先清除可能的冲突属性，再添加置顶属性
            subprocess.run(
                f"xprop -id {window_id} -remove _NET_WM_STATE; "
                f"xprop -id {window_id} -f _NET_WM_STATE 32a -set _NET_WM_STATE _NET_WM_STATE_ABOVE",
                shell=True,
                check=True,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT
            )

            # 4. 组合激活命令（确保焦点锁定）
            subprocess.run(
                f"xdotool windowactivate {window_id}; "  # 激活窗口
                f"xdotool windowfocus {window_id}; "     # 锁定焦点
                f"xdotool windowraise {window_id}",      # 物理举起窗口
                shell=True,
                check=True,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT
            )

            # 5. 验证窗口是否真的在最上层（通过xwininfo检查层级）
            xwininfo_result = subprocess.run(
                f"xwininfo -id {window_id} | grep 'Absolute upper-left Y'",
                shell=True,
                check=True,
                env=env,
                capture_output=True,
                text=True
            )
            # 若能获取到位置信息，说明窗口已显示在屏幕上
            #print(f"窗口{window_id}位置信息：{xwininfo_result.stdout.strip()}")

            # 6. 最终焦点验证（允许1秒延迟，应对WM的异步处理）
            time.sleep(1)
            current_focus = subprocess.run(
                "xdotool getwindowfocus",
                shell=True,
                check=True,
                env=env,
                capture_output=True,
                text=True
            ).stdout.strip()

            # 统一ID格式（十六进制对比）
            if hex(int(current_focus)) == hex(int(window_id, 16)):
                #print(f"窗口{window_id}已成功置顶并获取焦点")
                return True
            else:
                print(f"焦点验证失败：当前焦点窗口ID={current_focus}，目标={window_id}")
                return False

        except subprocess.CalledProcessError as e:
            print(f"强制置顶命令执行失败：{e.stderr}")
            return False
        except Exception as e:
            print(f"强制置顶异常：{str(e)}")
            return False

    @staticmethod
    def capture_terminal_region(window_id, output_path):
        """捕获终端截图（X11原生工具链）"""
        temp_xwd = "logs/xterm_target_temp.xwd"
        temp_pnm = "logs/xterm_target_temp.pnm"
        
        # 前置检查：确保目标窗口存在且可见
        try:
            # 检查窗口是否处于映射状态
            subprocess.run(
                f'xwininfo -id {window_id}',  # xwininfo可查询窗口状态
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        except subprocess.CalledProcessError as e:
            print(f"目标窗口不可见或不存在：{e.stderr}")
            return False

        try:
            # xwd截图→xwdtopnm转PNM→pnmtopng转PNG
            result = subprocess.run(
                f"xwd -id {window_id} -out {temp_xwd}",
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True  # 输出转为字符串，方便调试
            )
            #print(f"xwd截图完成, 返回码: {result.returncode}, stderr:{result.stderr}")
        except subprocess.CalledProcessError as e:
            print(f"xwd截图失败, 返回码: {e.returncode}, stderr:{e.stderr}")
            # 清理临时文件
            for f in [temp_xwd, temp_pnm]:
                if os.path.exists(f):
                    os.remove(f)
            return False
        except Exception as e:
            print(f"xwd截图异常: {str(e)}")
            for f in [temp_xwd, temp_pnm]:
                if os.path.exists(f):
                    os.remove(f)
            return False  

        try:
            result = subprocess.run(
                f"xwdtopnm {temp_xwd} > {temp_pnm}",
                shell=True,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True
            )
            #print(f"xwdtopnm完成, 返回码: {result.returncode}")
        except subprocess.CalledProcessError as e:
            print(f"xwdtopnm失败, stderr:{e.stderr}")
            for f in [temp_xwd, temp_pnm]:
                if os.path.exists(f):
                    os.remove(f)
            return False
        except Exception as e:
            print(f"xwdtopnm异常: {str(e)}")
            for f in [temp_xwd, temp_pnm]:
                if os.path.exists(f):
                    os.remove(f)
            return False  
                
        try:
            result = subprocess.run(
                f"pnmtopng {temp_pnm} > {output_path}",
                shell=True,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True
            )
            # 清理临时文件
            for f in [temp_xwd, temp_pnm]:
                if os.path.exists(f):
                    os.remove(f)
            #print(f"截图成功，保存至: {output_path}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"pnmtopng失败, stderr:{e.stderr}")
            for f in [temp_xwd, temp_pnm]:
                if os.path.exists(f):
                    os.remove(f)
            return False
        except Exception as e:
            print(f"pnmtopng异常: {str(e)}")
            for f in [temp_xwd, temp_pnm]:
                if os.path.exists(f):
                    os.remove(f)
            return False

    def scroll_terminal_to_line(line_number, terminal_line_num):
        """使用xdotool发送Shift+Page_Up翻页，按line_number÷20向上取整计算翻页次数（窗口已聚焦）"""
        try:
            # 1. 边界处理：目标行≤0时无需滚动
            lines_to_roll = line_number - terminal_line_num
            if lines_to_roll < 0:
                #print("目标行号无需滚动")
                return True
            
            # 2. 核心计算：line_number除以20向上取整得到翻页次数, 公式：翻页次数 = ceil(目标行号 / 20)，单次翻页滚动20行
            page_size = 20  # 每页行数（固定为20），因为xterm终端的 Shift+PageUp组合键翻页每次仅向上滚动20行字符
            page_count = math.ceil(lines_to_roll / page_size)  # 向上取整计算翻页次数
            if page_count == 0:
                page_count = 1
            
            #print(f"目标行号：{line_number}，每页滚动{page_size}行，需向上翻页次数：{page_count}")
            
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

    def find_target_line_in_output(log_file, target_text):
        """在日志中查找目标文本，返回【倒数行号】、正序行号、目标行内容（行号均从1开始）"""
        try:
            with open(log_file, 'r', errors='ignore') as f:
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
    def kill_xterm_by_window_id(window_id):
        """
        通过窗口ID关闭对应的xterm终端
        :param window_id: 窗口ID（十六进制，如"0x80000d"）
        :return: 成功返回True，失败返回False
        """
        try:
            # 方法1：向窗口发送关闭信号（推荐，模拟点击关闭按钮）
            # 使用xdotool向目标窗口发送WM_DELETE_WINDOW消息（标准关闭信号）
            result = subprocess.run(
                f"xdotool windowclose {window_id}",
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            #print(f"已向窗口{window_id}发送关闭信号，subprocess.run执行关闭xterm窗口的返回码：{result.returncode}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"方法1关闭失败，尝试备用方法：{e.stderr}")
            
            try:
                # 方法2：通过窗口ID查找进程PID，再kill进程（强制关闭）
                # 1. 获取窗口对应的进程PID
                pid_result = subprocess.run(
                    f"xdotool getwindowpid {window_id}",
                    shell=True,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                pid = pid_result.stdout.strip()
                
                # 2. 终止进程
                subprocess.run(
                    f"kill {pid}",
                    shell=True,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                #print(f"已强制终止窗口{window_id}对应的进程（PID：{pid}）")
                return True
                
            except subprocess.CalledProcessError as e2:
                print(f"方法2强制关闭失败：{e2.stderr}")
                return False
        except Exception as e:
            print(f"关闭窗口异常：{str(e)}")
            return False
            
    @staticmethod
    def capture_step_screenshot_terminal(screenshot_name: str, 
        terminal_name:str, 
        terminal_line_num:int,
        log_file:str, 
        expected_keywords:List[str], 
        screenshot_dir: str = "reports/screenshots") -> List[str]:
        """
        捕获当前步骤的截图（适配WSL环境）
        :param screenshot_name: 测试结果截图名字的前缀（如XXX_TEST_001_screenshot_step_1）
        :param screenshot_dir: 截图保存目录
        :return: 截图文件的绝对路径
        """
        print("="*10+f"准备截图"+"="*10)
        # 创建输出目录
        Path(screenshot_dir).mkdir(parents=True, exist_ok=True)
        screenshot_paths = []

        # 7. 获取目标终端窗口ID
        window_ids = ScreenshotHandler.get_xterm_window_id(terminal_name)
        if not window_ids:
            print("未找到目标终端窗口")
            return
        # 取第一个匹配的窗口
        window_id = window_ids.split()[0]
        #print(f"找到的目标终端窗口ID：{window_ids}，匹配的第一个终端窗口ID：{window_id}, 终端名字：{terminal_name}")

        all_empty = all(element == '' for element in expected_keywords)
        if not expected_keywords or all_empty:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.abspath(os.path.join(screenshot_dir, f"{screenshot_name}_{timestamp}.png"))
            # 10. 截图并保存
            if ScreenshotHandler.capture_terminal_region(window_id, screenshot_path):
                #print(f"截图成功，保存路径：{screenshot_path}")
                screenshot_paths.append(screenshot_path)
            else:
                print("expected_keywords为空时截图失败")
        else:
            # 8. 定位目标文本所在行
            for keyword in expected_keywords:
                target_reverse_line, target_line, target_content = ScreenshotHandler.find_target_line_in_output(log_file, keyword)
                if not target_line:
                    #print(f"未在终端输出中找到目标文本：'{keyword}'")
                    continue
                #print(f"目标文本 '{keyword}' 位置：倒数第 {target_reverse_line} 行")
            
                # 9. 聚焦窗口并滚动到目标行 force_window_above_and_focus ensure_window_focus
                #print("开始执行窗口聚焦操作") 
                if not ScreenshotHandler.force_window_above_and_focus(window_id):
                    print("窗口聚焦失败，无法滚动")
                else:
                    #print("开始执行滚动操作...")
                    scroll_success = ScreenshotHandler.scroll_terminal_to_line(target_reverse_line, terminal_line_num) #从最底下往上滚动到最后一次出现目标文本
                    if not scroll_success:
                        #print("滚动操作完成，目标行已显示在终端中")
                        #else:
                        print("滚动操作失败，将截图当前视图")

                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                screenshot_path = os.path.abspath(os.path.join(screenshot_dir, f"{screenshot_name}_{timestamp}.png"))
                
                # 10. 截图并保存
                if ScreenshotHandler.capture_terminal_region(window_id, screenshot_path):
                    #print(f"截图成功，保存路径：{screenshot_path}")
                    screenshot_paths.append(screenshot_path)
                else:
                    print("expected_keywords非空时截图失败")

                #滚动到终端末尾
                subprocess.run(
                    f'xdotool key Shift+End',
                    shell=True,
                    check=True
                )
                subprocess.run(
                    f'xdotool key BackSpace',
                    shell=True,
                    check=True
                )
                

        # 11. 关闭xterm终端
        if not ScreenshotHandler.kill_xterm_by_window_id(window_id):
            print(f"关闭终端：{terminal_name}（窗口ID：{window_id}）失败")
                

        return screenshot_paths

    @staticmethod
    def capture_step_screenshot_logfile(screenshot_name: str, terminal_name:str, 
        remote_os: str,remote_ip: str, remote_user:str, remote_passwd:str,remote_hdc_port: str,
        log_file:str, cat_output_file:str, expected_keywords:List[str], screenshot_dir: str = "reports/screenshots") -> Tuple[bool, List[str]]:
        """
        捕获当前步骤的截图（适配WSL环境）
        :param screenshot_name: 测试结果截图名字的前缀（如XXX_TEST_001_screenshot_step_1）
        :param screenshot_dir: 截图保存目录
        :return: 截图文件的绝对路径
        """
        print("="*10+f"准备截图"+"="*10)
        # 1. 创建输出目录
        Path(screenshot_dir).mkdir(parents=True, exist_ok=True)
        screenshot_paths = []

        # 2. 获取目标终端窗口ID，用于将该步骤待检查的日志截图后，kill该步骤command执行时的xterm终端，避免影响后续步骤的xterm终端截图
        window_ids = ScreenshotHandler.get_xterm_window_id(terminal_name)
        if not window_ids:
            print(f"未找到测试步骤执行的终端窗口：{terminal_name}")
            return (False, [])
        # 取第一个匹配的窗口
        window_id = window_ids.split()[0]

        # 3. 关闭该步骤command执行时的xterm终端
        if not ScreenshotHandler.kill_xterm_by_window_id(window_id):
            print(f"关闭测试步骤执行的终端：{terminal_name}（窗口ID：{window_id}）失败")
        else:
            print(f"关闭测试步骤执行的终端：{terminal_name}（窗口ID：{window_id}）成功")

        all_empty = all(element == '' for element in expected_keywords)
        if not expected_keywords or all_empty:
            print(f"对测试步骤执行产生的日志做检查时，发现expected_keywords为空：{expected_keywords}")
            return (False, [])
        else:
            terminal_name_logfile = f"view_logfile"
            for keyword in expected_keywords:
                # 4. 拉起xterm终端，用于cat该步骤待检查的日志文件后grep预期输出结果，然后截图
                core_cmd = f"cat {log_file} | grep -F -- '{keyword}'"
                if remote_ip == "127.0.0.1":
                    terminal_commands = (# ./main nok，没起来； ./unit_test ok, 所有命令都重定向到日志文件
                        'export TERM=xterm-256color; '  # 关键：强制终端类型为xterm，解析功能键
                        'stty cooked; '  # 强制熟模式
                        'short_pwd=$(echo "$PWD" | sed "s|^$HOME|~|"); '
                        'echo -n "$USER@$HOSTNAME:$short_pwd$ "; '  # 打印命令提示符（不换行）
                        f'echo "{core_cmd}"; '  # 打印命令
                        f"{core_cmd}; "  # 执行命令
                        'bash --rcfile ~/.bashrc_no_title --noprofile'
                    )
                    command = ["xterm", "-T", terminal_name_logfile, "-geometry", f"120x40", "-e", f"bash", "-c", terminal_commands]
                else:
                    escaped_exec_cmd = CommandExecutor.escape_special_chars(core_cmd)
                    if remote_os != "HarmonyOS":
                        #print("ScreenshotHandler.capture_step_screenshot_logfile: 待验证远程非鸿蒙系统下，对被测系统日志截图的逻辑")
                        terminal_commands = ( 
                            'export TERM=xterm-256color; '
                            f'expect -c "set timeout 30; '
                            f'spawn ssh {remote_user}@{remote_ip}; '
                            'expect { \n'
                            '   \\"Are you sure you want to continue connecting (yes/no)?\\" { send \\"yes\\r\\"; exp_continue; } \n'
                            '   -re {[Pp]assword:?\\s*|口令:?\\s*} { send \\"' + remote_passwd + '\\r\\"; exp_continue; } \n'
                            '   \\"Permission denied\\" { exit 1; } \n'
                            '   -re {[#$]\\s*} { send \\" ' + escaped_exec_cmd + ' 2>&1 | tee -a -;\\r\\"; interact; } \n'
                            '}; '
                            'interact" 2>&1 | tee -a ' + cat_output_file + '; '
                            'bash --rcfile ~/.bashrc_no_title --noprofile'
                        )
                    else:
                        print("ScreenshotHandler.capture_step_screenshot_logfile: 待验证远程鸿蒙系统下，对被测系统日志截图的逻辑,cat结果需重定向到cat_output_file")
                        terminal_commands = (
                            'export TERM=xterm-256color; '
                            'stty cooked; '
                            f'echo "=== 鸿蒙设备远程执行 ===" ; '
                            f'echo "设备IP: {remote_ip} | 执行命令对被测系统日志截图"; '
                            f'if ! hdc list targets | grep -q "{remote_ip}"; then '
                            f'  echo "错误：未找到鸿蒙设备 {remote_ip}，请检查hdc连接" ; '
                            '  bash --rcfile ~/.bashrc_no_title --noprofile; '
                            'else '
                            '  short_pwd=$(echo "$PWD" | sed "s|^$HOME|~|"); '
                            '  echo -n "$USER@$HOSTNAME:$short_pwd$ "; '
                            f'  echo "{core_cmd}"; '  # 打印命令
                            f'  hdc -t {remote_ip}:{remote_hdc_port} shell "({core_cmd}) 2>&1" ;'# 执行命令：子shell包裹
                            f'  echo "命令执行完成，终端保持打开状态..." ; '
                            '  bash --rcfile ~/.bashrc_no_title --noprofile; ' # 保活
                            'fi'
                        )
                    command = ["xterm", "-T", terminal_name_logfile, "-geometry", f"120x40", "-e", f"bash -c '{terminal_commands}'"]
                proc = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    shell=False
                    )
                time.sleep(3)

                # 对查看被测系统日志的xterm终端截图
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                screenshot_path = os.path.abspath(os.path.join(screenshot_dir, f"{screenshot_name}_{timestamp}.png"))
                logfile_window_ids = ScreenshotHandler.get_xterm_window_id(terminal_name_logfile)
                if not logfile_window_ids:
                    print(f"未找到查看被测系统日志的、名为{terminal_name_logfile}的终端窗口")
                    #continue
                    return (False, screenshot_paths)
                logfile_window_id = logfile_window_ids.split()[0] # 取第一个匹配的窗口
                
                # 10. 截图并保存
                if ScreenshotHandler.capture_terminal_region(logfile_window_id, screenshot_path):
                    screenshot_paths.append(screenshot_path)
                else:
                    print("expected_keywords非空时对被测系统日志截图失败")
                    return (False, screenshot_paths)

                # 关闭查看被测系统日志的xterm终端
                if not ScreenshotHandler.kill_xterm_by_window_id(logfile_window_id):
                    print(f"关闭终端：{terminal_name_logfile}（窗口ID：{logfile_window_id}）失败")

            return (True, screenshot_paths)

   