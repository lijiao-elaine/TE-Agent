import streamlit as st
import subprocess
import os
from pathlib import Path
from datetime import datetime
from uuid import uuid4
import re
import yaml

# ---------------- 页面设置 ----------------
st.set_page_config(page_title="测试用例自动化执行", layout="wide")
st.title("🧪 测试用例自动化执行工具")
st.divider()

# ---------------- 初始化状态 ----------------
def default_test_state():
    return {
        "active_tab": "test_session",  # 默认激活测试会话标签
        "test_type": "single_case",
        "test_results": [],
        "current_run": None,
        "logs": "",
        "selected_case": "test_cases/unit_test/module_1/XXX_TEST_002.json",
        "selected_module": "test_cases/unit_test/module_1",
        "report_path": "reports/test_report.html",  # HTML报告路径
        "word_report_path": "reports/test_report.docx",  # Word报告路径
        "config_content": ""
    }

# 会话列表：存储测试执行历史
if "test_sessions" not in st.session_state:
    st.session_state.test_sessions = []

# 当前选中会话 id
if "selected_test_id" not in st.session_state:
    st.session_state.selected_test_id = None

# 测试状态
if "test_state" not in st.session_state:
    st.session_state.test_state = default_test_state()

# 配置文件路径
CONFIG_PATH = Path("config/config.yaml")

# ---------------- 辅助函数 ----------------
def get_test_session(tid):
    if tid is None:
        return None
    for s in st.session_state.test_sessions:
        if s["id"] == tid:
            return s
    return None

def new_test_session(title=None):
    session = {
        "id": str(uuid4()),
        "title": title or f"测试会话 {datetime.now().strftime('%m-%d %H:%M')}",
        "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": None,
        "status": "未开始",
        "test_type": st.session_state.test_state["test_type"],
        "cases": [],
        "results": {},
        "logs": "",
        "report_path": st.session_state.test_state["report_path"],  # 关联默认HTML报告路径
        "word_report_path": st.session_state.test_state["word_report_path"]  # 关联默认Word报告路径
    }
    st.session_state.test_sessions.insert(0, session)
    st.session_state.selected_test_id = session["id"]
    return session

def run_test_command(command):
    """执行测试命令并返回输出"""
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True
        )
        return result.stdout, result.returncode
    except Exception as e:
        return f"执行命令时出错: {str(e)}", 1

def load_config_file():
    """加载配置文件原始内容（保留双引号、空行和原始格式）"""
    if not CONFIG_PATH.exists():
        # 如果配置文件不存在，创建默认配置（保留双引号，包含新增参数）
        default_config = '''test_env: "dev"
timeout: 30
retry_count: 1
log_level: "info"

# 执行环境配置
execute_machine:
  remote_ip: "127.0.0.1"
  remote_os: "ubuntu"
  remote_user: "root"
  remote_passwd: "Mind@123"
  hdc_port: "5555"

# 系统环境变量
env:
  DISPLAY: ":0"

# 脚本路径配置
script:
  full_process_script: "/home/lijiao/work/TE-Agent/sample/full_process_start.sh"
  stop_full_process_script: "/home/lijiao/work/TE-Agent/sample/full_process_stop.sh"

report:
  enable: true
  include_screenshots: false
'''
        # 创建config目录
        CONFIG_PATH.parent.mkdir(exist_ok=True)
        # 保存默认配置（按原始字符串保存）
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(default_config)
        return default_config
    
    # 读取现有配置文件原始内容（不格式化，保留所有原始字符）
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except Exception as e:
        st.error(f"加载配置文件失败: {str(e)}")
        return f"# 配置文件解析错误\n{str(e)}"

def save_config_file(content):
    """保存配置文件内容（保留用户输入的原始格式）"""
    try:
        # 仅验证YAML语法有效性，不修改格式
        yaml.safe_load(content)
        # 按原始内容保存文件
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        return True, "配置保存成功！"
    except Exception as e:
        return False, f"配置保存失败: {str(e)}"

