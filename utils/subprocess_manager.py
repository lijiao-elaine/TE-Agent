import subprocess
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import tempfile
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

        # 转义exec_cmd中的特殊字符，避免破坏expect脚本结构
    def escape_special_chars(self, cmd):
        """转义命令中的特殊字符，确保在expect和bash中正确解析"""
        return cmd.replace('\\', '\\\\') \
                .replace('"', '\\"') \
                .replace("'", "'\\''") \
                .replace('$', '\\$') \
                .replace('`', '\\`')

    def _get_terminal_command(self, 
        exec_cmd: str, 
        terminal_name: str, 
        output_file: str, 
        terminal_line_num: int, 
        blocked_process:int,
        cwd: str,
        remote_os: str,
        remote_ip: str,
        remote_user: str,
        remote_passwd: str,
        ) -> List[str]:
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
            #os.environ["DISPLAY"] = ":0"
            self.create_bashrc_no_title()

            if remote_ip == "127.0.0.1": # 本地运行TE-Agent工具，且本地执行用例可执行程序
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
            else:
                # 本地运行TE-Agent工具，下位机执行用例可执行程序: 使用expect处理SSH登录交互
                #print("本地运行TE-Agent工具，下位机执行用例可执行程序")
                if remote_os != "HarmonyOS":
                    if blocked_process == 1:
                        expect_commands_OK = ( 
                            'export TERM=xterm-256color; '
                            f'expect -c "set timeout 30; '
                            f'spawn ssh {remote_user}@{remote_ip}; '
                            'expect { \n'
                            '   \\"Are you sure you want to continue connecting (yes/no)?\\" { send \\"yes\\r\\"; exp_continue; } \n'
                            '   -re {[Pp]assword:?\\s*|口令:?\\s*} { send \\"' + remote_passwd + '\\r\\"; exp_continue; } \n'
                            '   \\"Permission denied\\" { exit 1; } \n'
                            '   -re {[#$]\\s*} { send \\"script -q -c \\\'\' '+ exec_cmd + '\\\'\' :; /dev/null 2>&1 | tee -a -;\\r\\"; interact; } \n'
                            '}; '
                            'interact" 2>&1 | tee -a ' + output_file + '; '
                            'bash --rcfile ~/.bashrc_no_title --noprofile'
                        )
                        expect_commands = ( 
                            'export TERM=xterm-256color; '
                            f'expect -c "set timeout 30; '
                            f'spawn ssh {remote_user}@{remote_ip}; '
                            'expect { \n'
                            '   \\"Are you sure you want to continue connecting (yes/no)?\\" { send \\"yes\\r\\"; exp_continue; } \n'
                            '   -re {[Pp]assword:?\\s*|口令:?\\s*} { send \\"' + remote_passwd + '\\r\\"; exp_continue; } \n'
                            '   \\"Permission denied\\" { exit 1; } \n'
                            '   -re {[#$]\\s*} { send \\"script -q -c \\\'\\\'\' cd ' + cwd + '; '+ exec_cmd + '\\\'\\\'\' /dev/null 2>&1 | tee -a -;\\r\\"; interact; } \n'
                            '}; '
                            'interact" 2>&1 | tee -a ' + output_file + '; '
                            'bash --rcfile ~/.bashrc_no_title --noprofile'
                        )
                        #  send \\"script -q -c \\\'\' cd ' + cwd + '; '+ exec_cmd + '\\\'\' :; /dev/null 2>&1 | tee -a -;\\r\\"; interact;
                    else:
                        expect_commands = ( 
                            'export TERM=xterm-256color; '
                            f'expect -c "set timeout 30; '
                            f'spawn ssh {remote_user}@{remote_ip}; '
                            'expect { \n'
                            '   \\"Are you sure you want to continue connecting (yes/no)?\\" { send \\"yes\\r\\"; exp_continue; } \n'
                            '   -re {[Pp]assword:?\s*|口令:?\s*} { send \\"' + remote_passwd + '\\r\\"; exp_continue; } \n'
                            '   \\"Permission denied\\" { exit 1; } \n'
                            '   -re {[#$]\s*} { send \\"(cd ' + cwd + ';' + exec_cmd + ') 2>&1 | tee -a -;\\r\\"; interact; } \n'
                            '}; '
                            'interact" 2>&1 | tee -a ' + output_file + '; '
                            'bash --rcfile ~/.bashrc_no_title --noprofile'
                        ) # (...)的是子shell，在子shell中cd只会改变子shell的工作目录
                    '''
                    return [
                        "xterm",
                        "-name", f"{terminal_name}",
                        "-T", f"{terminal_name}",
                        "-geometry", f"120x{terminal_line_num}",
                        "-e", f"bash -c '{expect_commands}'"
                    ]
                    '''
                else:
                    # 转义exec_cmd中的特殊字符,避免bash解析错误
                    #escaped_exec_cmd = exec_cmd.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
                    escaped_exec_cmd = self.escape_special_chars(exec_cmd)
                    expect_commands = (
                            'export TERM=xterm-256color; '
                            'stty cooked; '
                            f'echo "=== 鸿蒙设备远程执行 ===" | tee -a {output_file}; '
                            f'echo "设备IP: {remote_ip} | 执行命令: {escaped_exec_cmd}" | tee -a {output_file}; '
                            f'if ! hdc list targets | grep -q "{remote_ip}"; then '
                            f'  echo "错误：未找到鸿蒙设备 {remote_ip}，请检查hdc连接" | tee -a {output_file}; '
                            '  bash --rcfile ~/.bashrc_no_title --noprofile; '
                            'else '
                            f'  hdc shell "(cd {cwd};{escaped_exec_cmd}) 2>&1 | tee -a -" 2>&1 | tee -a {output_file}; '# 执行命令：子shell包裹
                            f'  echo "命令执行完成，终端保持打开状态..." | tee -a {output_file}; '
                            '  bash --rcfile ~/.bashrc_no_title --noprofile; ' # 保活
                            'fi'
                        )
                return [
                    "xterm",
                    "-name", f"{terminal_name}",  # 终端窗口名称（便于识别）
                    "-T", f"{terminal_name}",    # 终端标题栏显示名称
                    "-geometry", f"120x{terminal_line_num}",  # 窗口大小（宽120字符，高N行）
                    "-e", f"bash -c '{expect_commands}'"  # 执行构造好的hdc命令逻辑
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

    def start_subprocess_pre_post(self, exec_cmd: str, terminal_name: str, remote_os: str,
        remote_ip: str, remote_user: str, remote_passwd: str,
        blocked_process:int = 0, # 在xterm终端中执行的程序是否是持续运行不退出，即阻塞式进程
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
            output_file = self.create_log_file(log_path, log_file)

            # 生成终端命令
            self.create_bashrc_no_title()

            # 创建唯一的临时文件名前缀，避免多实例冲突
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            exit_code_file = f"logs/{remote_ip}_{terminal_name}_exit_code_{timestamp}.tmp"
            error_output_file = f"logs/{remote_ip}_{terminal_name}_error_log_{timestamp}.tmp"

            if remote_ip == "127.0.0.1": # 本地运行TE-Agent工具，且本地执行用例可执行程序
                # 创建包装器脚本，这是确保退出码传递的关键
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                    wrapper_script = f.name
                    f.write(f'''#!/bin/bash
                        # 执行实际命令并将错误输出重定向到临时文件
                        "$@" 2> {error_output_file}
                        cmd_exit_code=$?
                        # 保存退出码
                        echo $cmd_exit_code > {exit_code_file}
                        echo "命令执行完成，退出码: $cmd_exit_code"
                        exit $cmd_exit_code
                        ''')
                os.chmod(wrapper_script, 0o755)

                # 创建实际执行的命令脚本
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                    cmd_script = f.name
                    f.write(f'''#!/bin/bash
                        export TERM=xterm-256color
                        stty cooked
                        # 全局重定向：将整个脚本的输出写入日志
                        exec > >(tee -a {output_file}) 2>&1
                        echo "当前指令执行目录：$(pwd)"
                        ({exec_cmd}) 
                        echo "当前指令退出码："
                        echo ${{PIPESTATUS[0]}}
                        exit ${{PIPESTATUS[0]}}
                        ''')
                os.chmod(cmd_script, 0o755)

                # 构建xterm命令，直接执行临时脚本
                terminal_cmd = [
                    "xterm",
                    "-T", terminal_name,
                    "-geometry", f"120x{terminal_line_num}",
                    "-e", wrapper_script, cmd_script
                ]
            else: # 本地运行TE-Agent工具，下位机执行用例可执行程序
                escaped_exec_cmd = self.escape_special_chars(exec_cmd) # 对exec_cmd进行转义处理
                remote_error_file = f"/tmp/{remote_ip}_{terminal_name}_remote_command_error_{timestamp}.tmp"
                remote_exit_code = f"/tmp/{remote_ip}_{terminal_name}_remote_exit_code_{timestamp}.tmp"
                harmony_temp_err = f"/data/{remote_ip}_{terminal_name}_hdc_cmd_error_{timestamp}.tmp"  # 鸿蒙侧错误输出文件
                harmony_temp_exit = f"/data/{remote_ip}_{terminal_name}_hdc_cmd_exit_{timestamp}.tmp"  # 鸿蒙侧退出码文件
                # 1. 创建包装器脚本：处理hdc命令执行、退出码和错误捕获
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                    wrapper_script = f.name
                    f.write(f'''#!/bin/bash
                        # 捕获本地命令的执行错误（如设备连接失败）
                        "$@" 2> {error_output_file}
                        local_exit_code=$?
                        
                        # 尝试从远程命令获取退出码（如果文件存在）
                        if [ -f "{exit_code_file}" ]; then
                            cmd_exit_code=$(cat "{exit_code_file}" 2>/dev/null | grep -E '^[0-9]+$' | head -n1)
                        else
                            cmd_exit_code=$local_exit_code
                        fi

                        # 保存最终退出码并输出日志
                        echo "$cmd_exit_code" > "{exit_code_file}"
                        echo "远程命令执行完成，最终退出码: $cmd_exit_code"
                        exit $cmd_exit_code
                        ''')
                os.chmod(wrapper_script, 0o755)
                if remote_os != "HarmonyOS": 
                    # 2. 创建远程执行命令脚本
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                        cmd_script = f.name
                        # 构建expect脚本，捕获远程命令的退出码
                        expect_script = f'''#!/bin/bash
                            export TERM=xterm-256color
                            stty cooked

                            # 全局重定向：将整个脚本的输出写入日志
                            exec > >(tee -a {output_file}) 2>&1

                            # 1. 执行远程命令并获取退出码,先用bash处理文件判断，再调用expect处理交互
                            expect -c '
                            set timeout 30
                            spawn ssh {remote_user}@{remote_ip}
                            expect {{
                                "Are you sure you want to continue connecting (yes/no)?" {{
                                    send "yes\\r"
                                    exp_continue
                                }}
                                -re {{[Pp]assword:?\\s*|口令:?\\s*}} {{
                                    send "{remote_passwd}\\r"
                                    exp_continue
                                }}
                                "Permission denied" {{ exit 1}}
                                -re {{[#$]\\s*}} {{
                                    # 执行命令并同时捕获 stdout、stderr 和退出码
                                    send "({escaped_exec_cmd}) 2> {remote_error_file}; echo \\"\\$?\\" > {remote_exit_code}; echo \\"退出远程连接前，打印命令退出状态码：\\"; cat /tmp/remote_exit_code.tmp;cat {remote_error_file}; exit\\r"
                                    expect eof
                                }}
                                timeout {{exit 2}}
                                eof {{ exit 0}}
                            }}
                            '

                            # 2. 用bash处理退出码文件传输（避免在expect中使用bash语法）
                                expect -c '
                                spawn scp {remote_user}@{remote_ip}:{remote_exit_code} {exit_code_file}
                                expect {{
                                    -re {{[Pp]assword:?\\s*|口令:?\\s*}} {{
                                        send "{remote_passwd}\\r"
                                        exp_continue
                                    }}
                                    eof
                                }}
                                '
                                
                                # 读取退出码判断是否需要传输错误信息文件
                                exit_code=$(cat {exit_code_file})
                                if [ $exit_code -ne 0 ]; then
                                    expect -c '
                                    spawn scp {remote_user}@{remote_ip}:{remote_error_file} {error_output_file}
                                    expect {{
                                        -re {{[Pp]assword:?\\s*|口令:?\\s*}} {{
                                            send "{remote_passwd}\\r"
                                            exp_continue
                                        }}
                                        eof
                                    }}
                                    '
                                fi
                                
                                # 清理远程文件
                                expect -c '
                                spawn ssh {remote_user}@{remote_ip} "rm -f {remote_exit_code} {remote_error_file}"
                                expect {{
                                        -re {{[Pp]assword:?\\s*|口令:?\\s*}} {{
                                            send "{remote_passwd}\\r"
                                            exp_continue
                                        }}
                                        eof
                                    }}
                                '
                            '''
                        f.write(expect_script)
                    os.chmod(cmd_script, 0o755)
                    #print("\n===== cmd_script 内容如下 =====")
                    #with open(cmd_script, 'r') as f:
                    #    print(f.read())
                else:
                    # 2. 创建命令脚本：通过hdc shell执行目标命令，同步输出到日志
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                        cmd_script = f.name
                        hdc_exec_script = f'''#!/bin/bash
                            export TERM=xterm-256color
                            stty cooked
                            # 全局重定向：将整个脚本的输出写入日志
                            exec > >(tee -a {output_file}) 2>&1

                            echo "=== 开始执行鸿蒙远程命令 ===" 
                            echo "目标设备IP: {remote_ip}" 
                            echo "执行命令: {exec_cmd}" 

                            echo "[准备] 清理鸿蒙设备临时文件..." 
                            hdc shell "rm -f {harmony_temp_exit} {harmony_temp_err}" > /dev/null 2>&1
                            if [ $? -ne 0 ]; then
                                echo "[警告] 清理临时文件失败，可能影响退出码捕获" 
                            fi

                            echo "[执行] 正在鸿蒙设备上通过hdc shell运行命令..." 
                            hdc shell "({escaped_exec_cmd}) 2> {harmony_temp_err}; echo \$? > {harmony_temp_exit};" 2>&1 
                            
                            echo "[日志] 错误码和错误日志如下：" 
                            hdc shell "cat {harmony_temp_exit}; cat {harmony_temp_err}" 2>&1 
                            echo "[等待] 等待命令执行结果同步..." 
                            sleep {sleep_time}

                            echo "[拷贝] 拷贝远程鸿蒙设备上的退出码文件和错误日志文件..." 
                            hdc file recv {harmony_temp_exit} {exit_code_file} > /dev/null 2>&1
                            hdc file recv {harmony_temp_err} {error_output_file} > /dev/null 2>&1

                            hdc shell "rm -f {harmony_temp_exit} {harmony_temp_err}" > /dev/null 2>&1

                            echo "=== 鸿蒙远程命令执行结束 ===" 
                            '''
                        f.write(hdc_exec_script)
                    os.chmod(cmd_script, 0o755)

                    # 3. 构建xterm终端命令：启动终端并执行脚本 
                terminal_cmd = [
                    "xterm",
                    "-name", f"{terminal_name}",  # 终端窗口名称
                    "-T", f"{terminal_name}",    # 终端标题
                    "-geometry", f"120x{terminal_line_num}",  # 窗口大小（宽x高）
                    "-e", wrapper_script, cmd_script  # 执行包装器+命令脚本
                ]

            proc = subprocess.run(# 阻塞启动xterm终端，执行用例预处理和后置步骤指令
                terminal_cmd,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout
                )

            # 从临时文件读取真实退出码（绕过xterm直接返回0做返回码的默认行为）
            try:
                real_exit_code = -1
                error_message = ""
                if os.path.exists(exit_code_file) and os.path.getsize(exit_code_file) > 0:
                    with open(exit_code_file, 'r') as f:
                        real_exit_code = int(f.read().strip())
                        #print(f"获取执行结果成功，返回码为: {real_exit_code}")
                else:
                    raise Exception(f"返回码文件：{exit_code_file}不存在或为空")
                # 如果预处理或后置步骤执行失败，读取并显示错误信息
                if real_exit_code != 0:
                    if os.path.exists(error_output_file) and os.path.getsize(error_output_file) > 0:
                        with open(error_output_file, 'r') as f:
                            error_message = f.read().strip()
                            #print(f"pre_command或post_command中exec_cmd实际退出码: {real_exit_code},错误详情:{error_message}") 
                    else:
                        raise Exception(f"错误日志文件：{error_output_file}不存在或为空")
                    # 补充鸿蒙侧错误日志（若存在）
                    if os.path.exists(output_file):
                        with open(output_file, 'r') as f:
                            output_log = f.read()
                            # 提取鸿蒙侧命令的错误输出（从日志中过滤）
                            harmony_err_log = "\n".join([line for line in output_log.splitlines() 
                                                        if "ERROR" in line or line.startswith("cat " + harmony_temp_err)])
                            if harmony_err_log:
                                error_message += f"\n鸿蒙侧命令错误日志：\n{harmony_err_log}"
            except Exception as e:
                print(f"获取执行结果失败: {str(e)}")
            # 清理临时文件
            for tmp_file in [exit_code_file, error_output_file, wrapper_script, cmd_script]:
                try:
                    if os.path.exists(tmp_file):
                        os.remove(tmp_file)
                except:
                    pass

            return (True, proc.stdout, error_message, real_exit_code)
        except subprocess.TimeoutExpired:
            err = f"命令超时（{timeout}秒）: {terminal_cmd}"
            return (False, "", err, -1)  # 超时返回码设为-1
        except subprocess.CalledProcessError as e:
            return (False, e.stdout, e.stderr, e.returncode) # 非0返回码视为失败，返回实际返回码
        except Exception as e:
            err = f"命令执行异常: {str(e)}"
            return (False, "", err, -2)  # 其他错误返回码设为-2

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
        remote_os: str,
        remote_ip: str,
        remote_user: str,
        remote_passwd: str,
        blocked_process:int = 0, # 在xterm终端中执行的程序是否是持续运行不退出，即阻塞式进程
        cwd: Optional[str] = "",  # 子进程工作目录
        log_path: str = "logs",  # 测试步骤日志的输出目录
        log_file: str = "output_step.log",  # 测试步骤日志的文件名
        terminal_line_num: int = 20, # 拉起的xterm终端的高度，即多少行字符
        timeout: int = 30,
        sleep_time: int = 1 # 运行后立马退出的程序，留出时间给它执行
        ) -> Tuple[bool, subprocess.Popen, str, int]:
        """启动一个子流程，在独立终端运行可执行程序，并捕获输出
        :return: 子进程的Popen实例
        """

        try:
            # 步骤1：验证待执行指令的目录是否存在; 远程执行用例的场景，就没必要验证了，因为如下语句是在本地验证该目录是否存在
            if not os.path.isdir(cwd) and remote_ip == "127.0.0.1":
                raise FileNotFoundError(f"用例本地执行的场景下，要切换后用于执行指令的目录不存在：{cwd}")

            output_abs_path = self.create_log_file(log_path, log_file)

            # 生成终端命令
            terminal_cmd = self._get_terminal_command(
                exec_cmd, 
                terminal_name, 
                output_abs_path, 
                terminal_line_num, 
                blocked_process,
                cwd,
                remote_os,
                remote_ip,
                remote_user,
                remote_passwd
                )
            cmd_str = ' '.join(terminal_cmd)
            #print(f"子进程待执行命令：{cmd_str}")

            if remote_ip == "127.0.0.1":
                proc = subprocess.Popen(# 非阻塞启动xterm终端，执行用例指令
                    terminal_cmd,
                    cwd=cwd,
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                    )
            else:
                proc = subprocess.Popen(# 远程场景下，执行subprocess的cwd参数的意义是拉起xterm终端时所在的路径，而非在远程机器上执行用例命令所在的路径
                    terminal_cmd,
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                    )
            time.sleep(sleep_time)  # 有时如果terminal_cmd中拉起的程序是非阻塞式的，即运行后立马退出的，则需要留出时间给它执行

            # 保存子流程对象，便于后续管理
            self.subprocesses.append((proc, output_abs_path))
            #print(f"起xterm终端的子进程id为：{proc.pid}")
            
            # 返回Popen实例
            #return proc
            return (True, proc, "", proc.returncode)
        except FileNotFoundError as e:
            err = f"待执行的命令未找到: {str(e)}" # 输出类似：[Errno 2] No such file or directory: '不存在的命令'
            return (False, "", err, -1)
        except PermissionError as e:
            err = f"可执行程序权限不足: {str(e)}" # 输出类似：[Errno 13] Permission denied: 'no_permission_cmd' 
            return (False, "", err, -2)
        except OSError as e:
            return (False, "", f"系统错误：{str(e)}", -3)
        except ValueError as e:
            return (False, "", f"参数错误：{str(e)}", -4)

    def capture_output_file(self, output_file: str) -> str:
        """读取子进程输出文件的内容（实时捕获输出）"""
        if not os.path.exists(output_file):
            print(f"子进程的实时输出日志不存在：{output_file}, 可能该步骤未成功拉起xterm终端")
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
                #print("没有正在运行的 xterm 终端")
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

  
