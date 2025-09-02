"""
工作流节点函数
实现智能体的各个处理步骤
"""
import time
import traceback
from typing import Dict
from utils.command_executor import CommandExecutor
from utils.screenshot_handler import ScreenshotHandler
from utils.word_report_filler import WordReportFiller
from agent.state import TestState
from config.config_manager import ConfigManager  # 导入配置管理器
import pdb

def run_pre_commands(state: TestState) -> Dict:
    """预处理节点：执行环境准备命令（适配 merged_document.docx 中前置步骤）"""
    try:
        config_manager = ConfigManager()
        #pdb.set_trace()
        case_config = state.case_config
        state.add_log(f"开始预处理步骤 (用例: {case_config['case_name']})")
        
        pre_commands = case_config.get("pre_commands", [])
        timeout = config_manager.get("execution.pre_command_timeout", 30)
        
        if not pre_commands:
            state.add_log("无预处理命令需要执行")
            state.current_step = 0
            return {"current_step": 0}

        for cmd in pre_commands:
            state.add_log(f"执行预处理命令: {cmd} (超时: {timeout}s)")
            # 适配新返回值 (success, stdout, stderr, returncode)
            success, stdout, stderr, returncode = CommandExecutor.run_command(
                cmd, timeout=timeout
            )
            # 按 merged_document.docx 要求：非0返回码视为失败
            if not success or returncode != 0:
                raise RuntimeError(
                    f"预处理命令执行失败（返回码: {returncode}）\n错误输出: {stderr}"
                )
            state.add_log(f"命令执行成功（返回码: {returncode}）")

        state.add_log("所有预处理命令执行完成")
        state.current_step = 0
        return {"current_step": 0}
    except Exception as e:
        # 错误处理逻辑不变
        error_msg = f"预处理步骤失败: {str(e)}\n{traceback.format_exc()}"
        state.add_error(error_msg)
        state.add_log(f"预处理步骤异常: {str(e)}")
        state.current_step = -1
        return {"current_step": -1}


def run_test_step(state: TestState) -> Dict:
    """步骤执行节点：按顺序执行测试步骤（适配 merged_document.docx 中测试步骤）"""
    try:
        config_manager = ConfigManager()
        case_config = state.case_config
        case_result = state.case_result.copy()
        step_idx = state.current_step
        steps = case_config["execution_steps"]
        case_id = case_config["case_id"]
        log_path = config_manager.get_log_path()
        terminal_name=f"{case_id}_step_{step_idx + 1}"
        log_file=f"{case_id}_output_step_{step_idx + 1}.log"
        screenshot_name=f"{case_id}_screenshot_step_{step_idx + 1}"

        if step_idx < 0:
            state.add_log("检测到错误状态，跳过步骤执行")
            return {"current_step": step_idx}

        if step_idx >= len(steps):
            state.add_log("所有测试步骤已执行完成")
            return {"current_step": step_idx}

        # 执行当前步骤（按文档要求验证返回码和输出）
        step = steps[step_idx]
        state.add_log(f"开始执行步骤 {step_idx + 1}/{len(steps)}: {step['command']}")
        
        timeout = step.get("timeout", config_manager.get_default_timeout())
        sleep_time = step.get("sleep_time", config_manager.get_default_sleep_time())
        blocked_process = step['blocked_process']
        # 适配新返回值
        '''
        #success, stdout, stderr, returncode = CommandExecutor.run_command( # 改成subprocess.Popen
            command=step["command"],
            cwd=step["exec_path"],
            timeout=timeout
        )
        '''
        # 启动子进程执行测试步骤的shell指令
        process = state.proc_manager.start_subprocess(
            exec_cmd=step["command"],
            cwd=step["exec_path"],
            blocked_process=blocked_process,
            log_path=log_path,
            terminal_name=terminal_name,
            terminal_line_num=80,
            log_file=log_file,
            timeout=timeout,
            sleep_time=sleep_time
        )


        # 记录子进程 PID
        #state.processes.extend([proc.pid for proc, _ in state.proc_manager.subprocesses])
        pids = {proc.pid for proc, _ in state.proc_manager.subprocesses}
        state.processes.extend(pids)

        state.add_log(f"测试步骤执行完成, 终端输出将保存到：{state.proc_manager._get_subprocess_log_file(process.pid)}")
        state.add_log(f"测试步骤执行完成（子进程返回码: {process.returncode}，0:退出，None:未退出）")

        # 截图（按文档要求记录步骤截图） 暂时过滤截图操作，待放开
        #time.sleep(2)
        screenshot_paths = ScreenshotHandler.capture_step_screenshot(
            screenshot_name=screenshot_name,
            screenshot_dir=config_manager.get_screenshot_dir(),
            terminal_name=terminal_name,
            terminal_line_num=80,
            log_file=state.proc_manager._get_subprocess_log_file(process.pid),
            expected_keywords=step["expected_output"]
        )
        #pdb.set_trace()
        if not screenshot_paths:
            state.add_error(f"截图失败，未生成截图文件")
        else:
            state.add_log(f"已保存步骤截图: {screenshot_paths}")

        #screenshot_paths = "/home/lijiao/work/GD-Agent/examples/StartedNode/build"

        # 读取子进程输出的日志文件
        actual_output = state.proc_manager.capture_output(process.pid)

        # 关键词检查（按文档要求比对输出） 
        keyword_check = CommandExecutor.check_keywords(actual_output, step["expected_output"])

        # 结合返回码和关键词匹配判断结果（符合文档评估标准）
        #step_result = "通过" if (success and returncode == 0 and keyword_check["all_matched"]) else "不通过"
        step_result = "通过" if (keyword_check["all_matched"]) else "不通过"
        state.add_log(f"步骤 {step_idx + 1} 结果: {step_result} (关键词匹配结果: {keyword_check['all_matched']})")

        # 记录步骤结果（包含返回码，适配文档表格中的“测试结果”列）
        case_result["steps"].append({
            "step_idx": step_idx + 1,
            "command": step["command"],
            "expected_output": step["expected_output"],
            "keyword_check": keyword_check,
            "log_file":state.proc_manager._get_subprocess_log_file(process.pid),
            "screenshot_path": screenshot_paths,
            "returncode": process.returncode,  # 记录返回码用于后续校验
            "process_id":process.pid,
            "step_result": step_result
        })

        return {
            "current_step": step_idx + 1,
            "case_result": case_result
        }
    except Exception as e:
        # 错误处理逻辑不变
        error_msg = f"步骤 {state.current_step + 1} 执行失败: {str(e)}\n{traceback.format_exc()}"
        state.add_error(error_msg)
        state.add_log(f"步骤执行异常: {str(e)}")
        return {"current_step": -1}

