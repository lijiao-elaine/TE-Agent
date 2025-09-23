import os
import shutil
from pathlib import Path
import subprocess
import pytest
from test_case_manager.test_case_manager import TestCaseManager
from config.config_manager import ConfigManager  # 导入ConfigManager

REPORT_PATH = None  # 全局初始化

def clean_directory(dir_path: Path):
    """
    清理目录中的所有内容，但保留目录本身
    :param dir_path: 要清理的目录路径
    """
    if dir_path.exists() and dir_path.is_dir():
        # 遍历目录中的所有文件和子目录
        for item in dir_path.iterdir():
            try:
                if item.is_file() or item.is_symlink():
                    # 删除文件或符号链接
                    item.unlink()
                elif item.is_dir():
                    # 递归删除子目录及其内容
                    shutil.rmtree(item)
                print(f"已清理: {item}")
            except Exception as e:
                print(f"清理 {item} 失败: {str(e)}")

# pytest钩子，在命令行参数解析后立即处理报告路径
def pytest_configure(config):
    global REPORT_PATH
    config_manager = ConfigManager()
    report_path = Path(config_manager.get_report_file())
    
    # 检查是否已通过命令行指定--html
    if not config.getoption("--html"):
        REPORT_PATH = str(report_path)
        # 设置配置中的报告路径
        config.option.htmlpath = os.path.abspath(REPORT_PATH)
        config.option.self_contained_html = True
        print(f"钩子函数pytest_configure中设置报告路径: {config.option.htmlpath}")

def check_hdc_connection(remote_ip: str, hdc_port: str):
    terminal_cmd = ["hdc","list", "targets"]
    proc = subprocess.run(# 阻塞启动xterm终端，执行用例预处理和后置步骤指令
                terminal_cmd,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
                )
    if remote_ip not in proc.stdout.strip():
        hdc_cmd = ["hdc","tconn", f"{remote_ip}:{hdc_port}"]
        result = subprocess.run(# 阻塞启动xterm终端，执行用例预处理和后置步骤指令
                hdc_cmd,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
                )
        if result.stdout.strip() == "Connect OK":
            return True
        else:
            return False
    else:
        return True

@pytest.fixture(scope="session", autouse=True)
def init_test_session(request):
    """初始化测试会话"""
    try:
        config_manager = ConfigManager()
        case_manager = TestCaseManager()
        remote_ip = config_manager.get_remote_ip()
        remote_os = config_manager.get_remote_os()

        # 创建报告目录和截图目录、创建日志目录
        report_dir = Path(config_manager.get_report_file()).parent
        clean_directory(report_dir)
        
        screenshot_dir = Path(config_manager.get_screenshot_dir())
        clean_directory(screenshot_dir)

        log_dir = Path(config_manager.get_log_path())
        clean_directory(log_dir)

        report_dir.mkdir(parents=True, exist_ok=True)
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)

        # 准备用于回填测试结果的用例文档
        case_manager.get_test_case_report(
                original_word_file=config_manager.get_original_word_file(),
                new_word_file=config_manager.get_result_word_file()
            )

        print(f"测试报告将生成至: {os.path.abspath(REPORT_PATH)}")

        if remote_ip != "127.0.0.1" and remote_os == "HarmonyOS": 
            #print("开始检查远程鸿蒙系统 hdc 连接")
            hdc_port = config_manager.get_hdc_port()
            hdc_status = check_hdc_connection(remote_ip, hdc_port)
            if not hdc_status:
                #print("远程鸿蒙系统 hdc 连接失败")
                raise RuntimeError(f"远程鸿蒙系统 hdc 连接失败")
            else:
                print("远程鸿蒙系统 hdc 连接成功")
        yield # 执行用例

        print(f"\n测试完成，结果已填充到 {config_manager.get_result_word_file()}")
        if REPORT_PATH and Path(REPORT_PATH).exists:
            print(f"HTML测试报告已生成: {os.path.abspath(REPORT_PATH)}")
        elif REPORT_PATH:
            print(f"警告: HTML测试报告文件不存在 - {os.path.abspath(REPORT_PATH)}")

    except Exception as e:
        print(f"初始化测试会话失败: {str(e)}")
        raise
