import os, zipfile, tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from tkinter import Canvas, Frame, Button, Scrollbar

class ComicReader:
    def __init__(self, root):
        self.root = root
        self.root.title("ComicReader-MVP")
        self.index = 0
        self.imgs = []
        self.thumb_tkimgs = []  # 缩略图对象救生筏
        self.nav_btns = []  # 缩略图按钮救生筏
        self.current_tkimg = None  # 主图救生筏

        # === 1. 先建全部容器 ===
        self._build_ui()  # 新建函数，见下方
        # === 2. 再加载数据 ===
        self.load_zip()
        # === 3. 焦点 & 窗口提升 ===
        self.root.focus_set()
        self.root.focus_force()
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(lambda: self.root.attributes('-topmost', False))

        self.root.after_idle(lambda: self.root.attributes('-topmost', False))

        # ---- 绑定退出 ----
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_zip(self):
        path = filedialog.askopenfilename(filetypes=[("Zip", "*.zip")])
        if not path:
            exit()
        self.zip_path = path                    # ← 新增
        self.progress_path = path + ".progress" # ← 新增

        zf = zipfile.ZipFile(path)
        names = sorted(n for n in zf.namelist()
                       if n.lower().endswith(('.jpg', '.png', '.jpeg')))
        self.imgs = [Image.open(zf.open(n)) for n in names]

        # —— 读取进度 ——
        if os.path.exists(self.progress_path):
            self.index = int(open(self.progress_path).read())
        else:
            self.index = 0

        self.show()
        # 读进度
        progress = path + ".progress"
        if os.path.exists(progress):
            self.index = int(open(progress).read())
            self.show()
        self.nav_btns.clear()   # 防止重复加载
        # ===== PPT 式缩略图导航栏 =====
        self.nav_tkimgs = []   # 缩略图对象救生筏
        # self.nav_btns   = []   # 按钮对象救生筏
        h_nav = 150            # 统一缩略图高度
        for idx, img in enumerate(self.imgs):
            tk_img = ImageTk.PhotoImage(
                img.resize((int(img.width * h_nav / img.height), h_nav),
                           Image.LANCZOS))
            self.nav_tkimgs.append(tk_img)

            btn = Button(self.nav_inner, image=tk_img,
                         command=lambda i=idx: self.jump_to(i),
                         bd=2, relief='solid')
            btn.pack(fill='x', padx=4, pady=4)
            self.nav_btns.append(btn)

        # self.jump_to(0)  # 默认高亮第 0 页
        # ➜ 关键：刷新滚动区域
        self.nav_inner.update_idletasks()
        self.nav_canvas.config(scrollregion=self.nav_canvas.bbox("all"))

    def show(self):
        if not self.imgs:
            return
        src = self.imgs[self.index]
        w0, h0 = src.size
        scr_w = self.root.winfo_width()
        scr_h = self.root.winfo_height()
        scale = min(scr_w / w0, scr_h / h0, 1.0)
        new_w, new_h = int(w0 * scale), int(h0 * scale)
        dst = src.resize((new_w, new_h), Image.LANCZOS)

        self.current_tkimg = ImageTk.PhotoImage(dst)  # 救生筏
        self.label.config(image=self.current_tkimg)
        self.root.title(f"{self.index + 1}/{len(self.imgs)}  {w0}×{h0}")

        # ===== 新导航栏高亮 + 自动滚动 =====
        if self.nav_btns:  # 防止空列表
            for i, btn in enumerate(self.nav_btns):
                btn.config(bg='red' if i == self.index else 'SystemButtonFace')
            self.nav_canvas.update_idletasks()
            self.nav_canvas.yview_moveto(self.index / max(1, len(self.nav_btns)))

    def flip(self, d):
        self.index = max(0, min(len(self.imgs) - 1, self.index + d))
        self.show()
        # --- 自动进度保存 ---
        self._auto_save_progress()

    def on_close(self):
        """正常退出时自动保存当前页码"""
        with open(self.progress_path, "w", encoding="utf-8") as f:
            f.write(str(self.index))
        self.root.destroy()

    def on_mouse_wheel(self, event):
        # Windows 事件 delta 是 ±120，Linux/Mac 可能不同，统一用符号
        if event.delta > 0:
            self.flip(-1)   # 向上滚 → 上一页
        else:
            self.flip(1)    # 向下滚 → 下一页

    # ↓↓↓ 回调必须先于绑定定义 ↓↓↓
    def on_thumb_select(self, event):
        if self.lb.curselection():
            self.index = self.lb.curselection()[0]
            self.show()

    def make_thumb(self, img):
        """统一高度 120 px，宽度等比"""
        h = 120
        w = int(img.width * h / img.height)
        return img.resize((w, h), Image.LANCZOS)

    def _build_ui(self):
        # 左右主分割
        self.paned = tk.PanedWindow(self.root, orient='horizontal', sashwidth=4)
        self.paned.pack(fill='both', expand=True)

        # === 左侧 PPT 风格缩略图导航栏 ===
        nav_frame = tk.Frame(self.paned, width=180)
        self.paned.add(nav_frame)

        # 画布 + 滚动条
        self.nav_canvas = Canvas(nav_frame, width=180)
        self.nav_canvas.pack(side='left', fill='y', expand=True)
        scroll = Scrollbar(nav_frame, orient='vertical',
                           command=self.nav_canvas.yview)
        scroll.pack(side='right', fill='y')
        self.nav_canvas.config(yscrollcommand=scroll.set)

        # 内部容器，真正放按钮
        self.nav_inner = Frame(self.nav_canvas)
        self.nav_win = self.nav_canvas.create_window(
            (0, 0), window=self.nav_inner, anchor='nw', width=180)

        # 让鼠标滚轮也能滚动导航栏
        self.nav_canvas.bind_all("<MouseWheel>",
                                 lambda e: self.nav_canvas.yview_scroll(
                                     int(-1 * (e.delta / 120)), "units"))

        # === 右侧阅读区（你原有代码不动） ===
        right_frame = tk.Frame(self.paned)
        self.paned.add(right_frame)
        self.label = tk.Label(right_frame, bg='black')
        self.label.pack(fill='both', expand=True)

        # 键盘/滚轮绑定（保持原样）
        self.root.bind("<Left>",  lambda e: self.flip(-1))
        self.root.bind("<Right>", lambda e: self.flip(1))
        self.root.bind("<MouseWheel>", self.on_mouse_wheel)

    def jump_to(self, idx):
        self.index = idx
        self.show()
        # 高亮当前按钮
        for i, btn in enumerate(self.nav_btns):
            btn.config(bg='red' if i == idx else 'SystemButtonFace')
        # 自动滚动到可见区域
        self.nav_canvas.update_idletasks()
        self.nav_canvas.yview_moveto(idx / max(1, len(self.nav_btns)))

    def _auto_save_progress(self):
        """延迟 500ms 写盘（连续翻页只写最后一次）"""
        if hasattr(self, '_after_save'):
            self.root.after_cancel(self._after_save)
        self._after_save = self.root.after(500, self._write_progress)

    def _write_progress(self):
        """立即写盘"""
        with open(self.progress_path, "w", encoding="utf-8") as f:
            f.write(str(self.index))

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("800x600")
    ComicReader(root)
    root.mainloop()
