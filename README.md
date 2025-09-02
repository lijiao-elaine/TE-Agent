# TE-Agent

TE-Agent是根据测试细则文档执行测试用例，并生成填入了测试结果的测试细则文档的智能体框架。

## 项目简介

TE-Agent是一个基于LangGraph构建的智能体框架，能够自动分析C++单元测试代码，编译运行测试，并生成详细的测试用例文档。该智能体通过大模型分析代码功能，执行测试验证，最终生成标准化的测试文档。

## 功能特性

- 🔍 **智能分析word文档**: 使用大模型分析测试细则文档中每个用例的执行步骤和期望结果
- 🏗️ **自动运行并填入结果**: 自动执行测试用例并填入结果
- 📝 **文档自动生成**: 基于模板生成标准化的、填入了测试执行结果的测试用例文档
- 🔄 **工作流管理**: 基于LangGraph的可靠工作流管理
- 🎯 **错误处理**: 完善的错误处理和日志记录机制
- ⚙️ **配置管理**: 灵活的配置文件管理，支持多种参数配置

## 系统要求

- Python 3.10+
- CMake 3.10+
- C++编译器 (GCC/Clang)
- OpenAI API密钥

## 安装指南

### 1. 克隆项目

```bash
git clone <repository-url>
cd TE-Agent
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
sudo apt install xterm
sudo apt install x11-utils ##xwininfo、xprop等工具
sudo apt install x11-apps  # 包含xwd工具
sudo apt install netpbm -y #安装pnmtopng
sudo apt install xdotool # 安装窗口控制工具
sudo apt install wmctrl
```

### 3. 配置系统参数

项目使用YAML配置文件管理各种参数。默认配置文件位于 `config/config.yaml`：

## 使用方法

### 基本用法

#### 自动化用例写作

- 在test_cases目录下新增一个json文件即表明新增一个测试用例

- pre_commands、post_commands、以及execution_steps中的command的每一个""中的shell指令都是通过subprocess.run或subprocess.Popen起独立子进程执行的，仅改变子进程的状态或目录，不影响父进程，所以在尽量在一个""内通过&&串联完成一个完整的流程；

- 如果用例中，进程是需要在前台启动且持续保持在前台不退出时，需要设置命令不超时，则可以将timeout配置为None。

- 每个用例的 execution_steps 数量和步骤，应该严格与word测试细则文档中一致，否则填写测试结果时会发生错乱



#### 执行用例

1. 执行所有用例的场景：
```bash
python main.py 
```
或
```bash
pytest main.py -v
```

2. 执行单个用例的场景：
```bash
python main.py -t test_cases/test_case_1.json
```
或
```bash
python main.py --testcase test_cases/test_case_1.json
```

### 参数说明

- `--input`: 包含多个单元测试用例表格的word格式的测试细则文档
- `--output`: 输出在每个测试用例表格中都填入了测试执行结果的文档文件名 (默认从配置文件读取)
- `--config`: 配置文件路径 (默认: config/config.yaml)
- `--show-config`: 显示当前配置并退出

### scripts目录下脚本使用方法

#### Shell 脚本使用方法：
保存脚本为 xterm_screenshot.sh
赋予执行权限：chmod +x xterm_screenshot.sh
运行脚本：
查看帮助：./xterm_screenshot.sh --help
使用 flameshot 截图：./xterm_screenshot.sh --tool flameshot
使用 shutter 截图：./xterm_screenshot.sh --tool shutter


如果运行工具的环境是WSL2， 需要在linux子系统安装wmctrl，在windows系统安装VcXsrv（或MobaXterm）。
 wmctrl -l 可能会报错，原因是缺少窗口管理器和 X 服务器配置问题。需安装 X 服务器软件：VcXsrv（或MobaXterm），可通过它实现 WSL2 图形界面转发，Windows 11 并不默认自带 VcXsrv，需要单独进行安装。
可通过安装 openbox 窗口管理器并正确配置 X 服务器，可解决大部分问题；
若仍有困难，xdotool 是可靠的替代方案，能满足定位窗口的需求。
python -m pip install tk # pyautogui要用到的tkinter

#### Python 脚本使用方法：
保存脚本为 xterm_screenshot.py
安装所需依赖（根据使用的工具）：
PIL: pip install pillow
mss: pip install mss
pyautogui: pip install pyautogui
gnome-screenshot: sudo apt install gnome-screenshot
运行脚本：
查看帮助：python3 xterm_screenshot.py --help
使用 PIL 截图：python3 xterm_screenshot.py --tool PIL --output xterm.png
使用 gnome-screenshot 截图：python3 xterm_screenshot.py --tool gnome-screenshot

## 工作流程

TE-Agent的工作流程包含以下步骤：

1. **代码分析**: 使用大模型分析测试代码的功能、方法和期望结果
2. **编译运行**: 使用CMake编译项目并执行测试用例
3. **结果收集**: 收集编译和运行结果
4. **文档生成**: 基于分析结果和运行结果生成测试文档

## 项目结构

```
TE_Agent/
├── agent/                  # LangGraph相关模块
│   ├── __init__.py
│   ├── state.py
│   ├── nodes.py
│   └── langgraph_agent.py
├── config/                  # 工具函数
│   ├── __init__.py
│   ├── config_manager.py     # 配置管理器
│   └── config.yaml          # 默认配置文件
├── test_case_manager/         # 测试用例管理模块
│   ├── __init__.py
│   └── test_case_manager.py   # 新增TestCaseManager类
├── test_cases/                # 用例文件，每个用例文件由一个json文件定义
│   └── test_case_1.json       # case_name要与word测试细则文档中用例表格的“测试用例名称”完全一致，case_id也要与“标识”完全一致
├── reports/                # 报告和截图
│   └── screenshots/
├── utils/                  # 工具函数
│   ├── __init__.py
│   └── utils.py
├── conftest.py
├── main.py
└── merged_word.docx
```

## 示例测试项目

项目包含一个示例测试项目 (`examples/StartedNode/build`)，包含：

- `unit_test`: 包含多个测试函数的C++测试文件可执行程序

## 生成的文档格式

生成的测试用例文档包含以下部分：

- 测试用例概述
- 功能描述
- 测试框架和方法
- 测试场景
- 输入参数和期望输出
- 编译和运行信息
- 测试代码
- 结果分析
- 使用说明

## 故障排除

### 常见问题

1. **API密钥错误**
   - 检查API密钥是否有效且有足够的配额

2. **编译失败**
   - 确保系统已安装CMake和C++编译器
   - 检查CMakeLists.txt文件格式是否正确
   - 查看编译错误日志

3. **权限问题**
   - 确保对测试目录有读写权限
   - 确保可以执行编译和运行命令


### 日志和调试

智能体会输出详细的日志信息，包括：
- `[LOG]`: 正常操作日志
- `[ERROR]`: 错误信息

## 贡献指南

欢迎提交Issue和Pull Request来改进项目。

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 联系方式

如有问题或建议，请通过GitHub Issues联系我们。