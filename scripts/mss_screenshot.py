from mss import mss
from mss.tools import to_png
import time
import os

def capture_full_screen(save_path="full_screen.png"):
    with mss() as sct:
        # 打印所有可用显示器信息（调试用）
        for i, monitor in enumerate(sct.monitors):
            print(f"显示器 {i}: {monitor}")
        
        # 尝试使用第二个显示器（索引 1，通常是主显示器）
        monitor = sct.monitors[1]  # 从 0 修改为 1
        sct_img = sct.grab(monitor)
        to_png(sct_img.rgb, sct_img.size, output=save_path)
    print(f"全屏截图已保存至: {save_path}")
    return save_path

def find_window_region(full_screen_path, target_title="xter-title"):
    """
    模拟根据窗口标题特征查找窗口区域（实际应用中可结合图像识别优化）
    这里简化为返回预设的xterm窗口区域（需根据实际位置调整）
    """
    # 实际使用时，可通过OpenCV等库识别窗口标题栏来获取坐标
    # 以下为示例坐标，需根据你的xterm窗口位置修改
    return {
        "left": 200,   # 窗口左上角X坐标
        "top": 200,    # 窗口左上角Y坐标
        "width": 800,  # 窗口宽度
        "height": 600  # 窗口高度
    }

def capture_window(region, save_path="window_screenshot.png"):
    """根据指定区域截取窗口"""
    with mss() as sct:
        sct_img = sct.grab(region)
        to_png(sct_img.rgb, sct_img.size, output=save_path)
    print(f"窗口截图已保存至: {save_path}")
    return save_path

def main():
    # 确保保存目录存在
    output_dir = "screenshots"
    os.makedirs(output_dir, exist_ok=True)
    
    # 步骤1：启动目标xterm窗口（如果还没启动）
    print("启动xterm窗口...")
    #os.system('xterm -T "xter-title" &')  # 启动带标题的xterm
    #os.system(f"export DISPLAY=:0")
    os.environ["DISPLAY"] = ":0"
    command = 'xterm -T "test" -geometry 120x40 -e \'ls -lrt;pwd;bash --rcfile ~/.bashrc_no_title --noprofile\' &'
    os.system(command)
    time.sleep(2)  # 等待窗口完全启动
    
    # 步骤2：先截取全屏，用于定位窗口（可选）
    full_screen_path = os.path.join(output_dir, "full_screen.png")
    capture_full_screen(full_screen_path)
    
    # 步骤3：查找xterm窗口区域（实际应用中需优化定位逻辑）
    print("定位xterm窗口区域...")
    window_region = find_window_region(full_screen_path)
    
    # 步骤4：截取目标窗口
    window_screenshot_path = os.path.join(output_dir, "xterm_screenshot.png")
    capture_window(window_region, window_screenshot_path)
    
    print("自动化截图完成！")

if __name__ == "__main__":
    main()
