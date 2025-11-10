import os
import shutil
from pathlib import Path
import subprocess
import pytest
import time
from test_case_manager.test_case_manager import TestCaseManager
from config.config_manager import ConfigManager  # 导入ConfigManager

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


# pytest钩子，在命令行参数解析后立即处理报告路径
def pytest_configure(config):
    config_manager = ConfigManager()
    report_path = Path(config_manager.get_report_file())
    
    # 检查是否已通过命令行指定--html
    cli_html_path = config.getoption("--html")
    if not cli_html_path:  # 仅当命令行未指定时，使用配置文件中的默认路径
        os.environ["REPORT_PATH"] = str(report_path)
        config.option.htmlpath = os.path.abspath(str(report_path)) # 设置配置中的报告路径
        config.option.self_contained_html = True
        config.option.html_show_all_errors = True
        print(f"钩子函数pytest_configure中设置报告路径: {config.option.htmlpath}")
    else:
        os.environ["REPORT_PATH"] = cli_html_path
        print(f"使用命令行指定的报告路径: {os.path.abspath(cli_html_path)}")
    report_path = os.getenv("REPORT_PATH", "")
    report_dir = Path(report_path).parent
    clean_directory(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(report_dir, 0o755)  # 添加写入权限

    # 处理 Allure 结果路径
    default_allure_path = Path(config_manager.get_allure_results_path())  
    # 1. 读取命令行传入的 --alluredir 参数
    cli_allure_path = config.getoption("--alluredir")
    if not cli_allure_path: # 确定最终的 Allure 路径（命令行优先，否则用配置文件默认值）
        allure_path = default_allure_path
        os.environ["ALLURE_RESULTS_PATH"] = str(allure_path)
        config.option.alluredir = os.path.abspath(str(allure_path)) # 设置 config.yaml 配置中的 alluredir（同步给 allure-pytest 插件）
        print(f"钩子函数pytest_configure中设置 Allure 结果路径: {config.option.alluredir}")
    else:
        allure_path = Path(cli_allure_path)
        os.environ["ALLURE_RESULTS_PATH"] = cli_allure_path
        print(f"使用命令行指定的 Allure 结果路径: {os.path.abspath(cli_allure_path)}")
    # 确保 Allure 目录存在（关键：避免文件写入失败）
    if not allure_path.exists():
        allure_path.mkdir(parents=True, exist_ok=True)


# pytest钩子，强制先执行 batch1 标记的用例
def pytest_collection_modifyitems(items):
    # 分离batch1和batch2的用例
    batch1_items = [item for item in items if item.get_closest_marker("batch1")]
    batch2_items = [item for item in items if item.get_closest_marker("batch2")]
    # 重新排序：先batch1，后batch2
    items[:] = batch1_items + batch2_items


@pytest.fixture(scope="session", autouse=True)
def init_test_session(request):
    """初始化测试会话"""
    try:
        config_manager = ConfigManager()
        case_manager = TestCaseManager()
        remote_ip = config_manager.get_remote_ip()
        remote_os = config_manager.get_remote_os()
        env_DISPLAY = config_manager.get_env_DISPLAY()

        # 创建报告目录和截图目录、创建日志目录
        '''
        report_path = os.getenv("REPORT_PATH", "")
        if report_path:
            report_dir = Path(report_path).parent
        else:
            report_dir = Path(config_manager.get_report_file()).parent
        clean_directory(report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(report_dir, 0o755)  # 添加写入权限
        '''
        screenshot_dir = Path(config_manager.get_screenshot_dir())
        clean_directory(screenshot_dir)

        log_dir = Path(config_manager.get_log_path())
        clean_directory(log_dir)
        
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        subprocess.run( f'export DISPLAY="{env_DISPLAY}"', shell=True, check=True)

        # 准备用于回填测试结果的用例文档
        case_manager.get_test_case_report(
                original_word_file=config_manager.get_original_word_file(),
                new_word_file=config_manager.get_result_word_file()
            )

        report_path = os.getenv("REPORT_PATH", "")
        print(f"测试报告将生成至: {os.path.abspath(report_path)}")

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

        # pytest-html 插件在 pytest 会话完全结束后才会写入最终的报告文件，即使在yield 之后验证报告生成（用例执行完成后），但 pytest 可能仍在后台处理报告写入
    except Exception as e:
        print(f"初始化测试会话失败: {str(e)}")
        raise

