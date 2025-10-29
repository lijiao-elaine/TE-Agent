"""
工作流节点函数
实现智能体的各个处理步骤
"""
import time
from datetime import datetime
import os
import traceback
from pathlib import Path
from typing import Dict
import glob
from utils.command_executor import CommandExecutor
from utils.screenshot_handler import ScreenshotHandler
from utils.word_report_filler import WordReportFiller
from agent.state import TestState
from config.config_manager import ConfigManager  # 导入配置管理器
import subprocess


def run_pre_commands(state: TestState) -> Dict:
    """预处理节点：执行环境准备命令（适配 merged_document.docx 中前置步骤）"""
    print("="*40+"run_pre_commands"+"="*40)
    try:
        config_manager = ConfigManager()
        #pdb.set_trace()
        case_config = state.case_config 
        case_id = case_config["case_id"]
        pre_commands = case_config.get("pre_commands", [])
        timeout = config_manager.get("execution.pre_command_timeout", 30)
        os.environ["DISPLAY"] = config_manager.get("env.DISPLAY", ":0")
        log_path = config_manager.get_log_path()
        remote_os = config_manager.get_remote_os()
        remote_ip = config_manager.get_remote_ip()
        remote_user = config_manager.get_remote_user()
        remote_passwd = config_manager.get_remote_passwd()
        remote_hdc_port = config_manager.get_hdc_port()

        state.add_log(f"开始预处理步骤 (用例: {case_config['case_name']})")
        
        if not pre_commands:
            state.add_log("无预处理命令需要执行")
            state.current_step = 0
            return {"current_step": 0}

        if pre_commands:
            state.add_log(f"开始执行预处理命令 (共 {len(pre_commands)} 条，超时: {timeout}s)")
            idx = 0
            for cmd in pre_commands:
                if not cmd:
                    continue
                state.add_log(f"执行预处理命令: {cmd} ")
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                log_file_name=f"{remote_ip}_{case_id}_log_pre_{idx}_{timestamp}.log"
                terminal_name=f"{case_id}_pre_{idx}"
                # 适配新返回值 (success, stdout, stderr, returncode)
                success, stdout, stderr, returncode = state.proc_manager.start_subprocess_pre_post(
                    exec_cmd=cmd,
                    blocked_process=0,
                    log_path=log_path,
                    terminal_name=terminal_name,
                    terminal_line_num=40,
                    log_file=log_file_name,
                    timeout=timeout,
                    sleep_time=3,
                    remote_os=remote_os,
                    remote_ip=remote_ip,
                    remote_user=remote_user,
                    remote_passwd=remote_passwd,
                    remote_hdc_port=remote_hdc_port
                )
                idx += 1
                
                if not success or returncode != 0: 
                    #state.add_log(f"预处理命令执行失败（返回码: {returncode}）\n错误输出: {stderr}")
                    raise RuntimeError(
                        f"预处理命令执行失败（返回码: {returncode}）\n错误输出: {stderr}"
                    )
                else:
                    state.add_log(f"预处理命令执行成功（返回码: {returncode}）")

        state.add_log("所有预处理命令执行完成")
        state.current_step = 0
        return {"current_step": 0}
    except Exception as e:
        #error_msg = f"预处理步骤失败: {str(e)}\n{traceback.format_exc()}"
        error_msg = f"预处理步骤失败: {traceback.format_exc()}"
        state.add_error(error_msg)
        state.current_step = -1
        return {"current_step": -1}