# 测试类型映射字典
test_type_map = {
    'single_case': '执行单个用例',
    'module_case': '执行单个模块用例',
    'full_case': '执行全量用例'
}

# ---------------- 侧边栏 ----------------
with st.sidebar:
    # 导航菜单
    st.header("功能导航")
    nav_option = st.radio(
        "选择功能",
        ["test_session", "config_management"],
        format_func=lambda x: "测试会话管理" if x == "test_session" else "配置文件管理",
        key="nav_radio"
    )
    st.session_state.test_state["active_tab"] = nav_option
    
    st.divider()

    # 根据选中的导航项显示不同内容
    if nav_option == "test_session":
        # 测试历史
        st.header("测试历史")
        if st.session_state.test_sessions:
            ids = [s["id"] for s in st.session_state.test_sessions]
            default_idx = ids.index(st.session_state.selected_test_id) if st.session_state.selected_test_id in ids else 0
            chosen_id = st.radio(
                "选择测试会话",
                options=ids,
                index=default_idx,
                format_func=lambda tid: get_test_session(tid)["title"],
                key="test_session_radio",
            )
            st.session_state.selected_test_id = chosen_id
            
            # 显示当前会话信息
            session = get_test_session(chosen_id)
            if session:
                st.caption(f"开始时间: {session['start_time']}")
                st.caption(f"测试类型: {test_type_map.get(session['test_type'], '未知')}")
                st.caption(f"状态: {session['status']}")
                if session['end_time']:
                    st.caption(f"结束时间: {session['end_time']}")
                
                # 统计信息
                total = len(session['cases'])
                passed = sum(1 for res in session['results'].values() if res == "通过")
                failed = total - passed
                st.caption(f"用例总数: {total}")
                st.caption(f"通过: {passed}")
                st.caption(f"失败: {failed}")
        else:
            st.info("暂无测试记录（创建并执行测试后将显示）")

        st.divider()
        
        # 新建测试会话
        st.header("新建测试会话")
        test_type = st.radio(
            "选择测试类型",
            options=["single_case", "module_case", "full_case"],
            format_func=lambda x: test_type_map[x],
            key="test_type_selector"
        )
        st.session_state.test_state["test_type"] = test_type
        
        if st.button("创建新会话", use_container_width=True):
            new_test_session()
            # 确保激活测试会话标签
            st.session_state.test_state["active_tab"] = "test_session"

    else:  # config_management
        st.header("配置文件管理")
        st.info("在此处可以查看、修改、刷新工具配置参数")
        st.caption("配置文件路径: config/config.yaml")
        
        # 快速操作按钮
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📝 编辑配置", use_container_width=True):
                # 确保配置内容已加载
                if not st.session_state.test_state["config_content"]:
                    st.session_state.test_state["config_content"] = load_config_file()
        
        with col2:
            if st.button("🔄 刷新配置", use_container_width=True):
                st.session_state.test_state["config_content"] = load_config_file()
                st.success("已加载刷新为当前config/config.yaml配置文件的最新内容")

# ---------------- 主区域 ----------------
current_session = get_test_session(st.session_state.selected_test_id)
active_tab = st.session_state.test_state["active_tab"]

