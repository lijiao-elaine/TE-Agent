import os
import subprocess
import time
import re
import pdb
from datetime import datetime

def get_xterm_windows():
    """解析 xwininfo -root -tree 输出，提取所有 xterm 窗口信息"""
    try:
        # 执行命令获取窗口树； 要用subprocess.Popen起终端进程，获取唯一终端，否则有同名终端会错乱
        output = subprocess.check_output(
            'xwininfo -root -tree',
            shell=True,
            text=True
        )
        
        # 正则表达式匹配 xterm 窗口（标题和 ID）
        # 匹配格式：0xe0000d "标题": ("xterm" "XTerm")  宽x高+X+Y ...
        pattern = r'(\s+)(0x[0-9a-fA-F]+)\s+"([^"]+)"\s*:\s*\("xterm" "XTerm"\)\s+(\d+)x(\d+)\+(\d+)\+(\d+)'
        matches = re.findall(pattern, output)
        
        xterm_windows = []
        for match in matches:
            _, window_id, title, width, height, x, y = match
            xterm_windows.append({
                "id": window_id.strip(),
                "title": title.strip(),
                "width": int(width),
                "height": int(height),
                "x": int(x),          # 窗口左上角X坐标（相对于父窗口）
                "y": int(y),          # 窗口左上角Y坐标（相对于父窗口）
                "absolute_x": int(x), # 后续可计算绝对坐标（当前简化）
                "absolute_y": int(y)
            })

        #pdb.set_trace() 
        #  p output
        #'\nxwininfo: Window id: 0x438 (the root window) (has no name)\n\n  Root window id: 0x438 (the root window) (has no name)\n  Parent window id: 0x0 (none)\n     7 children:\n     0x2000a8 (has no name): ()  800x621+1483+725  +1483+725\n        1 child:\n        0xc0000d "test": ("xterm" "XTerm")  724x524+38+59  +1521+784\n           1 child:\n           0xc00018 (has no name): ()  724x524+0+0  +1521+784\n     0x2000a7 (has no name): ()  800x621+1277+278  +1277+278\n        1 child:\n        0xa0000d "test": ("xterm" "XTerm")  724x524+38+59  +1315+337\n           1 child:\n           0xa00018 (has no name): ()  724x524+0+0  +1315+337\n     0x2000a6 (has no name): ()  800x621+186+167  +186+167\n        1 child:\n        0x80000d "test": ("xterm" "XTerm")  724x524+38+59  +224+226\n           1 child:\n           0x800018 (has no name): ()  724x524+0+0  +224+226\n     0x20009f (has no name): ()  800x621+482+392  +482+392\n        1 child:\n        0x60000d "test": ("xterm" "XTerm")  724x524+38+59  +520+451\n           1 child:\n           0x600018 (has no name): ()  724x524+0+0  +520+451\n     0x200027 "Weston WM": ()  10x10+0+0  +0+0\n     0x200002 (has no name): ()  8192x8192+0+0  +0+0\n     0x200001 (has no name): ()  10x10+0+0  +0+0\n\n'

        # p matches 结果
        #[('\n        ', '0xc0000d', 'test', '724', '524', '38', '59'),
        # ('\n        ', '0xa0000d', 'test', '724', '524', '38', '59'),
        # ('\n        ', '0x80000d', 'test', '724', '524', '38', '59'),
        # ('\n        ', '0x60000d', 'test', '724', '524', '38', '59')]

        #p xterm_windows
        #[{'id': '0xc0000d', 'title': 'test', 'width': 724, 'height': 524, 'x': 38, 'y': 59, 'absolute_x': 38, 'absolute_y': 59}, 
        #{'id': '0xa0000d', 'title': 'test', 'width': 724, 'height': 524, 'x': 38, 'y': 59, 'absolute_x': 38, 'absolute_y': 59}, 
        #{'id': '0x80000d', 'title': 'test', 'width': 724, 'height': 524, 'x': 38, 'y': 59, 'absolute_x': 38, 'absolute_y': 59}, 
        #{'id': '0x60000d', 'title': 'test', 'width': 724, 'height': 524, 'x': 38, 'y': 59, 'absolute_x': 38, 'absolute_y': 59}]

        return xterm_windows
    
    except Exception as e:
        print(f"解析窗口信息失败：{e}")
        return []

def capture_xterm_by_title(target_title, output_dir="screenshots"):
    """根据标题中的关键字捕获目标 xterm 窗口"""
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有 xterm 窗口
    xterm_windows = get_xterm_windows()
    if not xterm_windows:
        print("未找到任何 xterm 窗口")
        return False
    
    # 过滤包含目标关键字的窗口（模糊匹配->精确匹配）
    target_windows = [
        win for win in xterm_windows
        if target_title == win["title"]
    ]

    #pdb.set_trace() 
    # p target_windows 结果：
    #[{'id': '0x80000d', 'title': 'test', 'width': 724, 'height': 524, 'x': 38, 'y': 59, 'absolute_x': 38, 'absolute_y': 59},
    # {'id': '0x60000d', 'title': 'test', 'width': 724, 'height': 524, 'x': 38, 'y': 59, 'absolute_x': 38, 'absolute_y': 59}]
    if not target_windows:
        print(f"未找到标题为 '{target_title}' 的 xterm 窗口")
        return False
    
    # 取第一个匹配的窗口id（可根据需求修改为多个）
    target = target_windows[0]
    print(f"找到目标窗口：ID={target['id']}，标题={target['title']}")
    
    # 用 xwd 捕获窗口并转换为 PNG
    output_path = os.path.join(output_dir, f"xterm_xwd_{target['id']}.png")
    try:
        # 步骤1：用 xwd 捕获窗口（指定窗口 ID）
        subprocess.run(
            f"xwd -id {target['id']} -out /tmp/xterm_temp.xwd",
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # 步骤2：用 convert 转换为 PNG
        subprocess.run(
            f"convert /tmp/xterm_temp.xwd {output_path}",
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # 清理临时文件
        os.remove("/tmp/xterm_temp.xwd")
        print(f"截图成功，保存至：{output_path}")
        return True
    
    except Exception as e:
        print(f"截图失败：{e}")
        return False

def main():
    # 启动一个带特定标题的 xterm
    xterm_title = "xwd_convert_test"  # 标题中包含的关键字
    print("启动 xterm 窗口前的时间：", datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"))
    print(f"启动 xterm 窗口（标题包含：{xterm_title}）...")

    #os.system(f"export DISPLAY=:0")
    os.environ["DISPLAY"] = ":0"
    command = f'xterm -T {xterm_title} -geometry 120x40 -e \'ls -lrt;pwd;date;bash --rcfile ~/.bashrc_no_title --noprofile\' &'
    #os.system(command)
    terminal = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2)  # 等待窗口启动
    
    # 截图标题包含 {xterm_title} 的 xterm 窗口
    capture_xterm_by_title(xterm_title)
    print("截图完成后的时间：", datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"))

if __name__ == "__main__":
    main()