def run_test_step(state: TestState) -> Dict:
    """步骤执行节点：按顺序执行测试步骤（适配 merged_document.docx 中测试步骤）"""
    print("="*40+"run_test_step"+"="*40)
    try:
        config_manager = ConfigManager()
        case_config = state.case_config
        case_result = state.case_result.copy()
        step_idx = state.current_step
        steps = case_config["execution_steps"]
        case_id = case_config["case_id"]
        log_path = config_manager.get_log_path()
        terminal_name=f"{case_id}_step_{step_idx + 1}"
        errors = state.errors

        if step_idx < 0 or errors:
            state.add_log("检测到错误状态，跳过步骤执行")
            return {"current_step": step_idx}

        if step_idx >= len(steps):
            state.add_log("所有测试步骤已执行完成")
            return {"current_step": step_idx}

        # 执行当前步骤
        step = steps[step_idx]
        state.add_log(f"开始执行步骤 {step_idx + 1}/{len(steps)}: {step['command']}")
        
        timeout = step.get("timeout", config_manager.get_default_timeout())
        sleep_time = step.get("sleep_time", config_manager.get_default_sleep_time())
        blocked_process = step['blocked_process']
        remote_os = config_manager.get_remote_os()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        remote_ip = config_manager.get_remote_ip()
        remote_user = config_manager.get_remote_user()
        remote_passwd = config_manager.get_remote_passwd()
        remote_hdc_port = config_manager.get_hdc_port()
        log_file_name=f"{remote_ip}_{case_id}_log_step_{step_idx + 1}_{timestamp}.log"
        
        #if step_idx == 1:
        #    raise Exception(f"raise Exception，用于验证执行部分步骤后，某个步骤还未执行且未记录case_result就异常的场景")

        # 启动子进程执行测试步骤的shell指令
        success, process, errmsg, returncode = state.proc_manager.start_subprocess(
            exec_cmd=step["command"],
            cwd=step["exec_path"],
            blocked_process=blocked_process,
            log_path=log_path,
            terminal_name=terminal_name,
            terminal_line_num=40,
            log_file=log_file_name,
            timeout=timeout,
            sleep_time=sleep_time,
            remote_os=remote_os,
            remote_ip=remote_ip,
            remote_user=remote_user,
            remote_passwd=remote_passwd,
            remote_hdc_port=remote_hdc_port
        )


        # 记录子进程 PID
        #state.processes.extend([proc.pid for proc, _ in state.proc_manager.subprocesses])
        pids = {proc.pid for proc, _ in state.proc_manager.subprocesses}
        state.processes.extend(pids) # 将 state.proc_manager.subprocesses列表中的所有进程id追加到state.processes中

        if errmsg:
            state.add_error(f"测试步骤执行终端输出, errmsg:{errmsg}")

        log_file = state.proc_manager._get_subprocess_log_file(process.pid)

        state.add_log(f"测试步骤执行完成, 终端输出将保存到：{log_file}")
        state.add_log(f"测试步骤执行完成（subprocess.Popen子进程返回码: {returncode}，0:退出，None:未退出）") 

        #if step_idx == 1:
        #    raise Exception(f"raise Exception，用于验证执行部分步骤后，某个步骤执行完成但未记录case_result就异常的场景") 

        # 记录步骤信息（但还未判断步骤执行结果，仅用于先将步骤信息追加进结果列表）
        case_result["steps"].append({
            "step_idx": step_idx + 1,
            "command": step["command"],
            "expected_output": step["expected_output"],
            "keyword_check": "",
            "log_file":log_file,
            "screenshot_path": "",
            "returncode": returncode,  # 记录返回码用于后续校验
            "process_id":process.pid,
            "step_result": ""
        })

        #if step_idx == 1:
        #    raise Exception(f"case_result[steps].append后raise Exception，用于验证执行部分步骤后，某个步骤执行完成且已记录case_result后异常的场景")

        return {
            "current_step": step_idx + 1,
            "case_result": case_result
        }
    except Exception as e:
        error_msg = f"步骤 {step_idx + 1} 执行出现Exception异常: {str(e)}\n{traceback.format_exc()}"
        state.add_error(error_msg)
        state.current_step = step_idx + 1
        return {
            "current_step": step_idx + 1,
            "case_result": case_result
        }

def should_continue(state: TestState) -> str:
    """条件函数：判断是否继续执行下一步测试步骤"""
    current_step = state.current_step
    errors = state.errors
    total_steps = len(state.case_config["execution_steps"])
    
    # 若当前步骤索引小于总步骤数，且没有error信息，继续执行；否则进入后置处理
    if current_step < total_steps and not errors:  
        return "run_step"
    else:
        return "fill_result"

