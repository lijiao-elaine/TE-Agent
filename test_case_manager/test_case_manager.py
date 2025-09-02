"""
测试用例管理器
负责读取和管理测试用例文件
"""
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from docx import Document
from pathlib import Path

class TestCaseManager:
    """测试用例管理器，负责测试用例文件的加载、解析和验证"""
    
    def __init__(self, test_cases_dir: str = "test_cases"):
        """初始化测试用例管理器
        
        Args:
            test_cases_dir: 测试用例文件存放目录
        """
        self.test_cases_dir = Path(test_cases_dir)
        # 确保测试用例根目录存在
        self.test_cases_dir.mkdir(parents=True, exist_ok=True)

    def _validate_test_case_dir(self) -> None:
        """验证测试用例目录是否存在，不存在则创建"""
        if not self.test_cases_dir.exists():
            self.test_cases_dir.mkdir(parents=True, exist_ok=True)
            print(f"测试用例目录不存在，已自动创建: {self.test_cases_dir}")

    def get_all_test_case_paths(self) -> List[str]:
        """获取所有测试用例文件路径"""
        #return [str(path) for path in self.test_cases_dir.glob("*.json")]
        """
        递归查找所有子目录中的JSON用例文件
        :return: 所有JSON用例文件的绝对路径列表
        """
        if not self.test_cases_dir.exists():
            raise FileNotFoundError(f"测试用例根目录不存在: {self.test_cases_dir.absolute()}")
        
        # 递归查找所有.json文件, rglob模式会匹配所有子目录
        json_files = list(self.test_cases_dir.rglob("*.json"))
        
        if not json_files:
            print(f"警告: 在 {self.test_cases_dir.absolute()} 及其子目录中未找到任何JSON用例文件")
        
        # 转换为字符串路径并返回
        return [str(file.absolute()) for file in json_files]

    def load_test_case(self, case_path: str) -> Dict[str, Any]:
        """
        加载单个测试用例文件
        :param case_path: 测试用例文件路径
        :return: 测试用例字典
        """
        if not isinstance(case_path, Path):
            raise TypeError(f"case_path必须是Path对象，而非{type(case_path).__name__}")

        if not Path(case_path).exists():
            raise FileNotFoundError(f"测试用例文件不存在: {case_path.absolute()}")
        
        if case_path.suffix.lower() != ".json":
            raise ValueError(f"不支持的文件格式: {case_path.suffix}，仅支持JSON文件")
         
        with open(case_path, "r", encoding="utf-8") as f:
            try:
                test_case = json.load(f)
                self._validate_test_case(test_case, case_path)
                return test_case
            except json.JSONDecodeError as e:
                raise ValueError(f"测试用例文件格式错误 {case_path.name}: 不是有效的JSON - {str(e)}")
            except Exception as e:
                raise RuntimeError(f"加载测试用例 {case_path.name} 失败: {str(e)}")

    def load_all_test_cases(self) -> List[Dict]:
        """加载所有测试用例文件"""
        case_paths = self.get_all_test_case_paths()
        return [self.load_test_case(path) for path in case_paths]

    def _validate_test_case(self, test_case: Dict, case_path: str) -> None:
        """验证测试用例是否包含必要字段"""
        # 验证测试用例必填字段
        required_fields = ["case_id", "case_name", "execution_steps"]
        for field in required_fields:
            if field not in test_case:
                raise ValueError(f"测试用例 {case_path} 缺少必要字段: {field}")
        
        # 验证步骤配置
        if not isinstance(test_case["execution_steps"], list):
            raise ValueError(f"测试用例 {case_path} 中 'execution_steps' 必须为列表")
            
        for idx, step in enumerate(test_case["execution_steps"]):
            step_required = ["exec_path", "command", "expected_output", "blocked_process", "sleep_time"]
            for field in step_required:
                if field not in step:
                    raise ValueError(
                        f"测试用例 {case_path} 中步骤 {idx+1} 缺少必要字段: {field}"
                    )

    def get_test_case_by_name(self, case_name: str) -> Optional[Dict]:
        """通过用例名称查找测试用例"""
        for test_case in self.load_all_test_cases():
            if test_case.get("case_name") == case_name:
                return test_case
        return None

    def get_test_case_report(self, original_word_file: str, new_word_file: str):
        # 打开原始文档
        doc = Document(original_word_file)
        doc.save(new_word_file)
