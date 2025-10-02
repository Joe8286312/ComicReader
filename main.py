import os, zipfile, tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

class ComicReader:
    def __init__(self, root):
        self.root = root
        self.root.title("ComicReader-MVP")
        self.index = 0
        self.imgs = []
        self.label = tk.Label(root)
        self.label.pack(fill="both", expand=True)
        self.load_zip()
        self.root.bind("<Left>", lambda e: self.flip(-1))
        self.root.bind("<Right>", lambda e: self.flip(1))
        self.root.bind("<MouseWheel>", self.on_mouse_wheel) # 鼠标滚轮翻页
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # === 强制抢夺焦点 + 提到最前，避免首次启动键盘失灵 ===
        self.root.focus_set()  # 基础焦点
        self.root.focus_force()  # 强制抢焦点
        self.root.lift()  # 提到最前
        self.root.attributes('-topmost', True)  # 临时置顶
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

    # def show(self):
    #     w, h = self.root.winfo_width(), self.root.winfo_height()
    #     img = self.imgs[self.index]
    #     img = img.resize((w, h), Image.LANCZOS)
    #     self.tkimg = ImageTk.PhotoImage(img)
    #     self.label.config(image=self.tkimg)
    #     self.root.title(f"{self.index+1}/{len(self.imgs)}")

    # 窗口逻辑修改
    def show(self):
        if not self.imgs:
            return
        src = self.imgs[self.index]
        w0, h0 = src.size  # 原始宽高
        scr_w = self.root.winfo_width()
        scr_h = self.root.winfo_height()

        # 计算放大系数：让整张图完整落在窗口内，不裁剪、不拉伸
        scale = min(scr_w / w0, scr_h / h0, 1.0)  # 1.0 防止放大超过原图
        new_w, new_h = int(w0 * scale), int(h0 * scale)

        # Lanczos 高质量缩放
        dst = src.resize((new_w, new_h), Image.LANCZOS)
        self.tkimg = ImageTk.PhotoImage(dst)

        # 标签居中显示（黑边自动出现）
        self.label.config(image=self.tkimg, bg='black')  # bg 可改任意色
        self.root.title(f"{self.index + 1}/{len(self.imgs)}  {w0}x{h0}")

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

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("800x600")
    ComicReader(root)
    root.mainloop()