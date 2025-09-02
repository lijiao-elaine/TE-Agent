import subprocess
import os
import sys
import time
from typing import Dict, List, Tuple, Optional, Any
import pdb

class SubprocessManager:
    def __init__(self):
        self.subprocesses = []  # 保存子流程对象，用于后续管理

    def create_bashrc_no_title(self):
        # 要写入的内容（与原Shell命令的输出完全一致）
        content = "PS1='\\u@\\h:\\w\\$ '"
        # 解析用户主目录（~ 转换为实际路径）
        bashrc_path = os.path.expanduser("~/.bashrc_no_title")
        
        try:
            # 写入文件（覆盖已有内容）
            with open(bashrc_path, "w") as f:
                f.write(content + "\n")  # 加换行符确保格式正确
            #print(f"成功创建文件：{bashrc_path}")
            return True
        except IOError as e:
            print(f"文件写入失败：{e}")
            return False

    def _get_terminal_command(self, exec_cmd: str, terminal_name: str, output_file: str, terminal_line_num: int, blocked_process:int) -> List[str]:
        """根据操作系统生成启动终端的命令（含输出重定向）"""
        # 构造可执行程序的命令（输出重定向到文件，同时终端显示）;不同终端的命令格式差异较大，需要针对性处理
        if sys.platform.startswith("win32"):
            # Windows：使用 cmd 终端，/k 表示执行后不关闭终端,输出同时写入文件和终端
            return [
                "cmd", "/k",
                f"{exec_cmd} > {output_file} 2>&1 & type {output_file} && tail -f {output_file}"
            ]
        elif sys.platform.startswith("linux"):
            # Linux：使用xterm，-T 设置终端标题；-e 执行命令，通过bash -c组合多个命令；最后添加bash保持终端不关闭
            os.environ["DISPLAY"] = ":0"
            self.create_bashrc_no_title()

            commands_1 = ( # ./main  ./unit_test 都 nok, main没起来，unit_test只重定向最后一个命令到日志文件
                'export TERM=xterm-256color; '  # 关键：强制终端类型为xterm，解析功能键
                'stty cooked; '  # 强制熟模式
                'echo \"当前指令执行目录：$(pwd)\"; '
                f"{exec_cmd} 2>&1 | tee -a {output_file};"
                'bash --rcfile ~/.bashrc_no_title --noprofile'
            )
            commands_2 = ( # ./main ok也可以重定向日志, ./unit_test nok, 不重定向日志文件了
                'export TERM=xterm-256color; '  # 关键：强制终端类型为xterm，解析功能键
                'stty cooked; '  # 强制熟模式
                'echo \"当前指令执行目录：$(pwd)\"; '
                f"script -q -c {exec_cmd} /dev/null 2>&1 | tee -a {output_file};"
                'bash --rcfile ~/.bashrc_no_title --noprofile'
            )
            commands_3 = ( # ./main ./unit_test 都 nok, main没起来，unit_test闪退
                'export TERM=xterm-256color; '  # 关键：强制终端类型为xterm，解析功能键
                'stty cooked; '  # 强制熟模式
                'echo \"当前指令执行目录：$(pwd)\"; '
                f"exec {exec_cmd} 2>&1 | tee -a {output_file};"
                'bash --rcfile ~/.bashrc_no_title --noprofile'
            )
            commands_4 = ( # ./main ./unit_test 都ok, main可以拉起，但不重定向日志；unit_test所有命令能重定向，但日志文件多了很多ECS等符号
                'export TERM=xterm-256color; '  # 关键：强制终端类型为xterm，解析功能键
                'stty cooked; '  # 强制熟模式
                'echo \"当前指令执行目录：$(pwd)\"; '
                f"script -q -c \"({exec_cmd})\" /dev/null 2>&1 | tee >(sed -r 's/\x1B\\[[0-9;]*[mK]//g' >> {output_file});"
                'bash --rcfile ~/.bashrc_no_title --noprofile'
            )
            commands_5 = (# ./main ok,可以拉起，但不重定向日志；./unit_test ok, 所有命令能重定向到日志，也没有ESC符号
                'export TERM=xterm-256color; '  # 强制终端类型
                'stty cooked; '  # 强制熟模式
                'shopt -s processsubstitution; '  # 确保进程替换（tee >(...)）生效（部分系统默认关闭）
                # 去掉多余转义，用单引号包裹字符串，避免双引号冲突
                'echo "当前指令执行目录：$(pwd)"; '
                # exec_cmd 若含特殊字符（如单引号），需提前处理：exec_cmd = exec_cmd.replace("'", "'\\''")
                f"script -q -c 'stdbuf -oL -eL {exec_cmd}' /dev/null 2>&1 | "  # 中层用单引号，避免与外层双引号冲突
                f"tee -a >(sed -r 's/\\x1B\\[[0-9;]*[mK]//g' >> {output_file}); "  # 过滤ANSI符号
                'read -r;'
                'bash --rcfile ~/.bashrc_no_title --noprofile'  # -i：强制交互模式，防止闪退
            )

            if blocked_process == 1:
                terminal_commands = ( # ./main ok,即使是复合语句也可以重定向日志, ./unit_test nok, 不重定向日志文件了
                    'export TERM=xterm-256color; '  # 关键：强制终端类型为xterm，解析功能键
                    'stty cooked; '  # 强制熟模式
                    'echo \"当前指令执行目录：$(pwd)\"; '
                    f"script -q -c \"{exec_cmd}\" /dev/null 2>&1 | tee -a {output_file};"
                    'bash --rcfile ~/.bashrc_no_title --noprofile'
                )
            else:
                terminal_commands = (# ./main nok，没起来； ./unit_test ok, 所有命令都重定向到日志文件
                    'export TERM=xterm-256color; '  # 关键：强制终端类型为xterm，解析功能键
                    'stty cooked; '  # 强制熟模式
                    'echo \"当前指令执行目录：$(pwd)\"; '
                    f"({exec_cmd}) 2>&1 | tee -a {output_file};"
                    'bash --rcfile ~/.bashrc_no_title --noprofile'
                )
            return [ # xterm终端的declare -x打印是bash -c 带来的，改成bash -c '{terminal_commands}' 2>&1 | grep -v '^declare -x'即可
                "xterm",
                "-T", f"{terminal_name}",
                "-geometry", f"120x{terminal_line_num}", # 终端宽度240字符、高度80行字符
                "-e", f"bash -c '{terminal_commands}'" 
            ]

        elif sys.platform.startswith("darwin"):
            # macOS：使用 Terminal 应用，通过 bash 执行命令
            return [
                "open", "-a", "Terminal",
                "bash", "-c",
                f"{exec_cmd} 2>&1 | tee {output_file}; exec bash"
            ]
        else:
            raise NotImplementedError(f"不支持的操作系统：{sys.platform}")

    def _get_subprocess_log_file(self, processId: str) -> str:
        for proc, output_file in self.subprocesses:
            if proc.pid == processId:
                if not os.path.exists(output_file):
                    #print(f"子进程的实时输出日志不存在：{output_file}")
                    return ""
                else:
                    #print(f"返回子进程的实时输出日志文件路径：{output_file}")
                    return output_file
                    
    def create_log_file(self,log_path, log_file):
        # 计算log_file的绝对路径
        base_dir = log_path if log_path is not None else os.makedirs(log_path, exist_ok=True)
        output_abs_path = os.path.abspath(os.path.join(base_dir, log_file))
        if os.path.isfile(output_abs_path):
            os.remove(output_abs_path)
        # 新建文件（使用with语句会自动创建并关闭文件）
        with open(output_abs_path, 'w') as f:
            pass  # 不写入内容，仅创建空文件
        return output_abs_path

    def start_subprocess(self, 
        exec_cmd: str,  #执行命令（如 ./main 或 main.exe）
        terminal_name: str,  # 拉起的xterm终端的名字
        blocked_process:int = 0, # 在xterm终端中执行的程序是否是持续运行不退出，即阻塞式进程
        cwd: Optional[str] = None,  # 子进程工作目录
        log_path: str = "logs",  # 测试步骤日志的输出目录
        log_file: str = "output_step.log",  # 测试步骤日志的文件名
        terminal_line_num: int = 20, # 拉起的xterm终端的高度，即多少行字符
        timeout: int = 30,
        sleep_time: int = 1 # 运行后立马退出的程序，留出时间给它执行
        ) -> Tuple[bool, str, str, int]:
        """启动一个子流程，在独立终端运行可执行程序，并捕获输出
        :return: 子进程的Popen实例
        """

        try:
            # 步骤1：验证待执行指令的目录是否存在
            if not os.path.isdir(cwd):
                raise FileNotFoundError(f"要切换后用于执行指令的目录不存在：{cwd}")

            output_abs_path = self.create_log_file(log_path, log_file)

            # 生成终端命令
            terminal_cmd = self._get_terminal_command(exec_cmd, terminal_name, output_abs_path, terminal_line_num, blocked_process)
            #print(f"子进程待执行命令：{terminal_cmd}")

            proc = subprocess.Popen(# 启动阻塞式子进程
                terminal_cmd,
                cwd=cwd,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            time.sleep(sleep_time)  # 有时如果terminal_cmd中拉起的程序是非阻塞式的，即运行后立马退出的，则需要留出时间给它执行
            #proc.wait()  # 等待进程结束

            # 保存子流程对象，便于后续管理
            self.subprocesses.append((proc, output_abs_path))
            #print(f"子进程保存的对象：{proc}")
            
            # 返回Popen实例
            #return proc
            return (True, proc.pid, "", proc.returncode)
        except FileNotFoundError as e:
            err = f"待执行的命令未找到: {str(e)}"
            print(f"命令未找到：{e}")  # 输出类似：[Errno 2] No such file or directory: '不存在的命令'
            return (False, "", err, -1)
        except PermissionError as e:
            err = f"可执行程序权限不足: {str(e)}"
            print(f"可执行程序权限不足：{e}")  # 输出类似：[Errno 13] Permission denied: 'no_permission_cmd'
            return (False, "", err, -2)

    def capture_output(self, processId: str) -> str:
        """读取子进程输出文件的内容（实时捕获输出）"""
        for proc, output_file in self.subprocesses:
            if proc.pid == processId:
                if not os.path.exists(output_file):
                    print(f"子进程的实时输出日志不存在：{output_file}")
                    return ""
                with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()

    def close_all_xterm(self):
        """关闭所有 xterm 终端"""
        try:
            # 查找所有 xterm 进程的 PID（排除 grep 自身）
            result = subprocess.run(
                "ps -ef | grep 'xterm' | grep -v 'grep' | awk '{print $2}'",
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            pids = result.stdout.strip().split()
            
            if not pids:
                print("没有正在运行的 xterm 终端")
                return
            
            # 逐个终止进程
            for pid in pids:
                subprocess.run(f"kill {pid}", shell=True, check=True)
                #print(f"已关闭 xterm 进程（PID：{pid}）")
        
        except subprocess.CalledProcessError as e:
            print(f"关闭 xterm 终端操作失败：{e.stderr}")

    def stop_all_subprocesses(self) -> None:
        """终止所有子进程（包括终端）"""
        for proc, output_file in self.subprocesses:
            if proc.poll() is None:  # 若子进程仍在运行
                proc.terminate()
                print(f"已终止子进程：{proc.pid}")
            # 删除输出文件
            #if os.path.exists(output_file):
            #    os.remove(output_file)
        # 再关闭所有 xterm 终端
        self.close_all_xterm()

  
