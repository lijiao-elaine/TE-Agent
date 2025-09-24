import streamlit as st
import subprocess
import os
import tempfile
from pathlib import Path
from datetime import datetime
from uuid import uuid4
import re

# ---------------- 页面设置 ----------------
st.set_page_config(page_title="测试用例自动化执行", layout="wide")
st.title("🧪 测试用例自动化执行工具")
st.divider()

# ---------------- 初始化状态 ----------------
def default_test_state():
    return {
        "test_type": "single_case",  # 默认执行单个用例
        "test_results": [],
        "current_run": None,
        "logs": "",
        "selected_case": "test_cases/module_1/XXX_TEST_002.json",
        "selected_module": "test_cases/module_1",
        "report_path": "reports/test_report.html",
        "word_report_path": "reports/test_report.docx"
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
        "report_path": "",  # 存储报告路径
        "word_report_path": ""
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

# 测试类型映射字典
test_type_map = {
    'single_case': '执行单个用例',
    'module_case': '执行单个模块用例',
    'full_case': '执行全量用例'
}

# ---------------- 侧边栏 ----------------
with st.sidebar:
    # 第一部分：测试历史
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
            #st.divider()
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

    # 分隔线
    st.divider()
    
    # 第二部分：新建测试会话
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
        # 不需要rerun，保持当前页面状态

# ---------------- 主区域 ----------------
# 获取当前会话
current_session = get_test_session(st.session_state.selected_test_id)

# 第一部分：工具介绍
st.subheader("工具介绍")
st.markdown("""
这是一个测试用例自动化执行工具，支持三种测试模式：
- **执行单个用例**：指定单个测试用例文件路径，仅执行该用例
- **执行单个模块用例**：指定模块目录，执行该目录下所有用例
- **执行全量用例**：不指定具体范围，执行test_cases目录下所有测试用例

工具会记录每次测试会话的执行结果，包括执行日志、测试结果统计和生成的报告，方便您跟踪测试历史和结果对比。
""")
st.divider()

# 第二部分：测试配置和执行（只有在有当前会话时显示）
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
                placeholder="如：test_cases/test_case_1.json",
                value=st.session_state.test_state["selected_case"],
                disabled=current_session["status"] != "未开始"  # 非未开始状态禁用编辑
            )
            st.session_state.test_state["selected_case"] = test_case
        
        elif test_type == "module_case":
            st.info("配置模块测试用例的执行参数")
            module_path = st.text_input(
                "模块目录",
                placeholder="如：test_cases/module_1",
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

    # 执行控制区域 - 只有未开始的会话才显示执行按钮
    st.divider()
    live_area = st.container()

    # 只有当会话状态为"未开始"时才显示执行按钮
    if current_session["status"] == "未开始":
        if st.button("▶️ 开始执行测试", use_container_width=True):
            # 验证输入
            valid = True
            if test_type == "single_case" and test_case and not Path(test_case).exists():
                st.error(f"测试用例文件不存在: {test_case}")
                valid = False
            if test_type == "module_case" and module_path and not Path(module_path).exists():
                st.error(f"模块目录不存在: {module_path}")
                valid = False
            
            if valid:
                # 更新会话状态
                current_session["status"] = "执行中"
                current_session["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                current_session["test_type"] = test_type
                current_session["report_path"] = report_path  # 保存报告路径
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
                    st.info(f"正在执行命令: {cmd_str}")
                    log_area = st.empty()
                    
                    # 执行测试
                    output, return_code = run_test_command(cmd_str)
                    
                    # 更新日志
                    current_session["logs"] = output
                    log_area.text_area("执行日志", output, height=300)
                    
                    # 解析结果
                    current_session["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    current_session["status"] = "成功" if return_code == 0 else "失败"
                    
                    # 提取用例信息
                    if "用例执行完成" in output:
                        case_name = re.search(r"用例 '(.+?)' 执行完成", output).group(1)
                        result = re.search(r"最终结果: (.+)", output).group(1)
                        current_session["cases"] = [case_name]
                        current_session["results"][case_name] = result
                    elif "共找到" in output and "个用例" in output:
                        # 解析模块或全量测试的用例数量
                        case_count = re.search(r"共找到 (\d+) 个用例", output).group(1)
                        current_session["cases"] = [f"模块用例 {i+1}" for i in range(int(case_count))]
                        # 这里简化处理，实际应根据输出解析每个用例结果
                
                st.success("测试执行完成！")
                st.rerun()

    # 显示当前会话日志
    if current_session["logs"]:
        st.divider()
        st.subheader("📋 执行日志")
        st.text_area("", current_session["logs"], height=300)

    # 结果展示区域
    if current_session["cases"]:
        st.divider()
        st.subheader("测试结果")
        for case, result in current_session["results"].items():
            status_color = "green" if result == "通过" else "red"
            st.markdown(f"**{case}**: <span style='color:{status_color}'>{result}</span>", unsafe_allow_html=True)

    # 报告下载区域 - 只有测试完成且报告存在时显示
    report_path = current_session.get("report_path", "")
    if current_session["status"] in ["成功", "失败"] and report_path and Path(report_path).exists():
        st.divider()
        with open(report_path, "rb") as f:
            st.download_button(
                label="📥 下载HTML测试报告",
                data=f,
                file_name=Path(report_path).name,
                mime="text/html"
            )
    word_report_path = current_session.get("word_report_path", "")
    if current_session["status"] in ["成功", "失败"] and word_report_path and Path(word_report_path).exists():
        #st.divider()
        with open(word_report_path, "rb") as f:
            st.download_button(
                label="📥 下载Word测试报告",
                data=f,
                file_name=Path(word_report_path).name,
                mime="docx"
            )
else:
    # 如果没有会话，提示创建新会话
    st.info("请在左侧创建新的测试会话开始测试")
