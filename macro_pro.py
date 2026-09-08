import time
import json
import threading
import queue
import math
import subprocess
import Quartz
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pynput import mouse, keyboard

def validate_events(data):
    if not isinstance(data, list) or not data:
        raise ValueError("文件必须包含非空的鼠标录制列表")
    result = []
    previous = 0
    for index, event in enumerate(data, 1):
        if not isinstance(event, dict):
            raise ValueError(f"第 {index} 条记录格式错误")
        values = {}
        for key in ("x", "y", "time"):
            value = event.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"第 {index} 条记录的 {key} 无效")
            values[key] = value
        if values["time"] < previous:
            raise ValueError(f"第 {index} 条记录的时间顺序错误")
        previous = values["time"]
        result.append(values)
    return result


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("宏工具独立版 1.1")
        self.root.geometry("720x550")

        self.recording = False
        self.playing = False
        self.events = []
        self.listener = None
        self.stop_event = threading.Event()
        self.record_start = None

        self.actions = queue.Queue()
        self.pressed_keys = set()

        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")

        ttk.Button(top, text="开始录制", command=self.start_record).grid(row=0, column=0, padx=5)
        ttk.Button(top, text="停止录制", command=self.stop_record).grid(row=0, column=1, padx=5)
        ttk.Button(top, text="开始播放", command=self.start_play).grid(row=0, column=2, padx=5)
        ttk.Button(top, text="停止播放", command=self.stop_play).grid(row=0, column=3, padx=5)
        ttk.Button(top, text="保存", command=self.save_file).grid(row=0, column=4, padx=5)
        ttk.Button(top, text="加载", command=self.load_file).grid(row=0, column=5, padx=5)

        opts = ttk.LabelFrame(root, text="播放设置", padding=10)
        opts.pack(fill="x", padx=10, pady=5)

        self.loop_forever = tk.BooleanVar(value=True)
        self.loop_count = tk.StringVar(value="10")

        ttk.Checkbutton(opts, text="无限循环", variable=self.loop_forever).grid(row=0, column=0)
        ttk.Label(opts, text="循环次数").grid(row=0, column=1)
        ttk.Entry(opts, textvariable=self.loop_count, width=8).grid(row=0, column=2)

        ttk.Label(root, text="全局快捷键：F6 开始播放 · F7 停止播放 · F8 开始录制 · F9 停止录制").pack()
        self.text = tk.Text(root)
        self.text.pack(fill="both", expand=True, padx=10, pady=10)

        permissions = ttk.Frame(root)
        permissions.pack(fill="x", padx=10, before=self.text)
        ttk.Button(permissions, text="检查权限", command=self.check_permissions).pack(side="left")
        ttk.Button(permissions, text="打开辅助功能设置", command=lambda: self.open_settings("Privacy_Accessibility")).pack(side="left", padx=5)
        ttk.Button(permissions, text="打开输入监控设置", command=lambda: self.open_settings("Privacy_ListenEvent")).pack(side="left")
        self.hotkeys = None
        self.check_permissions()
        if Quartz.CGPreflightListenEventAccess():
            self.hotkeys = keyboard.Listener(on_press=self.key_down, on_release=self.key_up)
            self.hotkeys.start()
        self.root.after(20, self.drain_actions)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def open_settings(self, pane):
        subprocess.Popen(["/usr/bin/open", "x-apple.systempreferences:com.apple.preference.security?" + pane])

    def check_permissions(self):
        post = bool(Quartz.CGPreflightPostEventAccess())
        listen = bool(Quartz.CGPreflightListenEventAccess())
        self.log("鼠标操作权限：" + ("已允许" if post else "未允许，请在辅助功能中添加并开启本 App"))
        self.log("录制及全局快捷键权限：" + ("已允许" if listen else "未允许，请在输入监控中添加并开启本 App"))
        if not post or not listen:
            self.log("更改权限后，请完全退出并重新打开本 App。给终端或 Python 的权限不能代替本 App 的权限。")
        return post, listen

    def key_down(self, key):
        if key in self.pressed_keys:
            return
        self.pressed_keys.add(key)
        actions = {keyboard.Key.f6: self.start_play, keyboard.Key.f7: self.stop_play,
                   keyboard.Key.f8: self.start_record, keyboard.Key.f9: self.stop_record}
        if key == keyboard.Key.f7:
            self.stop_event.set()
        if key in actions:
            self.actions.put(actions[key])

    def key_up(self, key):
        self.pressed_keys.discard(key)

    def drain_actions(self):
        try:
            while True:
                self.actions.get_nowait()()
        except queue.Empty:
            pass
        self.root.after(20, self.drain_actions)

    def close(self):
        self.stop_event.set()
        self.recording = False
        if self.listener:
            self.listener.stop()
        if self.hotkeys:
            self.hotkeys.stop()
        self.root.destroy()

    def log(self, msg):
        self.text.insert("end", msg + "\n")
        self.text.see("end")

    def on_click(self, x, y, button, pressed):
        if self.recording and pressed:
            t = time.time() - self.record_start
            event = {"x": x, "y": y, "time": t}
            self.events.append(event)
            self.actions.put(lambda: self.log(f"记录: {x},{y}"))

    def start_record(self):
        if self.recording or self.playing:
            return
        if not Quartz.CGPreflightListenEventAccess():
            self.check_permissions()
            return
        self.events = []
        self.recording = True
        self.record_start = time.time()
        self.listener = mouse.Listener(on_click=self.on_click)
        self.listener.start()
        self.log("开始录制")

    def stop_record(self):
        self.recording = False
        if self.listener:
            self.listener.stop()
        self.log(f"录制完成，共 {len(self.events)} 条")

    def start_play(self):
        if self.playing or self.recording:
            return
        if not self.events:
            self.log("没有数据，请先录制或加载文件")
            return
        try:
            loops = None if self.loop_forever.get() else int(self.loop_count.get())
            if loops is not None and loops < 1:
                raise ValueError()
        except ValueError:
            self.log("循环次数请输入大于零的整数")
            return
        if not Quartz.CGPreflightPostEventAccess():
            self.check_permissions()
            messagebox.showwarning("需要辅助功能权限", "尚未获得鼠标操作权限。请在系统设置的辅助功能列表中添加并开启宏工具独立版，然后退出并重新打开 App。")
            return
        self.stop_event.clear()
        self.playing = True
        events = [dict(e) for e in self.events]
        threading.Thread(target=self.play_worker, args=(events, loops), daemon=True).start()
        self.log(f"开始播放：{len(events)} 条记录，首次点击等待 {events[0]['time']:.1f} 秒；F7 或停止播放按钮可中止")

    def stop_play(self):
        self.stop_event.set()
        self.log("停止播放")

    def finish_play(self):
        self.playing = False

    def play_worker(self, events, loops):
        try:
            m = mouse.Controller()
            count = 0
            while not self.stop_event.is_set():
                if loops is not None and count >= loops:
                    break
                prev = 0
                for index, e in enumerate(events, 1):
                    if not Quartz.CGPreflightPostEventAccess():
                        raise RuntimeError("鼠标操作权限已失效，请检查辅助功能设置并重启 App")
                    if self.stop_event.wait(max(e["time"] - prev, 0)):
                        break
                    m.position = (e["x"], e["y"])
                    if self.stop_event.is_set():
                        break
                    m.click(mouse.Button.left)
                    self.actions.put(lambda i=index, x=e["x"], y=e["y"]: self.log(f"已发送第 {i} 次点击：({x:.0f}, {y:.0f})"))
                    prev = e["time"]
                if self.stop_event.is_set():
                    break
                count += 1
                self.actions.put(lambda n=count: self.log(f"完成第 {n} 次"))
                if self.stop_event.wait(0.01):
                    break
        except Exception as exc:
            self.actions.put(lambda msg=str(exc): self.log(f"播放失败: {msg}"))
        finally:
            self.actions.put(self.finish_play)

    def save_file(self):
        path = filedialog.asksaveasfilename(defaultextension=".json")
        if not path:
            return
        with open(path, "w") as f:
            json.dump(self.events, f)
        self.log(f"已保存: {path}")

    def load_file(self):
        if self.playing or self.recording:
            self.log("请先停止播放或录制，再加载文件")
            return
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                events = validate_events(json.load(f))
        except (OSError, ValueError) as exc:
            messagebox.showerror("加载失败", str(exc))
            self.log(f"加载失败：{exc}")
            return
        self.events = events
        self.log(f"已加载: {len(self.events)} 条记录，单轮约 {events[-1]['time']:.1f} 秒。点击开始播放或按 F6 执行。")

if __name__ == "__main__":
    import sys
    root = tk.Tk()
    if "--self-test" in sys.argv:
        root.withdraw()
        root.update()
        assert getattr(sys, "frozen", False), "必须在独立程序中检查"
        print("SELF_TEST_OK: bundled Python, Tk, mouse and keyboard loaded", flush=True)
        root.destroy()
    else:
        App(root)
        root.mainloop()
