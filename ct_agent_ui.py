import streamlit as st
from pathlib import Path
from datetime import datetime
from streamlit.delta_generator import DeltaGenerator
import subprocess
import re
import yaml

def render_editable_file(st, file_path: Path, editor_key: str):
    #文件编辑
    state = st.session_state

    original_text = file_path.read_text()

    shadow_key  = editor_key + "_shadow"    # 编辑区域
    hist_key    = editor_key + "_history"   # 历史记录
    action_key  = editor_key + "_action"    # 动作记录
    initial_key = editor_key + "_initial"   # 源码

    # 初始化
    if initial_key not in state:
        state[initial_key] = original_text

    if shadow_key not in state:
        state[shadow_key] = state[initial_key]

    if hist_key not in state:
        state[hist_key] = [state[initial_key]]

    if action_key not in state:
        state[action_key] = None

    action = state[action_key]

    # 保存
    if action == "save":
        new_content = state.get(shadow_key, state[initial_key])
        file_path.write_text(new_content)
        state[shadow_key] = new_content
        state[hist_key].append(new_content)
        state[action_key] = None
        st.rerun()

    # 撤销
    elif action == "undo":
        hist = state[hist_key]
        if len(hist) > 1:
            hist.pop()
            state[shadow_key] = hist[-1]
        state[action_key] = None
        st.rerun()

    # 重置
    elif action == "reset":
        state[shadow_key] = state[initial_key]
        state[hist_key]   = [state[initial_key]]
        state[action_key] = None
        st.rerun()

    st.text_area(
        "文件内容（可编辑）",
        height=300,
        key=shadow_key
    )


    c1, c2, c3 = st.columns([1,1,1])
    if c1.button("💾 保存", key=f"{editor_key}_save"):
        state[action_key] = "save"
        st.rerun()

    if c2.button("↩️ 撤销", key=f"{editor_key}_undo"):
        state[action_key] = "undo"
        st.rerun()

    if c3.button("🗑 重置", key=f"{editor_key}_reset"):
        state[action_key] = "reset"
        st.rerun()

# 去乱码
ansi_escape = re.compile(r'''
    \x1B    # ESC
    (?:     # 7-bit C1 Fe (Esc [ ...)
        \[ [0-?]* [ -/]* [@-~]
    )
''', re.VERBOSE)

def _clean_ansi(text):
    return ansi_escape.sub('', text)

def _run_cmd_full(cmd):
    """一次性执行命令，返回完整日志"""
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True
        )
        return _clean_ansi(result.stdout), result.returncode
    except Exception as e:
        return str(e), 1


def scan_new_generated_dirs(output_dir: Path, before_dirs: set):
    """对比执行前后的目录，得到新增的文件夹列表"""
    after_dirs = set(d for d in output_dir.iterdir() if d.is_dir())
    new_dirs = sorted(after_dirs - before_dirs)
    return new_dirs


def analyze_generated_folder(folder: Path):
    """对一个生成的目录查找 CMakeLists 和 CPP 文件）"""
    cmake_list = list(folder.glob("CMakeLists.txt"))
    cmake = cmake_list[0] if cmake_list else None
    cpp_files = list(folder.glob("*.cpp"))

    return cmake, cpp_files


# 读取配置文件
def load_config_from_yaml(config_file="config/config_ct_agent.yml"):
    """加载指定路径的 YAML 配置文件"""
    try:
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        st.error(f"无法读取配置文件 {config_file}: {e}")
        return {}

# 初始化 ct_state，将配置文件中的值作为默认值
def default_ct_state(config_data):
    return {
        "input-file-path": config_data.get("input-file-path", ""),
        "project-_dir": config_data.get("project-dir", ""),
        "config": config_data.get("config", ""),
        "model-type": config_data.get("model-type", ""),
        "model-name": config_data.get("model-name", ""),
        "api-url": config_data.get("api-url", ""),
        "debug-level": config_data.get("debug-level", ""),
        "output-dir": config_data.get("output-dir", ""),
        "requirement": config_data.get("requirement", ""),
        "compile-mode": config_data.get("compile-mode", "source"),
        "input-function": config_data.get("input-function", ""),
        "token-count": config_data.get("token-count", None),
        "max-iterations": config_data.get("max-iterations", None),
        "backend": config_data.get("backend", False)
    }

