import os, zipfile, tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
# 在 __init__ 里，把 self.label  packing 之前插入侧栏
from tkinter import Listbox, Scrollbar, END   # 顶部顺手 import 即可

class ComicReader:
    def __init__(self, root):
        self.root = root
        self.root.title("ComicReader-MVP")
        self.index = 0
        self.imgs = []
        self.thumb_tkimgs = []  # 缩略图对象救生筏
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



    def load_zip(self):
        path = filedialog.askopenfilename(filetypes=[("Zip", "*.zip")])
        if not path:
            exit()
        zf = zipfile.ZipFile(path)
        names = sorted(n for n in zf.namelist() if n.lower().endswith(('.jpg', '.png', '.jpeg')))
        self.imgs = [Image.open(zf.open(n)) for n in names]
        self.show()
        # 读进度
        progress = path + ".progress"
        if os.path.exists(progress):
            self.index = int(open(progress).read())
            self.show()
        # 缩略图对象救生筏
        self.thumb_tkimgs = [ImageTk.PhotoImage(self.make_thumb(im))
                             for im in self.imgs]
        for idx in range(len(self.thumb_tkimgs)):
            self.lb.insert(tk.END, f"页 {idx + 1}")
        self.lb.selection_set(0)

    # def show(self):
    #     w, h = self.root.winfo_width(), self.root.winfo_height()
    #     img = self.imgs[self.index]
    #     img = img.resize((w, h), Image.LANCZOS)
    #     self.tkimg = ImageTk.PhotoImage(img)
    #     self.label.config(image=self.tkimg)
    #     self.root.title(f"{self.index+1}/{len(self.imgs)}")

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

        # 同步高亮缩略图
        self.lb.selection_clear(0, tk.END)
        self.lb.selection_set(self.index)
        self.lb.see(self.index)

    def flip(self, d):
        self.index = max(0, min(len(self.imgs)-1, self.index + d))
        self.show()

    def on_close(self):
        progress = filedialog.askopenfilename() + ".progress"
        open(progress, "w").write(str(self.index))
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

        # 左侧缩略图
        thumb_frame = tk.Frame(self.paned, width=150)
        self.paned.add(thumb_frame)
        self.lb = tk.Listbox(thumb_frame, selectmode='single', exportselection=0)
        self.lb.pack(side='left', fill='y', expand=True)
        scroll = tk.Scrollbar(thumb_frame, orient='vertical', command=self.lb.yview)
        scroll.pack(side='right', fill='y')
        self.lb.config(yscrollcommand=scroll.set)
        self.lb.bind('<<ListboxSelect>>', self.on_thumb_select)

        # 右侧阅读区
        right_frame = tk.Frame(self.paned)
        self.paned.add(right_frame)
        self.label = tk.Label(right_frame, bg='black')
        self.label.pack(fill='both', expand=True)

        # 键盘/滚轮
        self.root.bind("<Left>", lambda e: self.flip(-1))
        self.root.bind("<Right>", lambda e: self.flip(1))
        self.root.bind("<MouseWheel>", self.on_mouse_wheel)


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("800x600")
    ComicReader(root)
    root.mainloop()