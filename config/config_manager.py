import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """全局配置管理器，负责加载和管理config.yaml中的配置"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载并解析YAML配置文件
        
        Returns:
            解析后的配置字典
            
        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: YAML格式错误
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
            
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"配置文件格式错误: {str(e)}")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（支持点分隔符嵌套查询）
        
        示例: 
            get("execution.default_timeout") 等价于获取 config['execution']['default_timeout']
            
        Args:
            key: 配置键（支持嵌套键，如"parent.child"）
            default: 默认值
            
        Returns:
            配置值或默认值
        """
        keys = key.split(".")
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def get_original_word_file(self) -> str:
        """获取原始测试用例Word文档路径"""
        return self.get("word_documents.original_template_file", "merged_word.docx")

    def get_result_word_file(self) -> str:
        """获取填充结果后的Word文档路径"""
        return self.get("word_documents.result_output_file", "reports/test_report.docx")

    def get_default_timeout(self) -> int:
        """获取默认步骤超时时间（秒）"""
        return self.get("execution.default_timeout", 60)
    
    def get_default_sleep_time(self) -> int:
        """获取步骤执行等待时间（秒）"""
        return self.get("execution.sleep_time", 1)

    def get_remote_os(self) -> str:
        """获取远程执行命令的开发板os类型"""
        return self.get("execute_machine.remote_os", "ubuntu")

    def get_remote_ip(self) -> str:
        """获取远程执行命令的开发板ip地址"""
        return self.get("execute_machine.remote_ip", "127.0.0.1")

    def get_remote_user(self) -> str:
        """获取远程执行命令的开发板登录用户名"""
        return self.get("execute_machine.remote_user", "user")

    def get_remote_passwd(self) -> str:
        """获取远程执行命令的开发板登录密码"""
        return self.get("execute_machine.remote_passwd", "Mind@123")

    def get_hdc_port(self) -> str:
        """获取远程执行命令的开发板登录密码"""
        return self.get("execute_machine.hdc_port", "8710")

    def get_screenshot_dir(self) -> str:
        """获取截图保存目录"""
        return self.get("reports.screenshot_dir", "reports/screenshots")

    def get_log_path(self) -> str:
        """获取日志保存目录"""
        return self.get("logging.log_path", "logs")

    def get_report_file(self) -> str:
        """获取测试报告保存目录"""
        return self.get("reports.report_file", "reports/test_report.html")

    def get_allure_results_path(self) -> str:
        """生成allure-results测试报告保存目录"""
        return self.get("reports.allure_results", "reports/allure_results")

    def get_env_DISPLAY(self) -> str:
        """获取测试报告保存目录"""
        return self.get("env.DISPLAY", ":0")

    def get_full_process_start_script(self) -> str:
        """获取全流程脚本路径"""
        return self.get("script.full_process_script", "")

    def get_full_process_stop_script(self) -> str:
        """获取终止全流程脚本路径"""
        return self.get("script.stop_full_process_script", "")

    def save_config(self) -> None:
        """保存当前配置到文件（用于动态修改配置后持久化）"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.config, f, allow_unicode=True, sort_keys=False)
    