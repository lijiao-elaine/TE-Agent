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
import os

def get_test_cases_by_module(module_path: str = None) -> list:
    """根据模块路径过滤用例"""
    config_manager = ConfigManager()
    remote_os = config_manager.get_remote_os()
    remote_ip = config_manager.get_remote_ip()
    if remote_ip != "127.0.0.1" and remote_os == "HarmonyOS":
        case_manager = TestCaseManager("test_cases_ohos")
    else:
        case_manager = TestCaseManager()
    all_cases = case_manager.get_all_test_case_paths()
    
    if not module_path:
        return all_cases
    
    target_module = Path(module_path).resolve()
    if not target_module.exists():
        raise FileNotFoundError(f"模块路径不存在: {target_module}")
    
    filtered_cases = []
    for case in all_cases:
        case_abs = Path(case).resolve()
        if target_module in case_abs.parents or case_abs.parent == target_module:
            filtered_cases.append(case)
    
    print(f"模块 {module_path} 下共找到 {len(filtered_cases)} 个用例")
    return filtered_cases

def test_run_case(case_path, init_test_session):
    """pytest批量执行测试用例"""
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
        assert overall_result == "通过", f"用例 {test_case['case_id']} 执行失败（结果：{overall_result}）\n错误详情:\n{error_details}"
    except Exception as e:
        pytest.fail(f"用例执行过程中发生异常: {str(e)}\n{traceback.format_exc()}")

# 使用pytest钩子动态生成测试参数
def pytest_generate_tests(metafunc):
    """在pytest收集用例阶段动态生成参数化用例"""
    print(f"进入钩子函数：pytest_generate_tests")
    # 仅对test_run_case函数生效
    if "case_path" in metafunc.fixturenames and metafunc.function.__name__ == "test_run_case":
        # 从环境变量获取用例列表（用分号分隔）
        cases_str = os.getenv("FILTERED_TEST_CASES", "")
        # 转换为列表（空字符串时返回空列表）
        filtered_cases = cases_str.split(";") if cases_str else []
        # 移除可能的空字符串（如最后一个元素）
        filtered_cases = [case for case in filtered_cases if case]
        
        metafunc.parametrize("case_path", filtered_cases)
    
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

    # 执行单个用例或所有用例
    filtered_cases = []
    if args.testcase:
        case_path = Path(args.testcase)
        if case_path.exists():
            test_case = str(case_path.absolute())
            print(f"待执行的单个用例为：{test_case}")
            filtered_cases.append(test_case)
            #success = run_single_case(str(case_path))
            #exit(0 if success else 1)
        else:
            print(f"错误: 测试用例文件不存在 - {case_path}")
            exit(1)
    else:
        # 获取模块过滤后的用例列表
        filtered_cases = get_test_cases_by_module(args.module)
        
    # 将用例列表存入环境变量（用分号分隔，支持路径含空格）
    os.environ["FILTERED_TEST_CASES"] = ";".join(filtered_cases)
        
    # 构建pytest参数， 加 "-s", 参数可以禁止pytest的输出捕获
    pytest_args = ["-v",  __file__] 
    if args.report:
        pytest_args.extend([f"--html={args.report}", "--self-contained-html"])
        
    # 执行测试
    pytest.main(pytest_args)
    