def render_ct_agent_ui(st: DeltaGenerator, g):
    # 从配置文件中加载配置
    config_data = load_config_from_yaml("config/config_ct_agent.yml")

    if "ct_sessions" not in st.session_state:
        st.session_state.ct_sessions = []

    if "selected_ct_id" not in st.session_state:
        st.session_state.selected_ct_id = None

    if "ct_state" not in st.session_state:
        st.session_state.ct_state = default_ct_state(config_data)
    ct_state = st.session_state.ct_state  # 当前 CT-Agent 的表单参数
    ct_sessions = st.session_state.ct_sessions  # 多个会话列表
    selected_ct_id = st.session_state.selected_ct_id  # 当前选中的会话 ID
    # 当前会话获取
    current_session = next(
        (s for s in ct_sessions if s["id"] == selected_ct_id), None
    )

    st.subheader("⚙️ CT-Agent 单元测试生成工具")

    if not current_session:
        st.info("请在左侧点击 **创建新的 CT-Agent 会话**")
        return

    st.caption(f"当前会话：{current_session['title']} | 状态：{current_session['status']}")

    st.divider()
    st.subheader("🔧 参数配置")
    
    # 用户输入其他必要的参数
    ct_state["input-file-path"] = st.text_input(
        "被测文件路径",
        ct_state.get("input-file-path", "")
    )
    ct_state["project-dir"] = st.text_input(
        "被测函数相关联代码所在目录",
        ct_state.get("project-dir", "")
    )

    if "compile_mode" not in st.session_state:
        st.session_state.compile_mode = "source"

    options = ["source", "link"]
    descriptions = {
        "source": "基于被测函数相关源代码的编译方式：单元测试用例与被测函数所在工程下的相关代码一起编译为一个可执行程序",
        "link": "基于动态链接被测函数所在库的编译方式：被测代码已被编译为动态链接库，单元测试用例将链接到相应动态链接库"
    }

    # 创建包含说明的选项标签
    option_labels = {
        "source": f"source - {descriptions['source']}",
        "link": f"link - {descriptions['link']}"
    }

    current_index = options.index(st.session_state.compile_mode)
    selected_compile_mode = st.radio(
        "编译方式", 
        options=options,
        format_func=lambda x: option_labels[x],
        index=current_index
    )
    if selected_compile_mode != st.session_state.compile_mode:
        st.session_state.compile_mode = selected_compile_mode
        st.rerun()

    ct_state["input-function"] = st.text_input(
        "被测函数列表",
        ct_state.get("input-function", "")
    )

    ct_state["max-iterations"] = st.text_input(
        "最大迭代次数（该参数用于定义智能体迭代优化的次数，输入是一个阿拉伯数字）",
        ct_state.get("max-iterations", "")
    )

    st.divider()

    # 加载配置文件中的默认值
    ct_state["config"] = config_data.get("config", "")
    ct_state["model-type"] = config_data.get("model-type", "")
    ct_state["model-name"] = config_data.get("model-name", "")
    ct_state["api-url"] = config_data.get("api-url", "")
    ct_state["debug-level"] = config_data.get("debug-level", "")
    ct_state["output-dir"] = config_data.get("output-dir", "")
    ct_state["requirement"] = config_data.get("requirement", "")
    ct_state["token-count"] = config_data.get("token-count", None)
    ct_state["backend"] = config_data.get("backend", None)

    st.markdown("""
    ### 说明：
    - 被测函数相关联代码所在目录指与被测函数相关的上下文代码（如函数所在类定义、调用者函数等）所在的目录。为了确保单元测试用例生成质量，建议将被测函数所在项目工程目录作为被测函数相关联代码所在目录。
    - 被测函数列表支持填写被测文件中的多个函数名（使用逗号“,”分隔），本功能会针对列表中的每个函数逐个生成单元测试工程。
    - 最大迭代次数指分析-生成代码-编译代码与执行程序-收集报告并分析的迭代次数，本功能会按照上述描述对测试用例进行迭代优化，考虑到迭代优化的边际效应，建议不超过5次。
    - 如果需要修改完整参数信息，请在config/config_ct_agent.yml中进行修改。    
    """)
        # 运行按钮
    if st.button("▶️ 开始生成单元测试", use_container_width=True):
        if not ct_state["input-file-path"] or not ct_state["project-dir"]:
            st.error("❌ input-file-path 和 project-dir 为必填参数")
            return

        # 记录执行前目录快照
        od = Path(ct_state["output-dir"])
        before_dirs = set(d for d in od.iterdir() if d.is_dir())
        current_session["before_dirs"] = before_dirs

        # 构造命令
        main_path = config_data.get("main-path", "") 
        cmd = ["python3", main_path]

        # 遍历ct_state，拼接命令行参数
        for key, value in ct_state.items():
            if value:  # 只添加非空值的参数
                cmd.append(f"--{key.replace('_', '-')}") 
                cmd.append(str(value))

        # 将命令拼接成一个完整的字符串
        cmd_str = " ".join(cmd)
        st.info(f"正在执行命令：\n`{cmd_str}`")

        # 执行命令
        out, code = _run_cmd_full(cmd_str)
        current_session["logs"] = out
        current_session["status"] = "成功" if code == 0 else "失败"
        current_session["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        new_dirs = scan_new_generated_dirs(od, before_dirs)
        folder_info_list = []

        for d in new_dirs:
            cmake, cpp_files = analyze_generated_folder(d)
            folder_info_list.append({
                "folder": str(d),
                "cmake": str(cmake) if cmake else None,
                "cpps": [str(c) for c in cpp_files],
            })

        current_session["generated_folders"] = folder_info_list

        # 更新 session
        for i, s in enumerate(st.session_state.ct_sessions):
            if s["id"] == selected_ct_id:
                st.session_state.ct_sessions[i] = current_session
                break
        st.session_state.ct_sessions = st.session_state.ct_sessions
        #import pdb;pdb.set_trace()
        st.success("执行完成，请查看生成内容👇")
    
    # 展示生成的文件夹和编辑入口
    if "generated_folders" in current_session:
        folders = current_session["generated_folders"]
        if folders:
            st.subheader("📁 本次生成的文件夹")
            for idx, item in enumerate(folders):
                folder_path = item["folder"]
                state_key = f"folder_open_{idx}"

                # 初始化状态
                if state_key not in st.session_state:
                    st.session_state[state_key] = False

                is_open = st.session_state[state_key]
                folder_name = folder_path
                button_label = f"{'📂 收起' if is_open else '📁 打开'} {folder_name}"

                if st.button(button_label, key=f"folder_btn_{idx}"):
                    st.session_state[state_key] = not is_open
                    st.rerun()

                # 根据状态显示或隐藏内容
                if st.session_state[state_key]:
                    st.write(f"### 📂 {folder_path}")
                    # CMakeLists
                    if item["cmake"]:
                        st.subheader("🛠️ CMakeLists.txt（可编辑）")
                        render_editable_file(
                            st,
                            Path(item["cmake"]),
                            editor_key=f"cmake_editor_{idx}"
                        )
                    else:
                        st.info("没有找到 CMakeLists.txt")
                    # CPP
                    if item["cpps"]:
                        st.subheader("📝 C++ 测试文件（可编辑）")
                        for file_i, cpp in enumerate(item["cpps"]):
                            st.markdown(f"#### `{cpp}`")
                            render_editable_file(
                                st,
                                Path(cpp),
                                editor_key=f"cpp_editor_{idx}_{file_i}"
                            )
                    else:
                        st.info("没有找到 cpp 文件")

    if current_session.get("logs"):
        st.subheader("📋 执行日志")
        st.text_area(
            "执行日志",
            current_session["logs"],
            height=300,
            label_visibility="collapsed"
        )
