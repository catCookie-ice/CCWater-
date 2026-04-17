import tkinter as tk
from tkinter import messagebox
import constants as c

# --- 复古街机风格按钮组件 ---
class ArcadeButton(tk.Frame):
    def __init__(self, parent, text, command, color=None, **kwargs):
        if color is None: color = c.COLOR_FG
        super().__init__(parent, bg=c.COLOR_BG, **kwargs)
        self.command = command
        self.color = color
        self.pressed = False
        
        # 阴影层
        self.shadow = tk.Frame(self, bg=c.COLOR_SHADOW)
        self.shadow.place(x=2, y=2, relwidth=1, relheight=1)
        
        # 按钮层
        self.btn_body = tk.Frame(self, bg=c.COLOR_BG, bd=2, relief="solid", highlightthickness=1, highlightbackground=color)
        self.btn_body.place(x=0, y=0, relwidth=1, relheight=1)
        
        self.label = tk.Label(self.btn_body, text=f" {text} ", font=c.FONT_PIXEL, bg=c.COLOR_BG, fg=color)
        self.label.pack(expand=True, fill="both")
        
        # 事件绑定
        for widget in (self.btn_body, self.label):
            widget.bind("<Button-1>", self._on_press)
            widget.bind("<ButtonRelease-1>", self._on_release)
            widget.bind("<Enter>", lambda e: self.btn_body.config(bg=c.COLOR_SHADOW))
            widget.bind("<Leave>", lambda e: self.btn_body.config(bg=c.COLOR_BG))

    def _on_press(self, event):
        self.pressed = True
        self.btn_body.place(x=2, y=2)
        self.label.config(fg=c.COLOR_BG, bg=self.color)
        self.btn_body.config(bg=self.color)

    def _on_release(self, event):
        if self.pressed:
            self.pressed = False
            self.btn_body.place(x=0, y=0)
            self.label.config(fg=self.color, bg=c.COLOR_BG)
            self.btn_body.config(bg=c.COLOR_BG)
            self.command()

    def config_state(self, state):
        if state == tk.DISABLED:
            self.label.config(fg="#555555")
            self.btn_body.config(highlightbackground="#555555")
            for widget in (self.btn_body, self.label):
                widget.unbind("<Button-1>")
                widget.unbind("<ButtonRelease-1>")
        else:
            self.label.config(fg=self.color)
            self.btn_body.config(highlightbackground=self.color)
            for widget in (self.btn_body, self.label):
                widget.bind("<Button-1>", self._on_press)
                widget.bind("<ButtonRelease-1>", self._on_release)

    def update_colors(self, new_color=None):
        if new_color:
            self.color = new_color
        self.btn_body.config(bg=c.COLOR_BG, highlightbackground=self.color)
        self.label.config(bg=c.COLOR_BG, fg=self.color)
        self.shadow.config(bg=c.COLOR_SHADOW)

