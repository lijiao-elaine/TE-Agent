import subprocess
import time
import os
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

class CommandExecutor:
    """处理测试用例中的命令执行、进程管理及结果捕获"""

    # 转义exec_cmd中的特殊字符，避免破坏expect脚本结构
    @staticmethod
    def escape_special_chars(cmd):
        """转义命令中的特殊字符，确保在expect和bash中正确解析"""
        return cmd.replace('\\', '\\\\') \
                .replace('"', '\\"') \
                .replace("'", "'\\''") \
                .replace('$', '\\$') \
                .replace('`', '\\`') \
                .replace('|', '\\\\|') \
                .replace(';', '\\\\;')  \
                .replace('[', '\\\\[')  \
                .replace(']', '\\\\]')  \
                .replace(' ', '\\ ')
    
    @staticmethod
    def run_command(command: str, cwd: Optional[str] = None, timeout: int = 30, retries: int = 2) -> Tuple[bool, str, str, int]:
        """
        执行命令并返回详细结果（适配 merged_document.docx 中返回码校验需求）
        :return: (是否成功, 标准输出, 错误输出, 命令返回码)
        """
        for i in range(retries + 1):
            try:
                result = subprocess.run(
                    command,
                    cwd=cwd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=timeout
                )
                # 返回成功标识、输出、返回码（0为成功）
                return (True, result.stdout, result.stderr, result.returncode)
            except subprocess.TimeoutExpired:
                err = f"命令超时（{timeout}秒）: {command}"
                return (False, "", err, -1)  # 超时返回码设为-1
            except subprocess.CalledProcessError as e:
                # 非0返回码视为失败，返回实际返回码
                return (False, e.stdout, e.stderr, e.returncode)
            except Exception as e:
                err = f"命令执行异常: {str(e)}"
                return (False, "", err, -2)  # 其他错误返回码设为-2
    
    @staticmethod
    def clear_expected_logfile(expected_log: str, remote_os: str, remote_ip: str, remote_user:str, remote_passwd:str, remote_hdc_port:str,
        output_file: str) -> Tuple[bool, str, str, int]:
        #print(f"进入函数：clear_expected_logfile, 备份日志:{expected_log}")
        core_cmd = f"mv -f {expected_log} {expected_log}.bak 2>/dev/null"
        if remote_ip == "127.0.0.1":
            terminal_commands = (
                'export TERM=xterm-256color; '
                'stty cooked; '
                f'echo "当前指令执行目录：$(pwd)；执行日志备份指令: mv {expected_log} {expected_log}.bak" 2>&1 | tee -a {output_file}; '
                f'({core_cmd};exit;) 2>&1 | tee -a {output_file}; '
            )
        else:
            if remote_os != "HarmonyOS":
                terminal_commands = ( 
                    'export TERM=xterm-256color; '
                    'stty cooked; '
                    f'expect -c "set timeout 3; '
                    f'spawn ssh {remote_user}@{remote_ip}; '
                    'expect { \n'
                    '   \\"Are you sure you want to continue connecting (yes/no)?\\" { send \\"yes\\r\\"; exp_continue; } \n'
                    '   -re {[Pp]assword:?\\s*|口令:?\\s*} { send \\"' + remote_passwd + '\\r\\"; exp_continue; } \n'
                    '   \\"Permission denied\\" { exit 1; } \n'
                    '   -re {[#$]\\s*} { send \\" ' + core_cmd + ' 2>&1 | tee -a -;\\r\\"; expect eof; } \n'
                    '   eof { exit 0 } \n'
                    '   timeout { exit 2 } \n'  # 明确处理超时情况
                    '}; '
                    '" 2>&1 | tee -a ' + output_file + '; '
                    'bash --rcfile ~/.bashrc_no_title --noprofile'
                )
            else:
                print("CommandExecutor.clear_expected_logfile: 待验证远程鸿蒙系统下，预处理备份清理日志的逻辑")
                terminal_commands = (
                    'export TERM=xterm-256color; '
                    'stty cooked; '
                    f'echo "=== 鸿蒙设备远程执行 ===" | tee -a {output_file}; '
                    f'echo "设备IP: {remote_ip} | 执行命令备份清理被测系统日志文件{expected_log}为{expected_log}.bak" | tee -a {output_file}; '
                    f'if ! hdc list targets | grep -q "{remote_ip}"; then '
                    f'  echo "错误：未找到鸿蒙设备 {remote_ip}，请检查hdc连接" | tee -a {output_file}; '
                    '  bash --rcfile ~/.bashrc_no_title --noprofile; '
                    'else '
                    f'  hdc -t {remote_ip}:{remote_hdc_port} shell "(mv -f {expected_log} {expected_log}.bak  2>/dev/null;exit;) 2>&1 | tee -a -" 2>&1 | tee -a {output_file}; '# 执行命令：子shell包裹
                    'fi'
                )
            
        # 构建命令列表
        #command = ["xterm", "-T", "pre_clear_logfile", "-geometry", "120x40", "-e", "bash", "-c", terminal_commands]
        command = f"xterm -T pre_clear_logfile -geometry 120x40 -e bash {terminal_commands}"
        return CommandExecutor.run_command(command)

    @staticmethod
    def run_script(shell_script: str, remote_os: str, remote_ip: str, remote_user:str, remote_passwd:str, remote_hdc_port:str,
        output_file:str) -> Tuple[bool, str, str, int]:

        cmd = f"chmod +x '{shell_script}'; nohup '{shell_script}' > /dev/null 2>&1 &"

        if remote_ip == "127.0.0.1":
            #os.system(cmd)
            terminal_commands = (
                'export TERM=xterm-256color; '
                'stty cooked; '
                f'echo "当前指令执行目录：$(pwd)；执行指令：{cmd}" 2>&1 | tee -a {output_file}; '
                f'({cmd}) 2>&1 | tee -a {output_file}; '
            )
        else:
            if remote_os != "HarmonyOS":
                #escaped_exec_cmd = CommandExecutor.escape_special_chars(cmd)
                terminal_commands = ( 
                    'export TERM=xterm-256color; '
                    'stty cooked; '
                    f'expect -c "set timeout 3; '
                    f'spawn ssh {remote_user}@{remote_ip}; '
                    'expect { \n'
                    '   \\"Are you sure you want to continue connecting (yes/no)?\\" { send \\"yes\\r\\"; exp_continue; } \n'
                    '   -re {[Pp]assword:?\\s*|口令:?\\s*} { send \\"' + remote_passwd + '\\r\\"; exp_continue; } \n'
                    '   \\"Permission denied\\" { exit 1; } \n'
                    '   -re {[#$]\\s*} { send \\" (' + cmd + ') 2>&1 | tee -a -;\\r\\"; expect eof; } \n'
                    '   eof { exit 0 } \n'
                    '   timeout { exit 2 } \n'  # 明确处理超时情况
                    '}; '
                    '" 2>&1 | tee -a ' + output_file + '; '
                )
            else:
                print("CommandExecutor.run_script: 待验证远程鸿蒙系统下，执行全流程脚本的逻辑")
                terminal_commands = (
                    'export TERM=xterm-256color; '
                    'stty cooked; '
                    f'echo "=== 鸿蒙设备远程执行 ===" | tee -a {output_file}; '
                    f'echo "设备IP: {remote_ip} | 执行全流程脚本: {cmd}" | tee -a {output_file}; '
                    f'if ! hdc list targets | grep -q "{remote_ip}"; then '
                    f'  echo "错误：未找到鸿蒙设备 {remote_ip}，请检查hdc连接" | tee -a {output_file}; '
                    '  bash --rcfile ~/.bashrc_no_title --noprofile; '
                    'else '
                    f'  hdc -t {remote_ip}:{remote_hdc_port} shell "({cmd};) 2>&1 | tee -a -" 2>&1 | tee -a {output_file}; '# 执行命令：子shell包裹
                    'fi'
                )
            
        # 构建命令列表
        #command = ["xterm", "-T", "run_fullProcess_script", "-geometry", "120x40", "-e", "bash", "-c", terminal_commands]
        command = f"xterm -T run_fullProcess_script -geometry 120x40 -e bash {terminal_commands}"
        return CommandExecutor.run_command(command)

    @staticmethod
    def kill_processes_by_keyword(keyword: str) -> bool:
        """
        根据关键字终止相关进程（后置处理用）
        :param keyword: 进程名关键字（如测试用例标识）
        :return: 是否成功执行终止命令
        """
        try:
            # 查找包含关键字的进程并终止
            subprocess.run(
                f"pkill -f '{keyword}'",
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return True
        except Exception as e:
            print(f"终止进程失败（关键字: {keyword}）: {str(e)}")
            return False

    @staticmethod
    def check_keywords(actual_output: str, expected_keywords: List[str]) -> Dict[str, Any]:
        """
        校验实际输出是否包含所有预期关键词（适配 merged_document.docx 中“期望结果”）
        :param actual_output: 命令执行的实际输出（stdout+stderr）
        :param expected_keywords: 预期需要匹配的关键词列表
        :return: 包含匹配结果的字典
        """
        matched = []
        missing = []
        #print(f"check_keywords:\nactual_output:{actual_output}")

        # 1. 按行分割实际输出（兼容 \n 换行）
        output_lines = actual_output.splitlines()
        # 2. 过滤掉含cat关键词的行（排除命令行本身）。用于避免远程执行时重定向cat的被测系统日志到本地后，把cat命令中的目标词也命中
        excluded_str1  = " cat "
        excluded_str2  = "| grep -F --"
        valid_lines = [line for line in output_lines if excluded_str1 not in line and excluded_str2 not in line]
        # 3. 将有效行重新拼接为字符串（保留原始换行结构）
        valid_output = "\n".join(valid_lines)

        for keyword in expected_keywords:
            # 4. 仅在有效行中检查关键词是否存在
            if keyword in valid_output:
                matched.append(keyword)
            else:
                missing.append(keyword)
        return {
            "all_matched": len(missing) == 0,
            "matched": matched,
            "missing": missing
        }