def run_fill_result(state: TestState) -> Dict:
    """回填测试结果节点：按顺序回填每一个测试步骤的结果和用例总体执行结果（适配 merged_document.docx 中测试步骤）"""
    # 等待3秒，待最后一个程序完成和所有前序程序直接的交互后，再检查各程序的终端输出并截图，这个等待时间需要再确认
    time.sleep(3)
    print("="*40+"run_fill_result"+"="*40)

    try:
        config_manager = ConfigManager()
        case_config = state.case_config
        case_result = state.case_result.copy()
        steps = case_config["execution_steps"]
        step_num = state.current_step
        case_id = case_config["case_id"]
        total_steps = len(steps)
        result_len = len(case_result["steps"])
        remote_ip = config_manager.get_remote_ip()
        remote_os = config_manager.get_remote_os()
        remote_user = config_manager.get_remote_user()
        remote_passwd = config_manager.get_remote_passwd()
        remote_hdc_port = config_manager.get_hdc_port()
        
        state.add_log(f"已执行完的测试步骤数量为：{step_num}, 待执行的总步骤数量为：{total_steps}")

        if step_num > 0:
            for step_idx, step in reversed(list(enumerate(steps, start=0))): #start=0表示索引从0开始（默认0） steps=[A, B, C] 则[(2, C), (1, B), (0, A)]
                if step_num < step_idx + 1: # 仅执行了step_num个步骤， 之后的步骤未执行就没有日志和xterm终端可用来截图，不做截图和获取执行结果的处理
                    continue

                state.add_log(f"回填第 {step_idx + 1} 个步骤的结果") 
                terminal_name = f"{case_id}_step_{step_idx + 1}"
                screenshot_name = f"{case_id}_screenshot_step_{step_idx + 1}"
                expected_type = step.get("expected_type", "terminal")
                expected_log = step.get("expected_log", "")
                
                if result_len < step_num: 
                    #state.add_log(f"获取第{step_idx+1}步的进程失败，可能是:1.执行该步骤时没拉起来xterm子进程就异常了; 2.执行完了但case_result.append前发生了异常，需回填该步骤的测试结果")
                    log_files = glob.glob(f"logs/{remote_ip}_{case_id}_log_step_{step_idx + 1}_*.log")
                    log_file_name = Path(log_files[0]).name if log_files else f"{remote_ip}_{case_id}_log_step_{step_idx + 1}_timestamp.log"
                    log_path = config_manager.get_log_path()
                    log_file = os.path.abspath(os.path.join(log_path, log_file_name))
                    case_result["steps"].append({
                        "step_idx": step_idx + 1,
                        "command": step["command"],
                        "expected_output": step["expected_output"],
                        "keyword_check": "",
                        "log_file":log_file,
                        "screenshot_path": "",
                        "returncode": None,  
                        "process_id":"", 
                        "step_result": ""
                    })
                    result_len += 1
                else:
                    process, log_file = state.proc_manager.subprocesses[step_idx]

                if expected_type == "logfile" and expected_log != "":
                    log_file = expected_log
                    #print(f"!!! 通过被测系统日志 {log_file}比对预期结果，而不是与被测程序的终端输出打印比对")

                actual_output = state.proc_manager.capture_output_file(log_file) # 放在if外面，在步骤执行完成但case_result.append前异常的情况，能正常读取到日志，回填正确结果
                
                if actual_output and expected_type == "terminal":
                    # 测试步骤的实时日志非空时，即已拉起了xterm终端并执行了用例指令，需要记录测试步骤截图
                    screenshot_paths = ScreenshotHandler.capture_step_screenshot_terminal(
                        screenshot_name=f"{remote_ip}_{case_id}_screenshot_step_{step_idx + 1}",
                        screenshot_dir=config_manager.get_screenshot_dir(),
                        terminal_name=f"{case_id}_step_{step_idx + 1}",
                        terminal_line_num=40,
                        log_file=log_file,
                        expected_keywords=step["expected_output"]
                    )
                    if not screenshot_paths:
                        state.add_error(f"第{step_idx + 1}步的被测程序执行时的xterm终端截图失败")
                    else:
                        state.add_log(f"已保存第{step_idx + 1}步的被测程序执行时的xterm终端截图: {screenshot_paths}")
                elif actual_output and expected_type == "logfile":
                    success, screenshot_paths = ScreenshotHandler.capture_step_screenshot_logfile(
                        screenshot_name=f"{remote_ip}_{case_id}_screenshot_step_{step_idx + 1}",
                        screenshot_dir=config_manager.get_screenshot_dir(),
                        terminal_name=f"{case_id}_step_{step_idx + 1}",
                        remote_os=remote_os,
                        remote_ip=remote_ip,
                        remote_user=remote_user,
                        remote_passwd=remote_passwd,
                        remote_hdc_port=remote_hdc_port,
                        log_file=log_file,
                        expected_keywords=step["expected_output"]
                    )
                    if not success:
                        state.add_error(f"第{step_idx + 1}步待检查的被测系统日志截图失败")
                    else:
                        state.add_log(f"已保存第{step_idx + 1}步待检查的被测系统日志截图: {screenshot_paths}")
                else:
                    state.add_error(f"第{step_idx + 1}步的执行日志文件或被测系统日志为空，可能是该步骤xterm终端未拉起，测试步骤实际未执行")
                    screenshot_paths = []

                # 结合返回码和关键词匹配判断结果（符合文档评估标准）
                keyword_check = CommandExecutor.check_keywords(actual_output, step["expected_output"])# 关键词检查（按用例要求比对终端输出）
                step_result = "通过" if (keyword_check["all_matched"]) else "不通过"
                state.add_log(f"步骤 {step_idx + 1} 结果: {step_result} (关键词匹配结果: {keyword_check['all_matched']})")

                # 记录步骤结果（包含返回码，适配文档表格中的“测试结果”列）
                case_result["steps"][step_idx]["keyword_check"] = keyword_check
                case_result["steps"][step_idx]["screenshot_path"] = screenshot_paths
                case_result["steps"][step_idx]["step_result"] = step_result

                print("="*20+f"第 {step_idx + 1} 步结果收集完成"+"="*20)

            # 计算总结果（结合返回码和关键词匹配，符合文档评估标准）
            if step_num < total_steps:
                overall_result = "不通过。部分用例步骤因异常未执行" 
            else:
                if not state.errors:
                    all_passed = all(
                        step["keyword_check"]["all_matched"] and step["step_result"] == "通过"
                        for step in state.case_result["steps"]
                    )
                    overall_result = "通过" if all_passed else "不通过"
                else:
                    overall_result = "不通过。部分用例步骤执行时出现异常或截图失败"
        elif step_num == -1:
            overall_result = "不通过。预处理失败，用例步骤全都未执行"
        elif step_num == 0:
            overall_result = "不通过。预处理成功，用例步骤因异常全都未执行"
        else:
            pass

        # 浅拷贝，所以overall_result需要再赋值一次，steps列表不用再次赋值，直接通过修改case_result["steps"]即可修改state.case_result["steps"]
        state.case_result["overall_result"] = overall_result 
        case_result["overall_result"] = overall_result 
        state.add_log(f"用例最终结果: {overall_result}")

        # 填充Word文档（按文档表格结构记录结果）
        result = WordReportFiller.fill_case_results(
            word_file=config_manager.get_result_word_file(),
            step_num=step_num,
            case_result={
                "case_id": case_config["case_id"],
                "case_name": case_config["case_name"],
                "execution_steps": state.case_result["steps"],
                "overall_result": overall_result
            }
        )
        if result:
            state.add_log(f"测试结果已回填至: {config_manager.get_result_word_file()}")
        else:
            state.add_error(f"测试结果回填word测试细则文档失败")

        return {
            "case_result": state.case_result
        }
    except Exception as e:
        error_msg = f"回填结果失败: {str(e)}\n{traceback.format_exc()}"
        state.add_error(error_msg)
        return {"case_result": state.case_result}

