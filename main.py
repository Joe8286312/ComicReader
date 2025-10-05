import os
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from tkinter import Canvas, Frame, Button, Scrollbar
import  customtkinter as ctk
from customtkinter import AppearanceModeTracker   # 官方追踪器

# -------------------- 常量 --------------------
NAV_WIDTH = 180
THUMB_H = 150
SAVE_DELAY = 200  # ms


class ComicReader:
    def __init__(self, root):
        self.root = root
        self.root.title("ComicReader")
        self.index = 0
        self.imgs = []          # 懒加载容器
        self.img_paths = []     # 只存路径
        self.thumb_tkimgs = []
        self.nav_btns = []
        self.current_tkimg = None
        self.zip_path = ""
        self.progress_path = ""
        # 设置窗口图标
        self._set_window_icon()
        self._build_ui()
        self.load_zip()
        self.root.focus_set()
        self.root.focus_force()
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(lambda: self.root.attributes('-topmost', False))
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 居中显示
        self._center_window(1000, 700)

    # -------------------- 加载入口 --------------------
    def load_zip(self):
        # 清旧导航
        for w in self.nav_inner.winfo_children():
            w.destroy()
        self.nav_btns.clear()
        self.thumb_tkimgs.clear()

        path = filedialog.askopenfilename(filetypes=[("Zip", "*.zip")])
        if not path:
            exit()
        if not zipfile.is_zipfile(path):
            messagebox.showerror("无效文件", "所选文件不是合法 ZIP")
            return self.load_zip()
        self.zip_path = path
        self.progress_path = path + ".progress"
        try:
            self._load_images()
            self._build_nav()
            self._load_progress()
            self.root.update_idletasks()
            self._update_status(path)
            self.root.after(10, self.show)
        except Exception as e:
            messagebox.showerror("加载失败", str(e))
            return self.load_zip()

    # -------------------- 拆：加载图片列表 --------------------
    def _load_images(self):
        with zipfile.ZipFile(self.zip_path) as zf:
            names = sorted(n for n in zf.namelist()
                           if n.lower().endswith(('.jpg', '.png', '.jpeg')))
            if not names:
                raise ValueError("压缩包内未找到图片")
            self.img_paths = names
            self.imgs = [None] * len(names)

    # -------------------- 拆：建导航缩略图 --------------------
    def _build_nav(self):
        self.thumb_tkimgs.clear()
        for idx, img_path in enumerate(self.img_paths):
            # 缩略图也按需加载
            with zipfile.ZipFile(self.zip_path) as zf:
                thumb = Image.open(zf.open(img_path)) \
                    .resize((int(Image.open(zf.open(img_path)).width * THUMB_H /
                                 Image.open(zf.open(img_path)).height), THUMB_H),
                            Image.LANCZOS)
                tk_img = ctk.CTkImage(thumb, size=(thumb.width, thumb.height))
            self.thumb_tkimgs.append(tk_img)
            btn = ctk.CTkButton(
                self.nav_inner,
                image=tk_img,
                text="",
                width=THUMB_H + 20,
                height=THUMB_H,
                fg_color="transparent",  # 背景透明
                border_width=2,  # 替代 bd
                border_color="white",  # 边框颜色
                hover_color="#444444",  # 悬停颜色
                command=lambda i=idx: self.jump_to(i)
            )
            btn.pack(fill='x', padx=4, pady=4)
            self.nav_btns.append(btn)
        self.nav_inner.update_idletasks()
        self.nav_canvas.config(scrollregion=self.nav_canvas.bbox("all"))

    # -------------------- 拆：读进度 --------------------
    def _load_progress(self):
        try:
            if os.path.exists(self.progress_path):
                with open(self.progress_path, 'r', encoding='utf-8') as f:
                    self.index = max(0, min(len(self.img_paths) - 1, int(f.read())))
            else:
                self.index = 0
        except Exception:
            self.index = 0

    # -------------------- 懒加载单张 --------------------
    def _get_image(self, idx):
        if self.imgs[idx] is None:
            with zipfile.ZipFile(self.zip_path) as zf:
                self.imgs[idx] = Image.open(zf.open(self.img_paths[idx]))
        return self.imgs[idx]

    # -------------------- 显示当前页 --------------------
    def show(self):
        if not self.img_paths:
            return
        src = self._get_image(self.index)
        w0, h0 = src.size
        scr_w = max(1, self.root.winfo_width() - NAV_WIDTH)
        scr_h = max(1, self.root.winfo_height())
        scale = min(scr_w / w0, scr_h / h0, 1.0)
        dst = src.resize((int(w0 * scale), int(h0 * scale)), Image.LANCZOS)
        self.current_tkimg = ImageTk.PhotoImage(dst)
        self.label.config(image=self.current_tkimg)
        self.root.title(f"{self.index + 1}/{len(self.img_paths)}  {w0}×{h0}")
        self._update_nav_ui()

    def _update_status(self, zip_path):
        """显示原始大小、zip 大小、压缩率"""
        raw_bytes = 0
        with zipfile.ZipFile(zip_path) as zf:
            for info in zf.infolist():
                raw_bytes += info.file_size  # 未压缩大小
        zip_bytes = os.path.getsize(zip_path)  # 压缩后大小
        ratio = (1 - zip_bytes / raw_bytes) * 100 if raw_bytes else 0

        text = (f"文件：{len(self.img_paths)} 张  |  "
                f"原始：{raw_bytes / 1024 / 1024:.1f} MB  |  "
                f"压缩后：{zip_bytes / 1024 / 1024:.1f} MB  |  "
                f"压缩率：{ratio:.1f}%")
        self.status_lbl.configure(text=text)

    # -------------------- 导航高亮+自动滚动 --------------------
    def _update_nav_ui(self):
        if not self.nav_btns:
            return
        for i, btn in enumerate(self.nav_btns):
            btn.configure(
                fg_color=("red" if i == self.index else "transparent"),
                border_color=("white" if i == self.index else "gray50")
            )
        self.nav_canvas.yview_moveto(self.index / max(1, len(self.nav_btns)))

    # -------------------- 翻页 --------------------
    def flip(self, d):
        self.index = max(0, min(len(self.img_paths) - 1, self.index + d))
        self.show()
        if hasattr(self, '_after_save'):
            self.root.after_cancel(self._after_save)
        self._after_save = self.root.after(SAVE_DELAY, self._write_progress)

    # -------------------- 跳转 --------------------
    def jump_to(self, idx):
        self.index = idx
        self.show()

    # -------------------- 保存进度 --------------------
    def _write_progress(self):
        try:
            with open(self.progress_path, "w", encoding="utf-8") as f:
                f.write(str(self.index))
        except Exception as e:
            if not getattr(self, '_save_warned', False):
                self._save_warned = True
                messagebox.showwarning("保存失败", f"进度文件无法写入：\n{str(e)}")

    # -------------------- 退出 --------------------
    def on_close(self):
        self._write_progress()
        self.root.destroy()

    # -------------------- 滚轮事件 --------------------
    def on_mouse_wheel(self, event):
        self.flip(-1 if event.delta > 0 else 1)

    def _toggle_fullscreen(self, event=None):
        if self.root.attributes("-fullscreen"):
            # 退出全屏
            self.root.state("normal")
            self.root.attributes("-fullscreen", False)
        else:
            # 进入全屏
            self.root.state("zoomed")
            self.root.attributes("-fullscreen", True)
        self.root.update_idletasks()
        self.root.after(100, self.show)

    # -------------------- 文件菜单 --------------------
    def _on_file_menu(self):
        """弹出文件选择对话框，等同于原来的 load_zip"""
        self.load_zip()  # 直接复用你原来的逻辑

    # -------------------- 主题菜单 --------------------
    def _on_theme_menu(self):
        """一键明暗切换，并同步左侧导航颜色"""
        # 1. 切换 CTk 主题
        new_mode = "Dark" if ctk.get_appearance_mode() == "Light" else "Light"
        ctk.set_appearance_mode(new_mode)

        # 2. 同步 tk 原生组件颜色
        self._sync_nav_colors()

    def _sync_nav_colors(self):
        """让 tk.Canvas/tk.Frame 与 CTk 主题保持一致"""
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg = "gray16" if is_dark else "gray95"  # 深/浅背景色
        fg = "gray60" if is_dark else "gray30"  # 按钮边框色

        # ① Canvas 背景
        self.nav_canvas.configure(bg=bg, highlightthickness=0)

        # ② 内部 Frame 背景
        self.nav_inner.configure(bg=bg)

        # ③ 所有缩略图按钮边框
        for btn in self.nav_btns:
            btn.configure(border_color=fg)

        # 2. 菜单栏（CTk 组件）—— 安全取色
        bg_bar = "#2b2b2b" if is_dark else "#dbdbdb"
        self.menubar.configure(fg_color=bg_bar)

    # 菜单居中
    def _center_window(self, width, height):
        """让窗口在屏幕中央"""
        self.root.update_idletasks()  # 先拿到真实尺寸
        scr_w = self.root.winfo_screenwidth()
        scr_h = self.root.winfo_screenheight()
        x = (scr_w - width) // 2
        y = (scr_h - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    # -------------------- UI 搭建 --------------------
    def _build_ui(self):
        # -------------------- 顶部菜单栏 --------------------
        self.menubar = ctk.CTkFrame(self.root, height=40, fg_color="gray20")
        self.menubar.pack(fill="x", padx=5, pady=5)

        # “文件”按钮
        self.file_btn = ctk.CTkButton(
            self.menubar, text="文件", width=60,
            command=self._on_file_menu
        )
        self.file_btn.pack(side="left", padx=5)

        # “主题”按钮
        self.theme_btn = ctk.CTkButton(
            self.menubar, text="主题", width=60,
            command=self._on_theme_menu
        )
        self.theme_btn.pack(side="left", padx=5)

        # 再pack主工作区
        self.paned = tk.PanedWindow(self.root, orient='horizontal', sashwidth=4)
        self.paned.pack(fill='both', expand=True)

        # 左侧导航
        nav_frame = ctk.CTkFrame(self.paned, width=NAV_WIDTH)
        self.paned.add(nav_frame)
        # self.nav_canvas = Canvas(nav_frame, width=NAV_WIDTH)
        self.nav_canvas = tk.Canvas(
            nav_frame,
            width=NAV_WIDTH,
            bg="gray16",  # ← 新增
            highlightthickness=0  # ← 去掉白色边框
        )
        self.nav_canvas.pack(side='left', fill='y', expand=True)
        scroll = Scrollbar(nav_frame, orient='vertical',
                           command=self.nav_canvas.yview)
        scroll.pack(side='right', fill='y')
        self.nav_canvas.config(yscrollcommand=scroll.set)
        # self.nav_inner = Frame(self.nav_canvas)
        self.nav_inner = tk.Frame(
            self.nav_canvas,
            bg="gray16"  # ← 新增
        )
        self.nav_win = self.nav_canvas.create_window(
            (0, 0), window=self.nav_inner, anchor='nw', width=NAV_WIDTH)
        self.nav_canvas.bind_all("<MouseWheel>",
                                 lambda e: self.nav_canvas.yview_scroll(
                                     int(-1 * (e.delta / 120)), "units"))

        # 右侧阅读区
        right_frame = ctk.CTkFrame(self.paned)
        self.paned.add(right_frame)
        self.label = tk.Label(right_frame, bg='black')
        self.label.pack(fill='both', expand=True)

        # 绑定
        self.root.bind("<Left>", lambda e: self.flip(-1))
        self.root.bind("<Right>", lambda e: self.flip(1))
        self.root.bind("<MouseWheel>", self.on_mouse_wheel)
        # 双击切换全屏
        self.root.bind("<Double-Button-1>", self._toggle_fullscreen)
        # esc退出
        self.root.bind("<Escape>", lambda e: self.root.attributes("-fullscreen", False))
        # -------------------- 底部状态栏 --------------------
        self.status = ctk.CTkFrame(self.root, height=28, fg_color="transparent")
        self.status.pack(side="bottom", fill="x", padx=5, pady=2)

        self.status_lbl = ctk.CTkLabel(
            self.status, text="", font=("Segoe UI", 12))
        self.status_lbl.pack(side="left", padx=8)

        # 在 _build_ui() 最后
        self._sync_nav_colors()


    def _set_window_icon(self):
        """跨平台设置窗口图标"""
        icon_path = os.path.join(os.path.dirname(__file__), "app.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)  # Windows
        else:
            # Linux/Mac 可用 png（部分系统需 tk 8.6+）
            icon_path = os.path.join(os.path.dirname(__file__), "app.png")
            if os.path.exists(icon_path):
                self.root.iconphoto(True, tk.PhotoImage(file=icon_path))
        # print(os.path.abspath(icon_path)) # 调试用

# -------------------- 启动 --------------------
if __name__ == "__main__":
    try:
        # root = tk.Tk()
        root = ctk.CTk()
        root.geometry("1000x700")
        ComicReader(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("未捕获异常", f"程序崩溃：\n{str(e)}")