def should_continue(state: TestState) -> str:
    """条件函数：判断是否继续执行下一步测试步骤"""
    current_step = state.current_step
    total_steps = len(state.case_config["execution_steps"])
    
    # 若当前步骤索引小于总步骤数，继续执行；否则进入后置处理
    if current_step < total_steps and current_step != -1:  # 排除错误状态（current_step=-1）
        return "run_step"
    else:
        return "fill_result"

def run_post_process(state: TestState) -> Dict:
    """后置处理节点：清理环境（适配 merged_document.docx 中用例终止条件）"""
    try:
        config_manager = ConfigManager()
        case_config = state.case_config
        state.add_log(f"开始后置处理 (用例: {case_config['case_name']})")
        
        # 执行后置命令（按文档要求验证返回码）
        post_commands = case_config.get("post_commands", [])
        timeout = config_manager.get("execution.post_command_timeout", 30)
        if post_commands:
            state.add_log(f"开始执行后置命令 (共 {len(post_commands)} 条，超时: {timeout}s)")
            for cmd in post_commands:
                state.add_log(f"执行后置命令: {cmd}")
                # 适配新返回值
                success, stdout, stderr, returncode = CommandExecutor.run_command(
                    cmd, timeout=timeout
                )
                if not success or returncode != 0:
                    state.add_error(f"后置命令执行失败（返回码: {returncode}）: {cmd}\n错误输出: {stderr}")
                else:
                    state.add_log(f"后置命令执行成功（返回码: {returncode}）: {cmd}")

        # 终止所有子进程和终端窗口
        state.proc_manager.stop_all_subprocesses()
        state.add_log(f"所有子进程已终止")

        # 计算总结果（结合返回码和关键词匹配，符合文档评估标准）
        if not state.errors:
            all_passed = all(
                step["returncode"] == 0 and step["keyword_check"]["all_matched"]
                for step in state.case_result["steps"]
            )
            overall_result = "通过" if all_passed else "不通过"
        else:
            overall_result = "不通过"

        state.case_result["overall_result"] = overall_result
        state.add_log(f"用例最终结果: {overall_result}")

        # 填充Word文档（按文档表格结构记录结果）
        WordReportFiller.fill_case_results(
            word_path=config_manager.get_result_word_path(),
            case_result={
                "case_id": case_config["case_id"],
                "case_name": case_config["case_name"],
                "execution_steps": state.case_result["steps"],
                "overall_result": overall_result
            }
        )

        return {
            "case_result": state.case_result,
            "errors": state.errors,
            "logs": state.logs
        }
    except Exception as e:
        # 错误处理逻辑不变
        error_msg = f"后置处理失败: {str(e)}\n{traceback.format_exc()}"
        state.add_error(error_msg)
        state.add_log(f"后置处理异常: {str(e)}")
        return {
            "case_result": state.case_result,
            "errors": state.errors,
            "logs": state.logs
        }
