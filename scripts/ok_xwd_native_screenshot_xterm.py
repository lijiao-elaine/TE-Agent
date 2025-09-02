import os
import subprocess
import time
import re
import pdb
from datetime import datetime

def get_xterm_windows():
    """解析 xwininfo -root -tree 输出，提取所有 xterm 窗口信息（修正绝对坐标计算）"""
    try:
        # 执行命令获取窗口树（保留父窗口绝对坐标，用于计算xterm真实绝对位置）
        output = subprocess.check_output(
            'xwininfo -root -tree',
            shell=True,
            text=True
        )
        
        # 正则表达式优化：匹配xterm窗口的同时，提取父窗口绝对坐标（解决原脚本绝对坐标错误）
        # 匹配格式：父窗口信息→xterm窗口信息（含相对父窗口坐标+父窗口绝对坐标）
        # 示例行：0xc0000d "test": ("xterm" "XTerm")  724x524+38+59  +1521+784
        pattern = r'(\s+)(0x[0-9a-fA-F]+)\s+"([^"]+)"\s*:\s*\("xterm" "XTerm"\)\s+(\d+)x(\d+)\+(\d+)\+(\d+)\s+\+(\d+)\+(\d+)'
        matches = re.findall(pattern, output)
        
        xterm_windows = []
        for match in matches:
            _, window_id, title, width, height, rel_x, rel_y, parent_abs_x, parent_abs_y = match
            # 计算xterm窗口的真实绝对坐标（父窗口绝对坐标 + 窗口相对父窗口坐标）
            absolute_x = int(parent_abs_x) + int(rel_x)
            absolute_y = int(parent_abs_y) + int(rel_y)
            
            xterm_windows.append({
                "id": window_id.strip(),
                "title": title.strip(),
                "width": int(width),
                "height": int(height),
                "x": int(rel_x),          # 相对父窗口X坐标（原脚本逻辑保留）
                "y": int(rel_y),          # 相对父窗口Y坐标（原脚本逻辑保留）
                "absolute_x": absolute_x, # 修正后的屏幕绝对X坐标
                "absolute_y": absolute_y  # 修正后的屏幕绝对Y坐标
            })

        return xterm_windows
    
    except Exception as e:
        print(f"解析窗口信息失败：{e}")
        return []

def capture_xterm_by_title(target_title, output_dir="screenshots"):
    """根据标题精确匹配xterm窗口，用xwd截图 + X11原生工具转换PNG"""
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有xterm窗口（含修正后的绝对坐标）
    xterm_windows = get_xterm_windows()
    if not xterm_windows:
        print("未找到任何 xterm 窗口")
        return False
    
    # 精确匹配目标窗口（避免同名窗口干扰）
    target_windows = [
        win for win in xterm_windows
        if target_title == win["title"]
    ]

    if not target_windows:
        print(f"未找到标题为 '{target_title}' 的 xterm 窗口")
        return False
    
    # 取第一个匹配的窗口（可扩展为批量处理多个窗口）
    target = target_windows[0]
    print(f"找到目标窗口：ID={target['id']}，标题={target['title']}，绝对坐标=({target['absolute_x']},{target['absolute_y']})")
    
    # 输出路径（用窗口ID命名，避免重复）
    output_path = os.path.join(output_dir, f"xterm_xwd_{target['id']}.png")
    # 临时文件（XWD原始格式 + PNM中间格式，均放在/tmp目录）
    temp_xwd = "/tmp/xterm_temp.xwd"
    temp_pnm = "/tmp/xterm_temp.pnm"
    
    try:
        # 步骤1：用xwd（X11原生）捕获指定窗口
        # -id：指定目标窗口ID；-out：输出XWD格式原始文件
        result = subprocess.run(
            f"xwd -id {target['id']} -out {temp_xwd}",
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,  # 屏蔽冗余输出，保持日志简洁
            stderr=subprocess.DEVNULL
        )
        print(f"xwd 捕获窗口成功，临时XWD文件：{temp_xwd}")
        
        # 步骤2：用xwdtopnm（X11原生）将XWD转换为PNM格式
        # PNM是Netpbm工具集的原生格式，X11原生工具可直接处理
        result = subprocess.run(
            f"xwdtopnm {temp_xwd} > {temp_pnm}",
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"xwdtopnm 转换成功，临时PNM文件：{temp_pnm}")
        
        # 步骤3：用pnmtopng（X11原生）将PNM转换为PNG通用格式
        result = subprocess.run(
            f"pnmtopng {temp_pnm} > {output_path}",
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"pnmtopng 转换成功，最终PNG文件：{output_path}")
        
        # 清理临时文件（避免占用磁盘空间）
        os.remove(temp_xwd)
        os.remove(temp_pnm)
        print(f"临时文件清理完成，截图最终路径：{os.path.abspath(output_path)}")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"截图/转换命令执行失败：{e}")
        # 出错时仍清理临时文件，避免残留
        if os.path.exists(temp_xwd):
            os.remove(temp_xwd)
        if os.path.exists(temp_pnm):
            os.remove(temp_pnm)
        return False
    except Exception as e:
        print(f"截图过程异常：{e}")
        return False

def main():
    # 启动带特定标题的xterm窗口（标题需精确匹配后续截图逻辑）
    xterm_title = "xwd_native_test"
    print("启动 xterm 窗口前的时间：", datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"))
    print(f"启动 xterm 窗口（标题：{xterm_title}）...")

    # 设置显示环境（确保X11可用，本地环境默认为:0）
    os.environ["DISPLAY"] = ":0"
    # 启动xterm命令：指定标题、尺寸，执行自定义命令后进入bash（避免窗口自动关闭）
    command = (
        f'xterm -T "{xterm_title}" -geometry 120x40 '
        f'-e \'ls -lrt;date; pwd; ls -lrt;ls -lrt;ls -lrt; bash --rcfile ~/.bashrc_no_title --noprofile\' &'
    )
    #os.system(command)
    terminal = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2)  # 延长等待时间，确保X11窗口完全注册（避免窗口未找到）
    
    # 执行截图（精确匹配标题为"test"的xterm窗口）
    capture_xterm_by_title(xterm_title)
    print("截图完成后的时间：", datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"))
    
if __name__ == "__main__":
    main()