# 配置文件管理界面
if active_tab == "config_management":
    st.subheader("⚙️ 配置文件管理")
    st.markdown("编辑 `config/config.yaml` 配置文件，先查看参数说明再修改，修改后点击保存按钮生效；点击刷新配置按钮即可加载config/config.yaml配置文件的最新内容")

    # 配置参数说明
    with st.expander("📚 需要修改的主要配置参数说明", expanded=True):
        st.markdown("""
        | 参数路径 | 说明 | 示例值 | 备注 |
        |----------|------|--------|------|
        | execute_machine.remote_ip | 用例执行环境IP地址 | "127.0.0.1"/"192.168.137.100" | 本地执行用例填127.0.0.1；远程执行用例就填远程执行机的IP |
        | execute_machine.remote_os | 用例执行环境OS类型 | "HarmonyOS"/"ubuntu" | 本地或远程执行用例的机器的操作系统类型 |
        | execute_machine.remote_user | 用例执行环境的登录用户名 | "root" | 登录执行环境的用户名（字符串类型需加双引号） |
        | execute_machine.remote_passwd | 用例执行环境的登录密码 | "Mind@123" | 登录执行环境的密码（字符串类型需加双引号） |
        | execute_machine.hdc_port | 鸿蒙系统用例执行环境的hdc端口 | "5555" | 仅鸿蒙系统需要配置，其他系统可忽略 |
        | env.DISPLAY | X服务器的图形界面环境变量 | ":0"/":1" | Linux系统图形界面配置 |
        | script.full_process_script | 全流程启动脚本路径 | "/home/lijiao/work/TE-Agent/sample/full_process_start.sh" | 启动全流程脚本的绝对路径（需确保文件存在） |
        | script.stop_full_process_script | 全流程停止脚本路径 | "/home/lijiao/work/TE-Agent/sample/full_process_stop.sh" | 停止全流程脚本的绝对路径（需确保文件存在） |
        """)

    # 配置内容编辑区
    st.markdown("### 配置内容 (YAML格式)")
    # 确保配置内容已加载
    if not st.session_state.test_state["config_content"]:
        st.session_state.test_state["config_content"] = load_config_file()
    
    config_content = st.text_area(
        "",
        value=st.session_state.test_state["config_content"],
        height=300,
        key="config_editor",
        help="支持保留双引号、空行等原始格式，遵循YAML语法即可"
    )
    st.session_state.test_state["config_content"] = config_content

    # 操作按钮
    btn_cols = st.columns([1, 1, 6])
    with btn_cols[0]:
        save_btn = st.button("💾 保存配置", use_container_width=True)
    with btn_cols[1]:
        reset_btn = st.button("🔄 刷新配置", use_container_width=True)

    # 按钮点击事件处理
    if save_btn:
        success, msg = save_config_file(config_content)
        if success:
            st.success(msg, icon="✅")
        else:
            st.error(msg, icon="❌")

    if reset_btn:
        st.session_state.test_state["config_content"] = load_config_file()
        st.info("已加载刷新为当前config/config.yaml配置文件的最新内容", icon="ℹ️")

