import os
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from tkinter import Canvas, Frame, Button, Scrollbar

# -------------------- 常量 --------------------
NAV_WIDTH = 180
THUMB_H = 150
SAVE_DELAY = 200  # ms


class ComicReader:
    def __init__(self, root):
        self.root = root
        self.root.title("ComicReader-MVP")
        self.index = 0
        self.imgs = []          # 懒加载容器
        self.img_paths = []     # 只存路径
        self.thumb_tkimgs = []
        self.nav_btns = []
        self.current_tkimg = None
        self.zip_path = ""
        self.progress_path = ""

        self._build_ui()
        self.load_zip()
        self.root.focus_set()
        self.root.focus_force()
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(lambda: self.root.attributes('-topmost', False))
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

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
            self.show()
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
                tk_img = ImageTk.PhotoImage(thumb)
            self.thumb_tkimgs.append(tk_img)
            btn = Button(self.nav_inner, image=tk_img,
                         command=lambda i=idx: self.jump_to(i),
                         bd=2, relief='solid')
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

    # -------------------- 导航高亮+自动滚动 --------------------
    def _update_nav_ui(self):
        if not self.nav_btns:
            return
        for i, btn in enumerate(self.nav_btns):
            btn.config(bg='red' if i == self.index else 'SystemButtonFace')
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

    # -------------------- UI 搭建 --------------------
    def _build_ui(self):
        self.paned = tk.PanedWindow(self.root, orient='horizontal', sashwidth=4)
        self.paned.pack(fill='both', expand=True)

        # 左侧导航
        nav_frame = tk.Frame(self.paned, width=NAV_WIDTH)
        self.paned.add(nav_frame)
        self.nav_canvas = Canvas(nav_frame, width=NAV_WIDTH)
        self.nav_canvas.pack(side='left', fill='y', expand=True)
        scroll = Scrollbar(nav_frame, orient='vertical',
                           command=self.nav_canvas.yview)
        scroll.pack(side='right', fill='y')
        self.nav_canvas.config(yscrollcommand=scroll.set)
        self.nav_inner = Frame(self.nav_canvas)
        self.nav_win = self.nav_canvas.create_window(
            (0, 0), window=self.nav_inner, anchor='nw', width=NAV_WIDTH)
        self.nav_canvas.bind_all("<MouseWheel>",
                                 lambda e: self.nav_canvas.yview_scroll(
                                     int(-1 * (e.delta / 120)), "units"))

        # 右侧阅读区
        right_frame = tk.Frame(self.paned)
        self.paned.add(right_frame)
        self.label = tk.Label(right_frame, bg='black')
        self.label.pack(fill='both', expand=True)

        # 绑定
        self.root.bind("<Left>", lambda e: self.flip(-1))
        self.root.bind("<Right>", lambda e: self.flip(1))
        self.root.bind("<MouseWheel>", self.on_mouse_wheel)


# -------------------- 启动 --------------------
if __name__ == "__main__":
    try:
        root = tk.Tk()
        root.geometry("1000x700")
        ComicReader(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("未捕获异常", f"程序崩溃：\n{str(e)}")