def run_post_process(state: TestState) -> Dict:
    """后置处理节点：清理环境（适配 merged_document.docx 中用例终止条件）"""
    print("="*40+"run_post_process"+"="*40)
    try:
        config_manager = ConfigManager()
        case_config = state.case_config
        case_id = case_config["case_id"]
        state.add_log(f"开始后置处理 (用例: {case_config['case_name']})")
        log_path = config_manager.get_log_path()
        remote_os = config_manager.get_remote_os()
        remote_ip = config_manager.get_remote_ip()
        remote_user = config_manager.get_remote_user()
        remote_passwd = config_manager.get_remote_passwd()
        remote_hdc_port = config_manager.get_hdc_port()

        # 执行后置命令，验证返回码
        post_commands = case_config.get("post_commands", [])
        timeout = config_manager.get("execution.post_command_timeout", 30)
        if post_commands:
            state.add_log(f"开始执行后置命令 (共 {len(post_commands)} 条，超时: {timeout}s)")
            idx = 0
            for cmd in post_commands:
                if not cmd:
                    continue
                state.add_log(f"执行后置命令: {cmd}")
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                log_file_name=f"{remote_ip}_{case_id}_log_post_{idx}_{timestamp}.log"
                terminal_name=f"{case_id}_post_{idx}"
                success, stdout, stderr, returncode = state.proc_manager.start_subprocess_pre_post(
                    exec_cmd=cmd,
                    blocked_process=0,
                    log_path=log_path,
                    terminal_name=terminal_name,
                    terminal_line_num=40,
                    log_file=log_file_name,
                    timeout=timeout,
                    sleep_time=3,
                    remote_os=remote_os,
                    remote_ip=remote_ip,
                    remote_user=remote_user,
                    remote_passwd=remote_passwd,
                    remote_hdc_port=remote_hdc_port
                )
                idx += 1
                
                # 非0返回码视为失败
                if not success or returncode != 0:
                    state.add_error(f"后置命令执行失败（返回码: {returncode}）\n错误输出: {stderr}")
                else:
                    state.add_log(f"后置命令执行成功（返回码: {returncode}）")
        # 终止所有子进程和终端窗口
        state.proc_manager.stop_all_subprocesses()
        state.add_log(f"所有子进程已终止")

        return {
            "case_result": state.case_result,
            "errors": state.errors,
            "logs": state.logs
        }
    except Exception as e:
        error_msg = f"后置处理失败: {str(e)}\n{traceback.format_exc()}"
        state.add_error(error_msg)
        #state.add_log(f"后置处理异常: {str(e)}")
        return {
            "case_result": state.case_result,
            "errors": state.errors,
            "logs": state.logs
        }