# --- UI 组件 ---
class MergeDialog(tk.Toplevel):
    def __init__(self, parent, file_list, callback):
        super().__init__(parent)
        self.title("合并文件")
        self.geometry("450x550")
        self.configure(bg=c.COLOR_BG)
        self.callback = callback
        self.file_vars = {}
        self.order_labels = {}
        self.selected_order = []

        # 双层边框
        main_frame = tk.Frame(self, bg=c.COLOR_BG, bd=2, relief="solid", highlightbackground=c.COLOR_BORDER_HL, highlightthickness=2)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(main_frame, text="[ 选择要合并的文件 ]", font=c.FONT_TITLE, bg=c.COLOR_BG, fg=c.COLOR_ACCENT).pack(pady=(20, 10))
        
        container = tk.Frame(main_frame, bg=c.COLOR_BG)
        container.pack(fill="both", expand=True, padx=20, pady=10)
        
        canvas = tk.Canvas(container, bg=c.COLOR_BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview, bg=c.COLOR_BG)
        self.scrollable_frame = tk.Frame(canvas, bg=c.COLOR_BG)

        # 核心逻辑：监听内容变化和窗口变化以更新滚动条
        self.scrollable_frame.bind("<Configure>", lambda e: self._update_scrollbar_visibility(canvas, scrollbar, self.scrollable_frame))
        canvas.bind("<Configure>", lambda e: self._update_scrollbar_visibility(canvas, scrollbar, self.scrollable_frame))

        canvas_window = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 动态调整内部框架宽度
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width), add="+")

        for filename in file_list:
            f_frame = tk.Frame(self.scrollable_frame, bg=c.COLOR_BG, pady=5)
            f_frame.pack(fill="x")
            
            var = tk.BooleanVar()
            self.file_vars[filename] = var
            cb = tk.Checkbutton(f_frame, text=filename.upper(), variable=var, font=c.FONT_PIXEL,
                                bg=c.COLOR_BG, fg=c.COLOR_FG, selectcolor=c.COLOR_BG,
                                activebackground=c.COLOR_BG, activeforeground=c.COLOR_ACCENT,
                                command=lambda f=filename: self.on_check(f))
            cb.pack(side="left")
            
            order_label = tk.Label(f_frame, text="", fg=c.COLOR_SECONDARY, font=c.FONT_PIXEL, bg=c.COLOR_BG)
            order_label.pack(side="right", padx=10)
            self.order_labels[filename] = order_label

            # 滚轮支持绑定到子组件
            for widget in (f_frame, cb, order_label):
                widget.bind("<MouseWheel>", lambda e: self._on_mousewheel(e, canvas))
                widget.bind("<Button-4>", lambda e: self._on_mousewheel(e, canvas))
                widget.bind("<Button-5>", lambda e: self._on_mousewheel(e, canvas))

        canvas.pack(side="left", fill="both", expand=True)
        # 初始时不 pack scrollbar

        # 滚轮支持
        for widget in (canvas, self.scrollable_frame):
            widget.bind("<MouseWheel>", lambda e: self._on_mousewheel(e, canvas))
            widget.bind("<Button-4>", lambda e: self._on_mousewheel(e, canvas))
            widget.bind("<Button-5>", lambda e: self._on_mousewheel(e, canvas))

        self.submit_btn = ArcadeButton(main_frame, "执行合并", self.submit, color=c.COLOR_FG, height=45)
        self.submit_btn.pack(fill="x", padx=40, pady=(20, 20))
        self.apply_theme() # 初始应用主题

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

    def on_check(self, filename):
        if self.file_vars[filename].get():
            if filename not in self.selected_order: self.selected_order.append(filename)
        else:
            if filename in self.selected_order: self.selected_order.remove(filename)
        self.refresh_order_labels()

    def refresh_order_labels(self):
        for label in self.order_labels.values(): label.config(text="")
        for i, filename in enumerate(self.selected_order):
            self.order_labels[filename].config(text=f"P{i+1}")

    def apply_theme(self):
        self.config(bg=c.COLOR_BG)
        for widget in self.winfo_children():
            if isinstance(widget, tk.Frame): # main_frame
                widget.config(bg=c.COLOR_BG, highlightbackground=c.COLOR_BORDER_HL)
                for sub_widget in widget.winfo_children():
                    if isinstance(sub_widget, tk.Label):
                        sub_widget.config(bg=c.COLOR_BG, fg=c.COLOR_ACCENT if "[ 选择要合并的文件 ]" in sub_widget.cget("text") else c.COLOR_FG)
                    elif isinstance(sub_widget, tk.Frame): # container
                        sub_widget.config(bg=c.COLOR_BG)
                        for canvas_widget in sub_widget.winfo_children():
                            if isinstance(canvas_widget, tk.Canvas):
                                canvas_widget.config(bg=c.COLOR_BG)
                                for frame_widget in canvas_widget.winfo_children(): # scrollable_frame
                                    if isinstance(frame_widget, tk.Frame):
                                        frame_widget.config(bg=c.COLOR_BG)
                                        for f_frame in frame_widget.winfo_children():
                                            if isinstance(f_frame, tk.Frame):
                                                f_frame.config(bg=c.COLOR_BG)
                                                for cb_widget in f_frame.winfo_children():
                                                    if isinstance(cb_widget, tk.Checkbutton):
                                                        cb_widget.config(bg=c.COLOR_BG, fg=c.COLOR_FG, selectcolor=c.COLOR_BG, activebackground=c.COLOR_BG, activeforeground=c.COLOR_ACCENT)
                                                    elif isinstance(cb_widget, tk.Label):
                                                        cb_widget.config(bg=c.COLOR_BG, fg=c.COLOR_SECONDARY)
                    elif isinstance(sub_widget, ArcadeButton):
                        sub_widget.update_colors(c.COLOR_FG)

    def submit(self):
        selected_files = [f for f in self.selected_order if self.file_vars[f].get()]
        if len(selected_files) < 2:
            messagebox.showwarning("警告", "至少选择两个文件进行合并！")
            return
        if messagebox.askyesno("确认", f"将数据合并到 {selected_files[0]}?\n其他文件将被删除！"):
            self.callback(selected_files)
            self.destroy()

