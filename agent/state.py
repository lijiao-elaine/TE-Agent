"""
智能体状态管理
定义工作流中传递的数据结构
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from utils.subprocess_manager import SubprocessManager

@dataclass
class TestState:
    """LangGraph工作流状态结构定义，包含日志和错误记录"""
    # 用例配置（默认空字典）
    case_config: Optional[Dict[str, Any]] = field(default_factory=dict)

    # 用例执行结果（默认空字典，包含初始结构）
    case_result: Optional[Dict[str, Any]] = field(default_factory=lambda: {"steps": [], "overall_result": "未执行"})

    # 用于管理子进程的共享实例
    proc_manager: SubprocessManager = field(default_factory=SubprocessManager)
    
    # 进程PID列表（默认空列表）
    processes: List[int] = field(default_factory=list)

    # 当前步骤索引（默认0）
    current_step: int = 0

    # 错误信息列表（默认空列表）
    errors: List[str] = field(default_factory=list)

    # 日志信息列表（默认空列表）
    logs: List[str] = field(default_factory=list)

    def add_log(self, message: str):
        """添加日志信息"""
        self.logs.append(message)
        print(f"[LOG] {message}")
    
    def add_error(self, error: str):
        """添加错误信息"""
        self.errors.append(error)
        print(f"[ERROR] {error}")