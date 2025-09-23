# TE-Agent

TE-Agent是根据测试细则文档和自动化用例配置文件执行测试用例，并生成填入了测试结果的测试细则文档的智能体框架。

## 项目简介

TE-Agent是一个基于pytest和LangGraph构建的智能体框架，能够自动运行测试用例，并回填测试结果和截图到测试用例文档，最终生成标准化的测试报告。

## 功能特性

- 🏗️ **自动运行并填入结果**: 自动执行测试用例并填入结果
- 📝 **文档自动生成**: 生成标准化的、填入了测试执行结果的测试报告
- 🔄 **工作流管理**: 基于LangGraph的可靠工作流管理和pytest用例管理
- 🎯 **错误处理**: 完善的错误处理和日志记录机制
- ⚙️ **配置管理**: 灵活的配置文件管理，支持多种参数配置

## 系统要求

- Python 3.10+
- pytest 8.4+


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
sudo apt-get install expect
```

### 3. 配置系统参数

项目使用YAML配置文件管理各种参数。默认配置文件位于 `config/config.yaml`：

如果需要修改任何配置，如：远程执行用例的机器os类型、ip地址、登录用户名和密码，或 生成报告的地址、归档日志的地址等，直接修改 `config/config.yaml` 中对应配置项的值即可。

scp unit_test root@192.168.137.100:/home/lijiao/work/GD-Agent/examples/StartedNode/build/
scp main root@192.168.137.100:/home/lijiao/work/display-GD-Agent-tool/

## 使用方法

### 基本用法

#### 自动化用例写作

- 在test_cases目录下新增一个json文件即表明新增一个测试用例

- 以下是自动化用例配置文件示例：
```bash
{
  "case_id": "XXX_TEST_001", # 用例id，需要与word测试细则文档中的用例“标识”一致且唯一，必填
  "case_name": "XXX_测试_001", # 用例id，需要与word测试细则文档中的用例“测试用例名称”一致，必填
  "pre_commands": [ # 用例预处理步骤
    "cd /home/lijiao/work/GD-Agent/examples/StartedNode && rm -rf ./build && mkdir build && cp main.c build && ls -lrt",
    "cd /home/lijiao/work/GD-Agent/examples/StartedNode/build && pwd && ls -lrt && gcc -o unit_test main.c && ls -lrt"
  ],
  "execution_steps": [ # 每个用例的多个执行步骤，其中步骤的数量和顺序，应该严格与word测试细则文档中一致，否则填写测试结果时会发生错乱，必填
    {
      "exec_path": "/home/lijiao/work/GD-Agent/examples/StartedNode", # 必填
      "command": "date;cd /home/lijiao/work/GD-Agent/examples/StartedNode/build && ls -lrt && ls -lrt", # 必填
      "blocked_process":0, # 表明 command 启动的进程是否始终保持在前台不退出，不退出即为阻塞式的，需要配置为1，否则为0
      "sleep_time":1, # 如果blocked_process值为0，则sleep_time必须配置，且不能过大，比当前步骤的command执行时长稍长1秒左右即可
      "timeout": 30,
      "expected_output": [] # 预期结果检查时，用于检查程序执行终端是否打印这些字符串以判断用例成功与否
    },
    {
      "exec_path": "/home/lijiao/work/GD-Agent/examples/StartedNode/build",
      "command": "date;./unit_test;ls -lrt;ls -lrt;ls -lrt;ls -lrt;ls -lrt;ls -lrt;ls -lrt;ls -lrt",
      "blocked_process":0,
      "sleep_time":1,
      "timeout": 30,
      "expected_output": [
        "[       OK ] EmitterStateTest.StartedNodeWithEmptyGroupsIncrementsDocCount",
        "[       OK ] EmitterStateTest.StartedNodeWithNonEmptyGroupsIncrementsChildCount",
        "[       OK ] EmitterStateTest.StartedNodeResetsAllFlags",
        "[       OK ] EmitterStateTest.StartedNodeInNestedGroups",
        "[  PASSED  ] 4 tests"
      ]
    }
  ],
  "post_commands": [ # 用例后处理步骤
    "ps -ef|grep './main'|grep -v grep|awk '{print $2}'|xargs kill -9"
  ]
}
```

- pre_commands、post_commands、以及execution_steps中的command的每一个""中的shell指令都是通过subprocess.Popen起独立子进程执行的，仅改变子进程的状态或目录，不影响父进程，所以在尽量在一个""内通过&&或;串联完成一个完整的流程；


### 用例运行环境依赖配置

如果是在上位机运行工具，下位机运行用例可执行程序，则需要修改以下配置：

1. 修改下位机的 ~/.bashrc ，将其中的如下语句注释，因为以下语句会将xterm终端的标题强行修改为user@host:dir：

``` bash
case "$TERM" in
xterm*|rxvt*)
    PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
    ;;