class FileCard(tk.Frame):
    def __init__(self, parent, filename, app, **kwargs):
        super().__init__(parent, bg=c.COLOR_BG, bd=1, relief="solid", **kwargs)
        self.filename = filename
        self.app = app
        self.selected = False
        
        # 像素风格边框
        self.config(highlightbackground=c.COLOR_BORDER, highlightthickness=1)
        
        # 装饰性像素点 (右下角)
        self.dot = tk.Frame(self, bg=c.COLOR_FG, width=4, height=4)
        self.dot.place(relx=1.0, rely=1.0, x=-6, y=-6)

        self.label = tk.Label(self, text=filename.upper(), font=c.FONT_PIXEL, bg=c.COLOR_BG, fg=c.COLOR_FG, padx=10, pady=8)
        self.label.pack(fill="both", expand=True)
        
        for widget in (self, self.label, self.dot):
            widget.bind("<Button-1>", self.on_click)
            widget.bind("<Double-Button-1>", self.on_double_click)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            
            # 滚轮支持 (绑定到父 Canvas)
            widget.bind("<MouseWheel>", lambda e: self.app._on_mousewheel(e, self.app.file_canvas))
            widget.bind("<Button-4>", lambda e: self.app._on_mousewheel(e, self.app.file_canvas))
            widget.bind("<Button-5>", lambda e: self.app._on_mousewheel(e, self.app.file_canvas))

    def _on_enter(self, event):
        if not self.selected:
            self.config(highlightbackground=c.COLOR_ACCENT, highlightthickness=2)
            self.label.config(fg=c.COLOR_ACCENT)

    def _on_leave(self, event):
        if not self.selected:
            self.config(highlightbackground=c.COLOR_BORDER, highlightthickness=1)
            self.label.config(fg=c.COLOR_FG)

    def on_click(self, event):
        self.app.on_file_card_selected(self)

    def on_double_click(self, event):
        # 暂时没有双击逻辑，可以预留
        pass

    def set_selected(self, selected):
        self.selected = selected
        if selected:
            self.config(highlightbackground=c.COLOR_ACCENT, highlightthickness=2, bg=c.COLOR_SHADOW)
            self.label.config(fg=c.COLOR_ACCENT, bg=c.COLOR_SHADOW)
            self.dot.config(bg=c.COLOR_ACCENT)
        else:
            self.config(highlightbackground=c.COLOR_BORDER, highlightthickness=1, bg=c.COLOR_BG)
            self.label.config(fg=c.COLOR_FG, bg=c.COLOR_BG)
            self.dot.config(bg=c.COLOR_FG)

    def update_colors(self):
        self.set_selected(self.selected)

