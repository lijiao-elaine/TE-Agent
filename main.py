#!/usr/bin/env python3
"""
TE-Agent: 测试用例自动化执行智能体
主程序入口
"""

import argparse
import pytest
import traceback
from pathlib import Path
from agent.test_execute_agent import TestExecuteAgent
from test_case_manager.test_case_manager import TestCaseManager
from config.config_manager import ConfigManager  # 导入配置管理器
from utils.command_executor import CommandExecutor
import os
import subprocess
import time

# 全局变量：记录执行状态
SHELL_SCRIPT_EXECUTED = False  # 批次间的全流程脚本是否已执行

# 在文件顶部添加 pytest 标记，排除非测试类，避免收集警告
pytestmark = [pytest.mark.filterwarnings("ignore::pytest.PytestCollectionWarning")]

def get_test_cases_by_module(module_path: str = None, case_type: str = "unit_test") -> list:
    """根据模块路径过滤用例"""
    config_manager = ConfigManager()
    remote_os = config_manager.get_remote_os()
    remote_ip = config_manager.get_remote_ip()
    if case_type == "full_process_test":
        if remote_ip != "127.0.0.1" and remote_os == "HarmonyOS":
            case_manager = TestCaseManager("test_cases_ohos/full_process_test")
        else:
            case_manager = TestCaseManager("test_cases/full_process_test")
    else:
        if remote_ip != "127.0.0.1" and remote_os == "HarmonyOS":
            case_manager = TestCaseManager("test_cases_ohos/unit_test")
        else:
            case_manager = TestCaseManager("test_cases/unit_test")
    all_cases = case_manager.get_all_test_case_paths()
    
    if not module_path:
        return all_cases
    
    target_module = Path(module_path).resolve()
    if not target_module.exists():
        raise FileNotFoundError(f"模块路径不存在: {target_module}")
    
    filtered_cases = []
    for case in all_cases:
        case_abs = Path(case).resolve()
        if target_module in case_abs.parents or case_abs.parent == target_module or case_abs == target_module:
            filtered_cases.append(case)

    print(f"模块 {module_path} 下共找到 {len(filtered_cases)} 个{case_type}用例")
    return filtered_cases

def clear_full_process_logfile(filtered_cases):
    case_manager = TestCaseManager()
    config_manager = ConfigManager()
    remote_os = config_manager.get_remote_os()
    remote_ip = config_manager.get_remote_ip()
    remote_user = config_manager.get_remote_user()
    remote_passwd = config_manager.get_remote_passwd()
    remote_hdc_port = config_manager.get_hdc_port()

    for case_path in filtered_cases:
        case_path_obj = Path(case_path)
        test_case = case_manager.load_test_case(case_path_obj)
        steps = test_case["execution_steps"]

        for step in steps:
            expected_type = step.get("expected_type", "terminal")
            expected_log = step.get("expected_log", "")
                
            if expected_type == "logfile" and expected_log != "":
                #print(f"！！！开始清理被测系统日志:{expected_log}")
                success, stdout, stderr, returncode = CommandExecutor.clear_expected_logfile(
                    expected_log=expected_log,
                    remote_os=remote_os,
                    remote_ip=remote_ip,
                    remote_user=remote_user,
                    remote_passwd=remote_passwd,
                    remote_hdc_port=remote_hdc_port,
                    output_file = f"logs/{remote_ip}_full_process_clear_logfile.log"
                )
                if not success or returncode != 0:
                    raise RuntimeError(
                        f"执行全流程用例前，清理日志文件失败（返回码: {returncode}）\n错误输出: {stderr}"
                    )

def run_full_process_script(shell_script):
    case_manager = TestCaseManager()
    config_manager = ConfigManager()
    remote_os = config_manager.get_remote_os()
    remote_ip = config_manager.get_remote_ip()
    remote_user = config_manager.get_remote_user()
    remote_passwd = config_manager.get_remote_passwd()
    remote_hdc_port = config_manager.get_hdc_port()

    success, stdout, stderr, returncode = CommandExecutor.run_script(
        shell_script=shell_script,
        remote_os=remote_os,
        remote_ip=remote_ip,
        remote_user=remote_user,
        remote_passwd=remote_passwd,
        remote_hdc_port=remote_hdc_port,
        output_file = f"logs/{remote_ip}_run_full_process_script.log"
    )
    if not success or returncode != 0:
        raise RuntimeError(
            f"执行全流程启动或停止脚本失败，（返回码: {returncode}）\n错误输出: {stderr}"
        )