*)
    ;;
esac
```

#### 执行用例

1. 执行所有用例的场景：
```bash
python main.py 
```

2. 执行module_1模块用例的场景：
```bash
python main.py -m test_cases/module_1
```

3. 执行单个用例的场景：
```bash
python main.py -t test_cases/test_case_1.json
```
或
```bash
python main.py --testcase test_cases/test_case_1.json
```

### 参数说明

- `-t`: 待执行的单个测试用例路径 (可选，如：test_cases/test_case_1.json)
- `-m`: 待执行的测试用例模块 (可选，如：test_cases/module_1)
- `-r`: 生成的测试报告路径 (可选，默认: reports/test_report.html)

## 工作流程

TE-Agent的工作流程包含以下步骤：

1. **用例管理**: 使用pytest管理用例和调度用例
2. **用例执行**: 使用LangGraph执行每个测试用例的内部工作流调度
3. **结果收集**: 收集用例运行结果
4. **报告生成**: 基于分析结果和运行结果生成测试文档

## 项目结构

```
TE_Agent/
├── agent/                  # LangGraph相关模块
│   ├── __init__.py
│   ├── state.py
│   ├── nodes.py
│   └── test_execute_agent.py
├── config/                  
│   ├── __init__.py
│   ├── config_manager.py     # 配置管理器
│   └── config.yaml          # 默认配置文件
├── test_case_manager/         # 测试用例管理模块
│   ├── __init__.py
│   └── test_case_manager.py   # 测试用例管理类
├── test_cases/                # 用例文件，每个用例文件由一个json文件定义
│   └── test_case_1.json       # case_name要与word测试细则文档中用例表格的“测试用例名称”完全一致，case_id也要与“标识”完全一致
├── test_cases_ohos/                # 鸿蒙系统下的用例文件，每个用例文件由一个json文件定义
│   └── test_case_1.json
├── reports/                # 报告和截图
│   └── screenshots/
├── utils/                  # 工具函数
│   ├── __init__.py
│   ├── screenshot_handler.py # 用于xterm终端截图的类
│   ├── subprocess_manager.py
│   ├── word_report_filler.py # 用于处理测试结果回填的类
│   └── command_executor.py
├── conftest.py        # pytest文件
├── main.py            # 入口
├── requirements.txt  # python依赖包列表
└── merged_word.docx  # 测试细则文档，用于读取文本用例
```

## 示例测试项目

项目包含2个示例模块和1个独立的示例测试用例，包含：

- 模块：test_cases/module_1 、 test_cases/module_2 ， 其下包含多个用例

- 用例： test_cases/test_case_1.json


## 生成的文档格式

生成的测试报告包含以下部分：

### test_report.docx

- 测试用例步骤的测试结果

- 测试用例步骤执行过程截图

- 测试用例执行结果

- 测试时间

- 测试人员

### test_report.html

- 总用例量

- 成功的用例量

- 失败的用例量

## 故障排除

### 常见问题

1. . **权限问题**
   - 确保对测试目录有读写权限
   - 确保可以执行用例指令


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