# 测试会话管理界面
else:
    # 工具介绍
    st.subheader("工具介绍")
    st.markdown("""
    这是一个测试用例自动化执行工具，当前仅支持在单台执行机执行用例，支持在本地、远程鸿蒙设备、远程非鸿蒙linux设备执行用例，同时支持三种测试模式：
    - **执行单个用例**：指定单个测试用例文件路径，仅执行该用例
    - **执行单个模块用例**：指定模块目录，执行该目录下所有用例
    - **执行全量用例**：不指定具体范围，执行test_cases或test_cases_ohos目录下所有测试用例

    工具会记录每次测试会话的执行结果，包括执行日志、执行过程截图、测试结果统计和生成的报告（包含html和word两种格式），方便跟踪测试历史和结果对比。
    """)
    st.divider()

    # 测试配置和执行（只有在有当前会话时显示）
    if current_session:
        st.subheader(f"当前会话: {current_session['title']}")

        # 根据选择的测试类型显示不同的配置项
        with st.expander("🔧 测试配置", expanded=True):
            test_type = st.session_state.test_state["test_type"] if current_session["status"] == "未开始" else current_session["test_type"]
            test_case = ""
            module_path = ""
            report_path = ""
            word_report_path = ""
            
            if test_type == "single_case":
                st.info("配置单个测试用例的执行参数")
                test_case = st.text_input(
                    "单个测试用例路径",
                    placeholder="如：test_cases/unit_test/test_case_1.json",
                    value=st.session_state.test_state["selected_case"],
                    disabled=current_session["status"] != "未开始"
                )
                st.session_state.test_state["selected_case"] = test_case
            
            elif test_type == "module_case":
                st.info("配置模块测试用例的执行参数")
                module_path = st.text_input(
                    "模块目录",
                    placeholder="如：test_cases/unit_test/module_1",
                    value=st.session_state.test_state["selected_module"],
                    disabled=current_session["status"] != "未开始"
                )
                st.session_state.test_state["selected_module"] = module_path
            
            else:  # full_case
                st.info("将执行全量测试用例")
            
            # 报告路径配置（所有类型通用）
            report_path = st.text_input(
                "HTML报告路径",
                placeholder="默认：reports/test_report.html",
                value=st.session_state.test_state["report_path"],
                disabled=current_session["status"] != "未开始"
            )
            st.session_state.test_state["report_path"] = report_path

            word_report_path = st.text_input(
                "Word报告路径",
                placeholder="默认：reports/test_report.docx",
                value=st.session_state.test_state["word_report_path"],
                disabled=current_session["status"] != "未开始"
            )
            st.session_state.test_state["word_report_path"] = word_report_path

        # 执行控制区域
        st.divider()
        live_area = st.container()
        
        # 执行按钮和下载按钮容器
        execute_container = st.container()
        download_container = st.container()

        # 执行按钮逻辑
        with execute_container:
            if current_session["status"] == "未开始":
                if st.button("▶️ 开始执行测试", use_container_width=True):
                    # 验证输入
                    valid = True
                    if test_type == "single_case" and test_case and not Path(test_case).exists():
                        st.error(f"测试用例文件不存在: {test_case}", icon="❌")
                        valid = False
                    if test_type == "module_case" and module_path and not Path(module_path).exists():
                        st.error(f"模块目录不存在: {module_path}", icon="❌")
                        valid = False
                    
                    if valid:
                        # 更新会话状态
                        current_session["status"] = "执行中"
                        current_session["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        current_session["test_type"] = test_type
                        current_session["report_path"] = report_path
                        current_session["word_report_path"] = word_report_path
                        current_session["logs"] = ""
                        
                        # 构建命令
                        cmd = ["python3", "main.py"]
                        if test_type == "single_case" and test_case:
                            cmd.extend(["-t", test_case])
                        if test_type == "module_case" and module_path:
                            cmd.extend(["-m", module_path])
                        if report_path:
                            cmd.extend(["-r", report_path])
                        cmd_str = " ".join(cmd)
                        
                        # 显示执行信息
                        with live_area:
                            st.info(f"正在执行命令: {cmd_str}", icon="ℹ️")
                            log_area = st.empty()
                            
                            # 执行测试
                            output, return_code = run_test_command(cmd_str)
                            
                            # 更新日志
                            current_session["logs"] = output
                            log_area.text_area("执行日志", output, height=300)
                            
                            # 更新会话状态为完成
                            current_session["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            current_session["status"] = "成功" if return_code == 0 else "失败"
                            
                            # 刷新页面以显示下载按钮
                            st.rerun()

        # 下载按钮逻辑（在执行按钮下方）
        with download_container:
            # 仅当测试执行完成（成功或失败）且报告路径存在时显示下载按钮
            if current_session["status"] in ["成功", "失败"]:
                # 获取default_test_state中定义的报告路径
                html_path = Path(st.session_state.test_state["report_path"])
                word_path = Path(st.session_state.test_state["word_report_path"])
                
                # 显示HTML报告下载按钮
                if html_path.exists():
                    with open(html_path, "rb") as f:
                        st.download_button(
                            label="📄 下载HTML报告",
                            data=f,
                            file_name=html_path.name,
                            mime="text/html",
                            use_container_width=True
                        )
                else:
                    st.button(
                        "📄 下载HTML报告（文件不存在）",
                        disabled=True,
                        use_container_width=True
                    )
                
                # 显示Word报告下载按钮
                if word_path.exists():
                    with open(word_path, "rb") as f:
                        st.download_button(
                            label="📝 下载Word报告",
                            data=f,
                            file_name=word_path.name,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True
                        )
                else:
                    st.button(
                        "📝 下载Word报告（文件不存在）",
                        disabled=True,
                        use_container_width=True
                    )

        # 显示日志（如果有）
        if current_session["logs"]:
            st.divider()
            st.subheader("📋 执行日志")
            st.text_area("", current_session["logs"], height=300)