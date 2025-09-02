import subprocess
import time
from typing import Dict, List, Tuple, Optional, Any

class CommandExecutor:
    """处理测试用例中的命令执行、进程管理及结果捕获"""
    
    @staticmethod
    def run_command(command: str, cwd: Optional[str] = None, timeout: int = 30, retries: int = 2) -> Tuple[bool, str, str, int]:
        """
        执行命令并返回详细结果（适配 merged_document.docx 中返回码校验需求）
        :return: (是否成功, 标准输出, 错误输出, 命令返回码)
        """
        for i in range(retries + 1):
            try:
                #print(f"subprocess.run的运行路径：{cwd}，执行命令：{command}")
                #print("timeout类型：", type(timeout), "值：", timeout) # <class 'int'>
                result = subprocess.run(
                    command,
                    cwd=cwd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
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
        for keyword in expected_keywords:
            if keyword in actual_output:
                matched.append(keyword)
            else:
                missing.append(keyword)
        return {
            "all_matched": len(missing) == 0,
            "matched": matched,
            "missing": missing
        }