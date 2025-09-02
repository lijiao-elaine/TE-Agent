"""
测试用例自动化执行智能体
基于LangGraph构建的工作流智能体
"""

from langgraph.graph import StateGraph, END
from agent.state import TestState
from agent.nodes import (
    run_pre_commands,
    run_test_step,
    should_continue,
    run_fill_result,
    run_post_process
)
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class TestExecuteAgent:
    """测试执行代理类，封装LangGraph工作流及状态管理"""
    
    def __post_init__(self):
        """初始化代理，构建工作流"""
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """构建LangGraph工作流"""
        workflow = StateGraph(TestState)

        # 添加节点
        workflow.add_node("pre_process", run_pre_commands)
        workflow.add_node("run_step", run_test_step)
        workflow.add_node("fill_result", run_fill_result)
        workflow.add_node("post_process", run_post_process)

        # 定义流程
        workflow.set_entry_point("pre_process")
        workflow.add_edge("pre_process", "run_step")
        workflow.add_conditional_edges(
            "run_step",
            should_continue,
            {"run_step": "run_step", "fill_result": "fill_result"}
        )
        workflow.add_edge("fill_result", "post_process")
        workflow.add_edge("post_process", END) 

        return workflow.compile()

    def run(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行测试工作流，封装状态初始化和工作流调用
        Args: test_case: 测试用例配置字典，包含case_id、case_name等字段           
        Returns: 工作流执行后的最终状态
        """
        # 初始化状态（封装状态构建逻辑）
        initial_state = TestState(
            case_config=test_case
        )

        # 添加初始日志
        initial_state.add_log(f"开始执行测试用例: {test_case['case_name']} (ID: {test_case['case_id']})")
        initial_state.add_log(f"测试用例配置文件: {test_case.get('_source_path', '未知')}")

        try:
            # 执行工作流
            final_state = self.workflow.invoke(initial_state)
            #print(f"final_state的type: {type(final_state)}")  # 通常会输出 <class 'dict'>
            #print(f"工作流执行完成, 生成结果final_state: {final_state}")
            print(f"工作流执行完成")
            return final_state
        except Exception as e:
            # 捕获工作流执行中的顶层异常
            error_msg = f"工作流执行失败: {str(e)}"
            initial_state.add_error(error_msg)
            initial_state.add_log(f"工作流执行异常: {error_msg}")
            return initial_state
