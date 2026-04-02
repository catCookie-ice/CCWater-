import tkinter as tk
import os
import sys
import shutil
import subprocess
import constants as c
from visualizer import WaterVisualizer

def main():
    # 检查是否为 PyInstaller 打包后的可执行文件
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
        exe_name = os.path.basename(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
        exe_name = "main.py" 

    target_dir_name = "CCWater"
    target_path = os.path.join(application_path, target_dir_name)
    
    # 如果当前运行目录不是目标目录，则进行自我部署
    if os.path.basename(application_path) != target_dir_name:
        print(f"程序不在 {target_dir_name} 目录中，正在进行自我部署...")
        
        # 创建目标目录
        if not os.path.exists(target_path):
            os.makedirs(target_path)
        
        # 复制所有 .py 文件到目标目录
        for file in os.listdir(application_path):
            if file.endswith(".py"):
                shutil.copy2(os.path.join(application_path, file), os.path.join(target_path, file))
        
        # 如果是打包后的 exe，也需要复制
        if getattr(sys, 'frozen', False):
            shutil.copy2(sys.executable, os.path.join(target_path, exe_name))
        
        # 复制 resource 文件夹到目标目录
        current_resource_path = os.path.join(application_path, 'resource')
        target_resource_path = os.path.join(target_path, 'resource')
        if os.path.exists(current_resource_path):
            if os.path.exists(target_resource_path):
                shutil.rmtree(target_resource_path)
            shutil.copytree(current_resource_path, target_resource_path)
        else:
            os.makedirs(target_resource_path, exist_ok=True)
        
        print(f"自我部署完成，正在从 {target_path} 重新启动...")
        
        # 重新启动新实例
        new_exe_path = os.path.join(target_path, exe_name)
        if getattr(sys, 'frozen', False):
            subprocess.Popen([new_exe_path])
        else:
            subprocess.Popen([sys.executable, new_exe_path])
        
        # 清理旧的 exe (仅打包模式下)
        if getattr(sys, 'frozen', False):
            current_exe_path = sys.executable
            temp_bat_path = os.path.join(application_path, "cleanup.bat")
            with open(temp_bat_path, "w") as f:
                f.write(f"@echo off\n")
                f.write(f"timeout /t 2 /nobreak > nul\n")
                f.write(f"del \"{current_exe_path}\"\n")
                f.write(f"del \"{temp_bat_path}\"\n")
            subprocess.Popen([temp_bat_path], creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW)
        
        sys.exit(0)

    root = tk.Tk()
    # 强制设置全局字体
    root.option_add("*Font", c.FONT_PIXEL)
    
    # 动态确定 resource 文件夹路径
    resource_dir = os.path.join(application_path, 'resource')
    
    # 检查并创建 resource 文件夹
    if not os.path.exists(resource_dir):
        os.makedirs(resource_dir)
        
    app = WaterVisualizer(root, resource_dir)
    app.root.mainloop()

if __name__ == "__main__":
    main()
