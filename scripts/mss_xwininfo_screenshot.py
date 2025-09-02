import subprocess
import re
from mss import mss
from mss.tools import to_png
import os
import time

def get_window_region_by_title(target_title):
    """用 xwininfo 获取目标窗口的实时区域（left, top, width, height）"""
    try:
        # 用 xwininfo 查询目标窗口信息
        output = subprocess.check_output(
            f'xwininfo -name "{target_title}"',
            shell=True,
            text=True
        )
        # 正则提取位置和尺寸
        left = int(re.search(r'Absolute upper-left X:\s+(\d+)', output).group(1))
        top = int(re.search(r'Absolute upper-left Y:\s+(\d+)', output).group(1))
        width = int(re.search(r'Width:\s+(\d+)', output).group(1))
        height = int(re.search(r'Height:\s+(\d+)', output).group(1))
        return {"left": left, "top": top, "width": width, "height": height}
    except Exception as e:
        print(f"xwininfo 获取窗口区域失败：{e}")
        return None

# 主流程：xwininfo 定位 → mss 精准截图
def main():
    target_title = "test"  # 目标窗口标题
    # 步骤1：启动目标xterm窗口（如果还没启动）
    print("启动xterm窗口...")
    #os.system('xterm -T "xter-title" &')  # 启动带标题的xterm
    #os.system(f"export DISPLAY=:0")
    os.environ["DISPLAY"] = ":0"
    command = f'xterm -T {target_title} -geometry 120x40 -e \'ls -lrt;pwd;bash --rcfile ~/.bashrc_no_title --noprofile\' &'
    os.system(command)
    time.sleep(2)  # 等待窗口完全启动

    window_region = get_window_region_by_title(target_title)
    if not window_region:
        return

    print(f"窗口区域：{window_region}")
    # mss 直接截取目标窗口区域
    with mss(display=os.environ["DISPLAY"]) as sct:  # 强制使用当前 DISPLAY
        sct_img = sct.grab(window_region)
        to_png(sct_img.rgb, sct_img.size, output="target_mss_window.png")
    print("mss 精准截图完成！")

if __name__ == "__main__":
    main()