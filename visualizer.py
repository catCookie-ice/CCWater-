import tkinter as tk
from tkinter import messagebox, filedialog
import os
import shutil
import threading
import constants as c
from data_utils import parse_data, save_data_to_file, validate_file_format, query_deepseek
from ui_components import ArcadeButton, MergeDialog, FileCard, DraggableCard

class WaterVisualizer:
    def __init__(self, root, resource_dir):
        self.root = root
        self.root.title("CCWater - 降雨量分析器")
        self.root.geometry("1280x850")
        self.resource_dir = resource_dir
        self.root.configure(bg=c.COLOR_BG)
        
        # 启动时最大化窗口
        self.root.state('zoomed')
        # 绑定F11键切换真全屏，Esc键退出真全屏
        self.root.bind("<F11>", self.toggle_true_fullscreen)
        self.root.bind("<Escape>", self.exit_true_fullscreen)
        
        self.all_files_data = {}
        self.current_data = {}
        self.included_cities = []
        self.excluded_cities = []
        self.detail_city = None 
        self.current_theme = "dark" # 默认主题为暗色
        self.clear_mode = False # 默认关闭清晰模式
        self.file_cards = [] # 存储文件卡片对象
        self.selected_file_card = None # 当前选中的文件卡片
        self.excluded_subs = {} # 存储每个城市被排除的子区域 {city_name: [sub1, sub2]}
        
        self.setup_ui()
        self.load_local_files()
        self.apply_theme() # 初始应用主题

    def toggle_true_fullscreen(self, event=None):
        if self.root.attributes('-fullscreen'):
            self.root.attributes('-fullscreen', False)
            self.root.state('zoomed') # 返回最大化窗口
        else:
            self.root.attributes('-fullscreen', True)

    def exit_true_fullscreen(self, event=None):
        if self.root.attributes('-fullscreen'):
            self.root.attributes('-fullscreen', False)
            self.root.state('zoomed') # 返回最大化窗口

    def toggle_theme(self):
        if self.current_theme == "dark":
            c.update_global_colors("light")
            self.current_theme = "light"
        else:
            c.update_global_colors("dark")
            self.current_theme = "dark"
        
        self.apply_theme()

    def toggle_clear_mode(self):
        self.clear_mode = not self.clear_mode
        self.apply_theme()
        self.draw_chart()

    def apply_theme(self):
        # 更新根窗口
        self.root.configure(bg=c.COLOR_BG)
        self.paned.config(bg=c.COLOR_BORDER)

        # 更新左侧边栏
        self.left_sidebar.config(bg=c.COLOR_BG)
        for widget in self.left_sidebar.winfo_children():
            if isinstance(widget, tk.Frame): # inner_left frame
                widget.config(bg=c.COLOR_BG)
                for sub_widget in widget.winfo_children():
                    if isinstance(sub_widget, tk.Label):
                        sub_widget.config(bg=c.COLOR_BG, fg=c.COLOR_ACCENT if "[ 已添加文件 ]" in sub_widget.cget("text") else (c.COLOR_SECONDARY if "[ AI 数据链接 ]" in sub_widget.cget("text") else c.COLOR_FG))
                    elif isinstance(sub_widget, tk.Frame): # file_outer_frame or btn_grid or ai_box
                        if sub_widget == self.file_outer_frame:
                            sub_widget.config(bg=c.COLOR_BG, highlightbackground=c.COLOR_BORDER)
                            for file_widget in self.file_canvas.winfo_children(): # file_frame
                                if file_widget == self.file_frame:
                                    file_widget.config(bg=c.COLOR_BG)
                                    for card in self.file_cards:
                                        card.update_colors()
                        else:
                            sub_widget.config(bg=c.COLOR_BG, highlightbackground=c.COLOR_BORDER)
                            for ai_widget in sub_widget.winfo_children():
                                if isinstance(ai_widget, tk.Entry):
                                    ai_widget.config(bg=c.COLOR_BG, fg=c.COLOR_FG, insertbackground=c.COLOR_FG)
                                elif isinstance(ai_widget, ArcadeButton):
                                    if "导入文件" in ai_widget.label.cget("text"):
                                        ai_widget.update_colors(c.COLOR_FG)
                                    elif "合并文件" in ai_widget.label.cget("text"):
                                        ai_widget.update_colors(c.COLOR_ACCENT)
                                    elif "删除文件" in ai_widget.label.cget("text"):
                                        ai_widget.update_colors(c.COLOR_SECONDARY)
                                    elif "运行搜索" in ai_widget.label.cget("text"):
                                        ai_widget.update_colors(c.COLOR_SECONDARY)
                    elif isinstance(sub_widget, ArcadeButton): # direct ArcadeButtons in inner_left
                        if "导入文件" in sub_widget.label.cget("text"):
                            sub_widget.update_colors(c.COLOR_FG)
                        elif "合并文件" in sub_widget.label.cget("text"):
                            sub_widget.update_colors(c.COLOR_ACCENT)
                        elif "删除文件" in sub_widget.label.cget("text"):
                            sub_widget.update_colors(c.COLOR_SECONDARY)
            elif isinstance(widget, tk.Label): # ai_status label
                widget.config(bg=c.COLOR_BG, fg=c.COLOR_BORDER)
        
        # 更新文件区域的 Canvas 和滚动条
        self.file_canvas.config(bg=c.COLOR_BG)
        self.file_scrollbar.config(troughcolor=c.COLOR_BG, bg=c.COLOR_BORDER, activebackground=c.COLOR_ACCENT)

        # 更新中间主区域
        self.main_area.config(bg=c.COLOR_BG)
        self.top_bar.config(bg=c.COLOR_BG)
        self.back_btn_frame.config(bg=c.COLOR_BG)
        self.back_btn.update_colors(c.COLOR_ACCENT)
        self.theme_toggle_btn.update_colors(c.COLOR_SECONDARY) # 更新主题切换按钮
        self.clear_mode_toggle_btn.update_colors(c.COLOR_ACCENT) # 更新清晰模式切换按钮
        for widget in self.top_bar.winfo_children():
            if isinstance(widget, tk.Label):
                widget.config(bg=c.COLOR_BG, fg=c.COLOR_FG)
        
        self.chart_container.config(bg=c.COLOR_BG, highlightbackground=c.COLOR_BORDER_HL)
        self.canvas.config(bg=c.COLOR_BG)

        # 更新右侧边栏
        self.right_sidebar.config(bg=c.COLOR_BG)
        for widget in self.right_sidebar.winfo_children():
            if isinstance(widget, tk.Frame): # inner_right frame
                widget.config(bg=c.COLOR_BG)
                for sub_widget in widget.winfo_children():
                    if isinstance(sub_widget, tk.Label):
                        sub_widget.config(bg=c.COLOR_BG, fg=c.COLOR_ACCENT if "[ 统计数据 ]" in sub_widget.cget("text") else (c.COLOR_FG if "活跃区域" in sub_widget.cget("text") else (c.COLOR_SECONDARY if "排除区域" in sub_widget.cget("text") else c.COLOR_FG)))
                    elif isinstance(sub_widget, tk.Frame): # quick_switch
                        sub_widget.config(bg=c.COLOR_BG)
                        for card_widget in sub_widget.winfo_children():
                            if isinstance(card_widget, ArcadeButton):
                                if "全部移除" in card_widget.label.cget("text"):
                                    card_widget.update_colors(c.COLOR_SECONDARY)
                                elif "全部添加" in card_widget.label.cget("text"):
                                    card_widget.update_colors(c.COLOR_FG)
                    elif isinstance(sub_widget, tk.Canvas): # inc_canvas, exc_canvas
                        sub_widget.config(bg=c.COLOR_BG)
                        for scrollbar_widget in sub_widget.winfo_children():
                            if isinstance(scrollbar_widget, tk.Scrollbar):
                                scrollbar_widget.config(troughcolor=c.COLOR_BG, bg=c.COLOR_BORDER, activebackground=c.COLOR_ACCENT)
            elif isinstance(widget, tk.Label): # direct labels in inner_right
                widget.config(bg=c.COLOR_BG, fg=c.COLOR_ACCENT if "[ 统计数据 ]" in widget.cget("text") else (c.COLOR_FG if "活跃区域" in widget.cget("text") else (c.COLOR_SECONDARY if "排除区域" in widget.cget("text") else c.COLOR_FG)))
            elif isinstance(widget, tk.Frame): # inc_outer_frame, exc_outer_frame
                if widget == self.inc_outer_frame:
                    widget.config(bg=c.COLOR_BG, highlightbackground=c.COLOR_FG)
                elif widget == self.exc_outer_frame:
                    widget.config(bg=c.COLOR_BG, highlightbackground=c.COLOR_SECONDARY)
        
        # 更新 MergeDialog (如果存在)
        for widget in self.root.winfo_children():
            if isinstance(widget, MergeDialog):
                widget.apply_theme()

        self.refresh_sidebar()
        self.draw_chart()

    def setup_ui(self):
        # 主布局容器
        self.paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.FLAT, sashwidth=4, bg=c.COLOR_BORDER)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # --- 左侧：文件与 AI 管理区 ---
        self.left_sidebar = tk.Frame(self.paned, bg=c.COLOR_BG, width=280)
        self.paned.add(self.left_sidebar, width=280)
        
        inner_left = tk.Frame(self.left_sidebar, bg=c.COLOR_BG, padx=15, pady=15)
        inner_left.pack(fill=tk.BOTH, expand=True)

        tk.Label(inner_left, text="[ 已添加文件 ]", font=c.FONT_PIXEL, bg=c.COLOR_BG, fg=c.COLOR_ACCENT).pack(anchor="w", pady=(0, 10))
        
        # 文件卡片滚动区域
        self.file_outer_frame = tk.Frame(inner_left, bg=c.COLOR_BG, bd=1, relief="solid", highlightbackground=c.COLOR_BORDER, highlightthickness=1)
        self.file_outer_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.file_canvas = tk.Canvas(self.file_outer_frame, bg=c.COLOR_BG, highlightthickness=0)
        self.file_scrollbar = tk.Scrollbar(self.file_outer_frame, orient="vertical", command=self.file_canvas.yview)
        self.file_frame = tk.Frame(self.file_canvas, bg=c.COLOR_BG)
        
        # 核心逻辑：监听内容变化和窗口变化以更新滚动条
        self.file_frame.bind("<Configure>", lambda e: self._update_scrollbar_visibility(self.file_canvas, self.file_scrollbar, self.file_frame))
        self.file_canvas.bind("<Configure>", lambda e: self._update_scrollbar_visibility(self.file_canvas, self.file_scrollbar, self.file_frame))
        
        self.file_window = self.file_canvas.create_window((0, 0), window=self.file_frame, anchor="nw")
        self.file_canvas.configure(yscrollcommand=self.file_scrollbar.set)
        
        # 动态调整内部框架宽度
        self.file_canvas.bind("<Configure>", lambda e: self.file_canvas.itemconfig(self.file_window, width=e.width), add="+")
        
        self.file_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # 初始时不 pack scrollbar，由 _update_scrollbar_visibility 控制

        # 滚轮支持
        for widget in (self.file_canvas, self.file_frame):
            widget.bind("<MouseWheel>", lambda e: self._on_mousewheel(e, self.file_canvas))
            widget.bind("<Button-4>", lambda e: self._on_mousewheel(e, self.file_canvas))
            widget.bind("<Button-5>", lambda e: self._on_mousewheel(e, self.file_canvas))

        btn_grid = tk.Frame(inner_left, bg=c.COLOR_BG)
        btn_grid.pack(fill=tk.X)
        
        ArcadeButton(btn_grid, "导入文件", self.import_and_save_file, c.COLOR_FG, height=35).pack(fill="x", pady=2)
        ArcadeButton(btn_grid, "合并文件", self.open_merge_dialog, c.COLOR_ACCENT, height=35).pack(fill="x", pady=2)
        ArcadeButton(btn_grid, "删除文件", self.delete_selected_files, c.COLOR_SECONDARY, height=35).pack(fill="x", pady=2)

        tk.Label(inner_left, text="[ AI 数据链接 ]", font=c.FONT_PIXEL, bg=c.COLOR_BG, fg=c.COLOR_SECONDARY).pack(anchor="w", pady=(20, 5))
        ai_box = tk.Frame(inner_left, bg=c.COLOR_BG, bd=1, relief="solid", highlightbackground=c.COLOR_BORDER, highlightthickness=1, padx=8, pady=8)
        ai_box.pack(fill=tk.X)
        
        self.ai_entry = tk.Entry(ai_box, font=c.FONT_PIXEL, bg=c.COLOR_BG, fg=c.COLOR_FG, insertbackground=c.COLOR_FG, relief="flat", bd=0)
        self.ai_entry.pack(fill=tk.X, pady=5)
        
        self.ai_btn = ArcadeButton(ai_box, "运行搜索", self.handle_ai_lookup, color=c.COLOR_SECONDARY, height=35)
        self.ai_btn.pack(fill="x")
        
        self.ai_status = tk.Label(inner_left, text="状态: 就绪", font=c.FONT_PIXEL, bg=c.COLOR_BG, fg=c.COLOR_BORDER)
        self.ai_status.pack(pady=10)

        # --- 中间：核心展示区 ---
        self.main_area = tk.Frame(self.paned, bg=c.COLOR_BG)
        self.paned.add(self.main_area, stretch="always")

        # 顶部标题栏
        self.top_bar = tk.Frame(self.main_area, bg=c.COLOR_BG, height=70, bd=0)
        self.top_bar.pack(fill=tk.X)
        self.top_bar.pack_propagate(False)

        self.back_btn_frame = tk.Frame(self.top_bar, bg=c.COLOR_BG)
        self.back_btn = ArcadeButton(self.back_btn_frame, "返回", self.show_main_view, color=c.COLOR_ACCENT, width=80, height=40)
        self.back_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.title_var = tk.StringVar(value="请插入硬币开始")
        tk.Label(self.top_bar, textvariable=self.title_var, font=c.FONT_TITLE, bg=c.COLOR_BG, fg=c.COLOR_FG).pack(side=tk.LEFT, padx=20, pady=15)

        # 主题切换按钮
        self.theme_toggle_btn = ArcadeButton(self.top_bar, "切换主题", self.toggle_theme, color=c.COLOR_SECONDARY, width=100, height=40)
        self.theme_toggle_btn.pack(side=tk.RIGHT, padx=10, pady=10)

        # 清晰模式切换按钮
        self.clear_mode_toggle_btn = ArcadeButton(self.top_bar, "清晰模式", self.toggle_clear_mode, color=c.COLOR_ACCENT, width=100, height=40)
        self.clear_mode_toggle_btn.pack(side=tk.RIGHT, padx=10, pady=10)

        # 画布容器
        self.chart_container = tk.Frame(self.main_area, bg=c.COLOR_BG, bd=2, relief="solid", highlightbackground=c.COLOR_BORDER_HL, highlightthickness=2)
        self.chart_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.canvas = tk.Canvas(self.chart_container, bg=c.COLOR_BG, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda e: self.draw_chart())
        
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_drop)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_double_click)

        # --- 右侧：筛选区 ---
        self.right_sidebar = tk.Frame(self.paned, bg=c.COLOR_BG, width=260)
        self.paned.add(self.right_sidebar, width=260)
        
        inner_right = tk.Frame(self.right_sidebar, bg=c.COLOR_BG, padx=15, pady=15)
        inner_right.pack(fill=tk.BOTH, expand=True)

        tk.Label(inner_right, text="[ 统计数据 ]", font=c.FONT_PIXEL, bg=c.COLOR_BG, fg=c.COLOR_ACCENT).pack(anchor="w", pady=(0, 10))

        tk.Label(inner_right, text=" 活跃区域 ", font=c.FONT_PIXEL, bg=c.COLOR_FG, fg=c.COLOR_BG).pack(anchor="w")
        
        # 活跃区域的外部框架 (固定边框和大小)
        self.inc_outer_frame = tk.Frame(inner_right, bg=c.COLOR_BG, bd=1, relief="solid", highlightbackground=c.COLOR_FG, highlightthickness=1)
        self.inc_outer_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 10))

        # 活跃区域滚动容器 (在外部框架内部)
        inc_canvas = tk.Canvas(self.inc_outer_frame, bg=c.COLOR_BG, highlightthickness=0)
        inc_scrollbar = tk.Scrollbar(self.inc_outer_frame, orient="vertical", command=inc_canvas.yview)
        self.inc_frame = tk.Frame(inc_canvas, bg=c.COLOR_BG) # 内部框架，不带边框，由 Canvas 边框显示
        
        # 核心逻辑：监听内容变化和窗口变化以更新滚动条
        self.inc_frame.bind("<Configure>", lambda e: self._update_scrollbar_visibility(inc_canvas, inc_scrollbar, self.inc_frame))
        inc_canvas.bind("<Configure>", lambda e: self._update_scrollbar_visibility(inc_canvas, inc_scrollbar, self.inc_frame))
        
        inc_window = inc_canvas.create_window((0, 0), window=self.inc_frame, anchor="nw")
        inc_canvas.configure(yscrollcommand=inc_scrollbar.set)
        
        # 动态调整内部框架宽度以填充 Canvas
        inc_canvas.bind("<Configure>", lambda e: inc_canvas.itemconfig(inc_window, width=e.width), add="+")
        
        inc_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # 初始时不 pack scrollbar
        
        # 滚轮支持
        for widget in (inc_canvas, self.inc_frame):
            widget.bind("<MouseWheel>", lambda e: self._on_mousewheel(e, inc_canvas))
            widget.bind("<Button-4>", lambda e: self._on_mousewheel(e, inc_canvas))
            widget.bind("<Button-5>", lambda e: self._on_mousewheel(e, inc_canvas))
        
        quick_switch = tk.Frame(inner_right, bg=c.COLOR_BG)
        quick_switch.pack(fill=tk.X, pady=5)
        ArcadeButton(quick_switch, "全部移除", lambda: self.move_all(False), color=c.COLOR_SECONDARY, height=30).pack(side=tk.LEFT, expand=True, fill="x", padx=2)
        ArcadeButton(quick_switch, "全部添加", lambda: self.move_all(True), color=c.COLOR_FG, height=30).pack(side=tk.RIGHT, expand=True, fill="x", padx=2)

        tk.Label(inner_right, text=" 排除区域 ", font=c.FONT_PIXEL, bg=c.COLOR_SECONDARY, fg=c.COLOR_BG).pack(anchor="w", pady=(10, 0))
        
        # 排除区域的外部框架 (固定边框 and 大小)
        self.exc_outer_frame = tk.Frame(inner_right, bg=c.COLOR_BG, bd=1, relief="solid", highlightbackground=c.COLOR_SECONDARY, highlightthickness=1)
        self.exc_outer_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # 排除区域滚动容器 (在外部框架内部)
        exc_canvas = tk.Canvas(self.exc_outer_frame, bg=c.COLOR_BG, highlightthickness=0)
        exc_scrollbar = tk.Scrollbar(self.exc_outer_frame, orient="vertical", command=exc_canvas.yview)
        self.exc_frame = tk.Frame(exc_canvas, bg=c.COLOR_BG) # 内部框架，不带边框，由 Canvas 边框显示
        
        # 核心逻辑：监听内容变化和窗口变化以更新滚动条
        self.exc_frame.bind("<Configure>", lambda e: self._update_scrollbar_visibility(exc_canvas, exc_scrollbar, self.exc_frame))
        exc_canvas.bind("<Configure>", lambda e: self._update_scrollbar_visibility(exc_canvas, exc_scrollbar, self.exc_frame))
        
        exc_window = exc_canvas.create_window((0, 0), window=self.exc_frame, anchor="nw")
        exc_canvas.configure(yscrollcommand=exc_scrollbar.set)
        
        # 动态调整内部框架宽度以填充 Canvas
        exc_canvas.bind("<Configure>", lambda e: exc_canvas.itemconfig(exc_window, width=e.width), add="+")
        
        exc_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # 初始时不 pack scrollbar

        # 滚轮支持
        for widget in (exc_canvas, self.exc_frame):
            widget.bind("<MouseWheel>", lambda e: self._on_mousewheel(e, exc_canvas))
            widget.bind("<Button-4>", lambda e: self._on_mousewheel(e, exc_canvas))
            widget.bind("<Button-5>", lambda e: self._on_mousewheel(e, exc_canvas))

    # --- AI 查找逻辑 ---
    def handle_ai_lookup(self):
        region = self.ai_entry.get().strip()
        if not region: return
        
        self.ai_status.config(text="连接中...", fg=c.COLOR_SECONDARY)
        self.ai_btn.config_state(tk.DISABLED)
        
        threading.Thread(target=self._run_deepseek_search, args=(region,), daemon=True).start()

    def _run_deepseek_search(self, region):
        res = query_deepseek(region)
        def _finish():
            if res and "cities" in res:
                idx = 1
                while os.path.exists(os.path.join(self.resource_dir, f"AIfind_{idx}.txt")): idx += 1
                fname = f"AIfind_{idx}.txt"
                fpath = os.path.join(self.resource_dir, fname)
                custom_title = res.get("title", f"AI搜索: {region}")
                data_dict = {}
                for city_data in res["cities"]:
                    m_city = city_data.get("main_city")
                    if not m_city: continue
                    data_dict[m_city] = {}
                    for item in city_data.get("results", []):
                        data_dict[m_city][item.get('sub_city') or "城区"] = item.get('rainfall', 0.0)
                if data_dict:
                    save_data_to_file(fpath, data_dict, custom_title)
                    self.load_local_files()
                    self.ai_status.config(text=f"同步完成: {fname}", fg=c.COLOR_FG)
                    messagebox.showinfo("AI 链接已建立", f"数据已下载: {fname}\n区域: {region}")
            else:
                self.ai_status.config(text="链接错误", fg=c.COLOR_SECONDARY)
                messagebox.showerror("错误", "AI 数据链接失败。")
            self.ai_btn.config_state(tk.NORMAL)
        self.root.after(0, _finish)

    # --- 文件与数据管理 ---
    def load_local_files(self):
        if not os.path.exists(self.resource_dir): os.makedirs(self.resource_dir)
        
        # 清除旧卡片
        for card in self.file_cards:
            card.destroy()
        self.file_cards = []
        self.all_files_data = {}
        self.selected_file_card = None

        for filename in sorted(os.listdir(self.resource_dir)):
            if filename.endswith(".txt"):
                card = FileCard(self.file_frame, filename, self)
                card.pack(fill="x", pady=2, padx=5)
                self.file_cards.append(card)
                self.all_files_data[filename] = parse_data(os.path.join(self.resource_dir, filename))

    def on_file_card_selected(self, card):
        # 取消之前的选中
        if self.selected_file_card:
            self.selected_file_card.set_selected(False)
        
        # 设置新的选中
        self.selected_file_card = card
        card.set_selected(True)
        
        # 加载数据
        fname = card.filename
        data, custom_title = self.all_files_data[fname]
        self.set_active_data(data, (custom_title if custom_title else fname).upper())

    def import_and_save_file(self):
        path = filedialog.askopenfilename(filetypes=[("文本文件", "*.txt")])
        if path and validate_file_format(path):
            fname = os.path.basename(path)
            dest = os.path.join(self.resource_dir, fname)
            shutil.copy(path, dest)
            self.load_local_files()
            messagebox.showinfo("成功", f"文件已加载并保存到 {dest}")

    def open_merge_dialog(self):
        files = list(self.all_files_data.keys())
        if files: MergeDialog(self.root, files, self.merge_files)

    def merge_files(self, selected_files):
        merged_data = {}
        found_titles = []
        for fname in selected_files:
            data, title = self.all_files_data[fname]
            if title: found_titles.append(title)
            for city, subs in data.items():
                if city not in merged_data: merged_data[city] = subs.copy()
                else:
                    for sub, val in subs.items(): merged_data[city][sub] = merged_data[city].get(sub, 0.0) + val
        target_name = selected_files[0]
        final_title = found_titles[0] if len(found_titles) == 1 else (self.all_files_data[target_name][1] or target_name)
        if save_data_to_file(os.path.join(self.resource_dir, target_name), merged_data, final_title):
            for f in selected_files[1:]: os.remove(os.path.join(self.resource_dir, f))
            self.load_local_files()
            self.set_active_data(merged_data, final_title.upper())

    def delete_selected_files(self):
        if self.selected_file_card and messagebox.askyesno("确认", "确定要从删除此文件吗？"):
            fname = self.selected_file_card.filename
            os.remove(os.path.join(self.resource_dir, fname))
            self.load_local_files()
            self.current_data = {}
            self.refresh_sidebar()
            self.draw_chart()

    def set_active_data(self, data, title):
        self.current_data = data
        self.included_cities = list(data.keys())
        self.excluded_cities = []
        self.excluded_subs = {} # 重置所有子区域排除状态
        self.detail_city = None
        self.title_var.set(title)
        self.refresh_sidebar()
        self.draw_chart()

    # --- 侧边栏与渲染 ---
    def refresh_sidebar(self):
        for f in (self.inc_frame, self.exc_frame):
            for w in f.winfo_children(): w.destroy()
        
        if self.detail_city:
            # 明细模式：显示子区域卡片
            subs = self.current_data.get(self.detail_city, {})
            excluded = self.excluded_subs.get(self.detail_city, [])
            for sub_name, val in sorted(subs.items()):
                card_text = f"{sub_name}: {val:.1f}mm"
                if sub_name in excluded:
                    DraggableCard(self.exc_frame, text=card_text, city_name=sub_name, app=self).pack(fill="x", pady=2, padx=5)
                else:
                    DraggableCard(self.inc_frame, text=card_text, city_name=sub_name, app=self).pack(fill="x", pady=2, padx=5)
        else:
            # 主模式：显示城市卡片
            for city in sorted(self.included_cities):
                DraggableCard(self.inc_frame, text=city, city_name=city, app=self).pack(fill="x", pady=2, padx=5)
            for city in sorted(self.excluded_cities):
                DraggableCard(self.exc_frame, text=city, city_name=city, app=self).pack(fill="x", pady=2, padx=5)

    def move_city(self, name, to_inc):
        if self.detail_city:
            # 明细模式：操作子区域
            if self.detail_city not in self.excluded_subs:
                self.excluded_subs[self.detail_city] = []
            
            excluded = self.excluded_subs[self.detail_city]
            if to_inc:
                if name in excluded: excluded.remove(name)
            else:
                if name not in excluded: excluded.append(name)
        else:
            # 主模式：操作城市
            if to_inc:
                if name in self.excluded_cities: self.excluded_cities.remove(name); self.included_cities.append(name)
            else:
                if name in self.included_cities: self.included_cities.remove(name); self.excluded_cities.append(name)
            if not to_inc and self.detail_city == name: self.show_main_view()
            
        self.refresh_sidebar()
        self.draw_chart()

    def move_all(self, to_inc):
        if self.detail_city:
            # 明细模式：全部加入/排除子区域
            if to_inc:
                self.excluded_subs[self.detail_city] = []
            else:
                self.excluded_subs[self.detail_city] = list(self.current_data[self.detail_city].keys())
        else:
            # 主模式：全部加入/排除城市
            if to_inc: 
                self.included_cities.extend(self.excluded_cities)
                self.excluded_cities = []
            else: 
                self.excluded_cities.extend(self.included_cities)
                self.included_cities = []
                self.show_main_view()
        
        self.refresh_sidebar()
        self.draw_chart()

    def draw_chart(self):
        self.canvas.delete("all")
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 100 or h < 100 or not self.current_data:
            self.canvas.create_text(w/2, h/2, text="[ 插入硬币 / 加载数据 ]", font=c.FONT_TITLE, fill=c.COLOR_BORDER)
            return

        plot_data = []
        if self.detail_city:
            self.back_btn_frame.pack(side=tk.LEFT)
            excluded = self.excluded_subs.get(self.detail_city, [])
            for sub, val in self.current_data.get(self.detail_city, {}).items():
                if sub not in excluded:
                    plot_data.append((sub, val))
        else:
            self.back_btn_frame.pack_forget()
            for city in self.included_cities: plot_data.append((city, sum(self.current_data[city].values())))

        if not plot_data: return
        plot_data.sort(key=lambda x: x[1], reverse=True)

        ml, mr, mt, mb = 80, 40, 80, 100
        cw, ch = w - ml - mr, h - mt - mb
        max_val = max(v for _, v in plot_data) * 1.1 if plot_data else 1
        bw = (cw / len(plot_data)) * 0.7
        gap = (cw / len(plot_data)) * 0.3

        # 辅助线与刻度
        for i in range(5):
            y = h - mb - (i * 0.25 * ch)
            self.canvas.create_line(ml, y, w - mr, y, fill="#333333", dash=(1, 2))
            self.canvas.create_text(ml - 15, y, text=f"{int(max_val * i * 0.25)}", font=c.FONT_PIXEL, fill="#888888", anchor="e")

        # 坐标轴 (加粗像素感)
        self.canvas.create_line(ml, h - mb, w - mr, h - mb, fill=c.COLOR_BORDER_HL, width=3)
        self.canvas.create_line(ml, mt-20, ml, h - mb, fill=c.COLOR_BORDER_HL, width=3)

        for i, (name, val) in enumerate(plot_data):
            x0, y0 = ml + i * (bw + gap) + gap/2, h - mb - (val / max_val * ch)
            x1, y1 = x0 + bw, h - mb
            
            if self.clear_mode:
                # 清晰模式：现代风格柱子
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=c.COLOR_BAR, outline=c.COLOR_BAR, width=1, tags=("bar", name))
                text_color = "black" if self.current_theme == "light" else c.COLOR_FG
                self.canvas.create_text((x0+x1)/2, y1 + 30, text=name, font=c.FONT_PIXEL, 
                                        angle=45 if len(plot_data)>8 else 0, fill=text_color)
                self.canvas.create_text((x0+x1)/2, y0 - 25, text=f"{val:.0f}", font=c.FONT_PIXEL, fill=text_color)
            else:
                # 像素风格柱子 (实色块 + 高亮边缘 + 像素阴影)
                self.canvas.create_rectangle(x0+4, y0+4, x1+4, y1, fill=c.COLOR_SHADOW, outline="") # 阴影
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=c.COLOR_BAR, outline=c.COLOR_BG, width=1, tags=("bar", name))
                
                # 顶部和左侧像素高亮
                self.canvas.create_line(x0+1, y0+1, x1-1, y0+1, fill="#FFFFFF")
                self.canvas.create_line(x0+1, y0+1, x0+1, y1-1, fill="#FFFFFF")
                
                # 文字标签
                text_color = "black" if self.current_theme == "light" else c.COLOR_FG
                self.canvas.create_text((x0+x1)/2, y1 + 30, text=name, font=c.FONT_PIXEL, 
                                        angle=45 if len(plot_data)>8 else 0, fill=text_color)
                self.canvas.create_text((x0+x1)/2, y0 - 25, text=f"{val:.0f}", font=c.FONT_PIXEL, fill=text_color)

        # 扫描线效果 (Scanlines)
        if not self.clear_mode: # 清晰模式下不显示扫描线
            for y in range(0, h, 3):
                self.canvas.create_line(0, y, w, y, fill="#000000", stipple="gray25", state="disabled")

    def on_canvas_click(self, event):
        item = self.canvas.find_closest(event.x, event.y)
        tags = self.canvas.gettags(item)
        if "bar" in tags:
            self._drag_item, self._drag_city, self._drag_start = item, tags[1], (event.x, event.y)
            self.canvas.itemconfig(item, fill=c.COLOR_SECONDARY)

    def on_canvas_drag(self, event):
        if hasattr(self, "_drag_item"):
            self.canvas.move(self._drag_item, event.x - self._drag_start[0], event.y - self._drag_start[1])
            self._drag_start = (event.x, event.y)

    def on_canvas_drop(self, event):
        if hasattr(self, "_drag_item"):
            rx, ry = self.canvas.winfo_rootx() + event.x, self.canvas.winfo_rooty() + event.y
            
            # 检查是否拖入活跃区域
            inc_x, inc_y = self.inc_outer_frame.winfo_rootx(), self.inc_outer_frame.winfo_rooty()
            inc_w, inc_h = self.inc_outer_frame.winfo_width(), self.inc_outer_frame.winfo_height()
            
            # 检查是否拖入排除区域
            exc_x, exc_y = self.exc_outer_frame.winfo_rootx(), self.exc_outer_frame.winfo_rooty()
            exc_w, exc_h = self.exc_outer_frame.winfo_width(), self.exc_outer_frame.winfo_height()
            
            if inc_x <= rx <= inc_x + inc_w and inc_y <= ry <= inc_y + inc_h:
                self.move_city(self._drag_city, True)
            elif exc_x <= rx <= exc_x + exc_w and exc_y <= ry <= exc_y + exc_h:
                self.move_city(self._drag_city, False)
            else:
                self.draw_chart()
            del self._drag_item

    def on_canvas_double_click(self, event):
        item = self.canvas.find_closest(event.x, event.y)
        tags = self.canvas.gettags(item)
        if "bar" in tags and not self.detail_city: self.show_detail(tags[1])

    def _on_mousewheel(self, event, widget):
        """通用滚轮滚动处理方法，仅在溢出时生效"""
        # 检查是否溢出 (通过 scrollregion 和 winfo_height)
        scroll_region = widget.cget("scrollregion")
        if not scroll_region: return
        
        # 兼容处理：有些版本 cget 返回的是字符串，有些是元组
        if isinstance(scroll_region, str):
            _, _, _, total_h = map(float, scroll_region.split())
        else:
            _, _, _, total_h = scroll_region
            
        visible_h = widget.winfo_height()
        
        if total_h <= visible_h:
            return # 未溢出，不触发滚动

        if event.num == 5 or event.delta < 0:
            widget.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            widget.yview_scroll(-1, "units")

    def _update_scrollbar_visibility(self, canvas, scrollbar, frame):
        """更新滚动条可见性"""
        frame.update_idletasks()
        canvas.update_idletasks()
        
        # 获取内容高度
        content_h = frame.winfo_reqheight()
        # 获取容器高度
        visible_h = canvas.winfo_height()
        
        if content_h > visible_h:
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        else:
            scrollbar.pack_forget()
        
        # 同时更新 scrollregion
        canvas.configure(scrollregion=(0, 0, frame.winfo_reqwidth(), content_h))

    def show_detail(self, city): 
        self.detail_city = city
        self.refresh_sidebar()
        self.draw_chart()

    def show_main_view(self): 
        self.detail_city = None
        self.refresh_sidebar()
        self.draw_chart()