def test_run_case(case_path, init_test_session, batch):
    """pytest批量执行测试用例"""
    global SHELL_SCRIPT_EXECUTED
    shell_script = os.getenv("SHELL_SCRIPT_PATH", "")

    # 标记存在第二批用例
    if batch == 2:
        os.environ["BATCH_2_EXIST_FLAG"] = "True"  # 写入环境变量
    
    # 执行完第一批次的单元测试用例后，执行全流程脚本
    if batch == 2 and not SHELL_SCRIPT_EXECUTED and shell_script:
        batch2_cases = os.getenv("BATCH2_TEST_CASES", "").split(";")
        filtered_cases = [case for case in batch2_cases if case]
        clear_full_process_logfile(filtered_cases) # 在执行全流程脚本前，将所有用例需要检查的日志都清理掉，确保全流程用例检查的日志都是跑全流程生成的

        print(f"\n===== 开始执行全流程shell脚本：{shell_script} =====")
        try:
            run_full_process_script(shell_script)
            time.sleep(20)  # 延迟20秒，确保全流程脚本执行完成
        except Exception as e:
            print(f"执行全流程脚本异常：{str(e)}")
            pytest.fail("全流程脚本执行失败，终止后续用例")
        SHELL_SCRIPT_EXECUTED = True

    try:
        case_path_obj = Path(case_path)
        case_manager = TestCaseManager()
        test_case = case_manager.load_test_case(case_path_obj)
        test_case["_source_path"] = str(case_path_obj)

        agent = TestExecuteAgent()
        final_state = agent.run(test_case)

        # 断言用例结果
        error_details = "\n".join(final_state['errors']) if final_state['errors'] else "无错误"
        overall_result = final_state['case_result'].get("overall_result", "未知")
        #print(f"用例 {test_case.get('case_id')} 执行结果：{overall_result}")
        assert overall_result == "通过", f"用例 {test_case['case_id']} 执行失败（结果：{overall_result}）\n错误详情:\n{error_details}"
    except Exception as e:
        #print(f"用例执行异常：{str(e)}\n{traceback.format_exc()}")
        pytest.fail(f"用例执行过程中发生异常: {str(e)}\n{traceback.format_exc()}")


# 使用pytest钩子动态生成测试参数
def pytest_generate_tests(metafunc):
    """在pytest收集用例阶段动态生成参数化用例"""
    print(f"进入钩子函数：pytest_generate_tests")
    if "case_path" in metafunc.fixturenames and "batch" in metafunc.fixturenames and metafunc.function.__name__ == "test_run_case":
        batch1_cases = os.getenv("BATCH1_TEST_CASES", "").split(";")
        batch1_cases = [case for case in batch1_cases if case]
        
        batch2_cases = os.getenv("BATCH2_TEST_CASES", "").split(";")
        batch2_cases = [case for case in batch2_cases if case]
        
        # 合并用例并添加批次标记
        all_cases_with_batch = []
        for case in batch1_cases:
            all_cases_with_batch.append(pytest.param(case, 1, marks=pytest.mark.batch1))
        for case in batch2_cases:
            all_cases_with_batch.append(pytest.param(case, 2, marks=pytest.mark.batch2))
        
        metafunc.parametrize("case_path,batch", all_cases_with_batch)


if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="测试用例执行工具")
    parser.add_argument(
        "-t", "--testcase", 
        help="指定单个测试用例文件路径（如：test_cases/test_case_1.json）",
        type=str
    )
    parser.add_argument(
        "-m", "--module",
        help="指定模块目录（如test_cases/module_1），执行该模块下所有用例",
        type=str,
        default=None
    )
    parser.add_argument(
        "-r", "--report",
        help="指定HTML报告路径（默认：reports/test_report.html）",
        type=str,
        default=None
    )
    args = parser.parse_args()

    filtered_cases = []
    if args.testcase:
        filtered_cases = get_test_cases_by_module(args.testcase, "unit_test") # 获取单个用例
    else:
        filtered_cases = get_test_cases_by_module(args.module, "unit_test") # 获取模块过滤后的用例列表

    filtered_cases2 = []
    if args.testcase:
        filtered_cases2 = get_test_cases_by_module(args.testcase, "full_process_test")
    else:
        filtered_cases2 = get_test_cases_by_module(args.module, "full_process_test")

    print(f"单元测试用例,共{len(filtered_cases)}个; 全流程测试用例，共{len(filtered_cases2)}个")

    config_manager = ConfigManager()
    full_process_start = config_manager.get_full_process_start_script()
    full_process_stop = config_manager.get_full_process_stop_script()

    # 环境变量传递用例和全流程脚本路径
    os.environ["BATCH1_TEST_CASES"] = ";".join(filtered_cases)
    os.environ["BATCH2_TEST_CASES"] = ";".join(filtered_cases2)
    os.environ["SHELL_SCRIPT_PATH"] = full_process_start
    #os.environ["STOP_SCRIPT_PATH"] = full_process_stop

    pytest_args = ["-v",  __file__]  # "--capture=tee-sys", ： 捕获 stdout/stderr 输出（用于报告生成）
    if args.report:
        pytest_args.extend([f"--html={args.report}", "--self-contained-html"])
            
    # 执行测试
    exit_code = pytest.main(pytest_args)

    print(f"所有单元测试用例和全流程用例执行完成， pytest 会话执行完成，退出码：{exit_code}")

    # 验证html报告
    report_path = os.getenv("REPORT_PATH", "")
    report_final_path = report_path if report_path else config_manager.get_report_file()
    if Path(os.path.abspath(report_final_path)).is_file(): 
        print(f"\n测试完成，用例结果已填充到 {config_manager.get_result_word_file()}")
        print(f"HTML测试报告已生成: {os.path.abspath(report_final_path)}")
    else:
        print(f"\n警告: HTML测试报告文件不存在 - {os.path.abspath(report_final_path)}")

    # 用例执行完成后，执行stop全流程的脚本（在报告生成前）
    batch_2_exist = os.getenv("BATCH_2_EXIST_FLAG", "False") == "True"
    if batch_2_exist and full_process_stop:
        stop_script_path = Path(full_process_stop)
        if stop_script_path.exists():
            print(f"\n开始执行stop全流程的脚本：{stop_script_path} ")
            run_full_process_script(stop_script_path)
        else:
            print(f"警告：stop全流程的脚本不存在 - {stop_script_path}")