class DraggableCard(tk.Frame):
    def __init__(self, parent, text, city_name, app, **kwargs):
        super().__init__(parent, bg=c.COLOR_BG, bd=1, relief="solid", **kwargs)
        self.city_name = city_name
        self.app = app
        
        # 像素风格边框
        self.config(highlightbackground=c.COLOR_BORDER, highlightthickness=1)
        
        # 装饰性像素点
        self.dot = tk.Frame(self, bg=c.COLOR_FG, width=4, height=4)
        self.dot.place(x=2, y=2)

        self.label = tk.Label(self, text=text, font=c.FONT_PIXEL, bg=c.COLOR_BG, fg=c.COLOR_FG, padx=10, pady=5)
        self.label.pack(fill="both", expand=True)
        
        for widget in (self, self.label, self.dot):
            widget.bind("<Button-1>", self.on_start_drag)
            widget.bind("<B1-Motion>", self.on_drag)
            widget.bind("<ButtonRelease-1>", self.on_drop)
            widget.bind("<Double-Button-1>", self.on_double_click)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            
            # 滚轮支持 (绑定到父 Canvas)
            widget.bind("<MouseWheel>", lambda e: self.app._on_mousewheel(e, self.master.master))
            widget.bind("<Button-4>", lambda e: self.app._on_mousewheel(e, self.master.master))
            widget.bind("<Button-5>", lambda e: self.app._on_mousewheel(e, self.master.master))

    def _on_enter(self, event):
        self.config(highlightbackground=c.COLOR_ACCENT, highlightthickness=2)
        self.label.config(fg=c.COLOR_ACCENT)
        self.dot.config(bg=c.COLOR_ACCENT)

    def _on_leave(self, event):
        self.config(highlightbackground=c.COLOR_BORDER, highlightthickness=1)
        self.label.config(fg=c.COLOR_FG)
        self.dot.config(bg=c.COLOR_FG)

    def on_start_drag(self, event):
        self._drag_data = {"x": event.x, "y": event.y}
        self.config(cursor="fleur")
        self.lift()

    def on_drag(self, event):
        x = self.winfo_x() + (event.x - self._drag_data["x"])
        y = self.winfo_y() + (event.y - self._drag_data["y"])
        self.place(x=x, y=y)

    def on_drop(self, event):
        self.config(cursor="")
        x, y = self.winfo_rootx() + event.x, self.winfo_rooty() + event.y
        
        # 活跃区域边界
        inc_x, inc_y = self.app.inc_outer_frame.winfo_rootx(), self.app.inc_outer_frame.winfo_rooty()
        inc_w, inc_h = self.app.inc_outer_frame.winfo_width(), self.app.inc_outer_frame.winfo_height()
        
        # 排除区域边界
        exc_x, exc_y = self.app.exc_outer_frame.winfo_rootx(), self.app.exc_outer_frame.winfo_rooty()
        exc_w, exc_h = self.app.exc_outer_frame.winfo_width(), self.app.exc_outer_frame.winfo_height()
        
        # 图表区域 (中间工作区) 边界
        chart_x, chart_y = self.app.chart_container.winfo_rootx(), self.app.chart_container.winfo_rooty()
        chart_w, chart_h = self.app.chart_container.winfo_width(), self.app.chart_container.winfo_height()
        
        if (inc_x <= x <= inc_x + inc_w and inc_y <= y <= inc_y + inc_h) or \
           (chart_x <= x <= chart_x + chart_w and chart_y <= y <= chart_y + chart_h):
            self.app.move_city(self.city_name, True)
        elif exc_x <= x <= exc_x + exc_w and \
             exc_y <= y <= exc_y + exc_h:
            self.app.move_city(self.city_name, False)
        else:
            self.app.refresh_sidebar()

    def on_double_click(self, event):
        self.app.show_detail(self.city_name)

    def update_colors(self):
        self.config(bg=c.COLOR_BG, highlightbackground=c.COLOR_BORDER)
        self.dot.config(bg=c.COLOR_FG)
        self.label.config(bg=c.COLOR_BG, fg=c.COLOR_FG)
