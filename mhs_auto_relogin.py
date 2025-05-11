import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import json
import os
import psutil
import pyautogui
import pygetwindow as gw
import pydirectinput
import time
import ctypes

# 全局變量
GAME_WINDOW_TITLE = "墨香 Online-16年在地經營 官方正版授權"
GAME_PROCESS_NAME = "MHClient-Connect.exe"
is_relogining = False
is_running = False

# 事件配置 (繁體中文顯示)
LOGIN_CONFIG = {
    "斷線確認": {"interval": 30, "max_wait": 60, "coords": [976, 602]},
    "選擇伺服器": {"interval": 15, "max_wait": 30, "coords": [954, 422]},
    "登入按鈕": {"interval": 10, "max_wait": 20, "coords": [953, 689]},
    "網路失敗確認": {"interval": 10, "max_wait": 20, "coords": [973, 602]},
    "二次密碼(第一位)": {"interval": 1, "max_wait": 5, "coords": [944, 537]},
    "二次密碼(第二位)": {"interval": 1, "max_wait": 5, "coords": [944, 537]},
    "二次密碼(第三位)": {"interval": 1, "max_wait": 5, "coords": [944, 537]},
    "二次密碼(第四位)": {"interval": 1, "max_wait": 5, "coords": [944, 537]},
    "二次密碼確認按鈕": {"interval": 5, "max_wait": 10, "coords": [951, 571]},
    "選擇角色": {"interval": 5, "max_wait": 10, "coords": [1809, 219]},
    "進入遊戲按鈕": {"interval": 5, "max_wait": 10, "coords": [1815, 378]},
    "選擇分流": {"interval": 5, "max_wait": 10, "coords": [944, 420]},
    "分流確認按鈕": {"interval": 5, "max_wait": 10, "coords": [954, 695]}
}

TELEPORT_CONFIG = {
    "teleport_key": "不使用奇門遁甲捲",
    "events": {
        "點擊移動場所分頁": {"interval": 5, "max_wait": 10, "coords": [855, 659]},
        "點擊可移動場所名稱": {"interval": 5, "max_wait": 10, "coords": [940, 581]},
        "點擊移動按鈕": {"interval": 5, "max_wait": 10, "coords": [952, 706]}
    }
}

TRAINING_CONFIG = {
    "events": {
        "點擊地面": {"interval": 5, "max_wait": 10, "coords": [313, 454]},
        "點擊狩獵圖標": {"interval": 5, "max_wait": 10, "coords": [1392, 1061]},
        "開始狩獵": {"interval": 5, "max_wait": 10, "coords": [732, 760]}
    }
}

class EventFrame(ttk.Frame):
    """事件配置框架"""
    def __init__(self, parent, name, description):
        super().__init__(parent)
        
        # 事件名稱和說明
        self.name = name
        ttk.Label(self, text=f"{name}:").pack(side=tk.LEFT, padx=2)
        ttk.Label(self, text=description, foreground="gray").pack(side=tk.LEFT, padx=2)
        
        # 座標顯示
        self.coords_var = tk.StringVar(value="X: 0, Y: 0")
        ttk.Label(self, textvariable=self.coords_var).pack(side=tk.LEFT, padx=2)
        
        # 記錄座標按鈕
        self.record_btn = ttk.Button(
            self,
            text="記錄座標",
            command=lambda n=name: self.master.master.master.master.start_recording(n)
        )
        self.record_btn.pack(side=tk.RIGHT, padx=2)
    
    def update_coords(self, x, y):
        """更新座標顯示"""
        self.coords_var.set(f"X: {x}, Y: {y}")

class MHSAutoReloginApp:
    def __init__(self, root):
        self.root = root
        self.root.title("墨香Online自動重連工具 v1.0")
        self.root.geometry("1200x800")
        
        # 運行狀態
        self.is_running = False
        self.relogin_thread = None
        self.recording_coords = False
        self.record_target = None
        
        # 事件框架字典
        self.event_frames = {}
        
        # 配置文件路徑
        self.config_file = "mhs_config.json"
        
        # 創建主要面板
        main_panel, left_panel, right_panel = self.create_main_panels()
        
        # 創建日誌區域
        self.create_log_area(right_panel)
        
        # 初始化配置
        self.config = self.load_config()
        
        # 創建主要元件
        self.create_widgets(left_panel)
        
        # 窗口關閉事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        global app
        app = self
    
    def load_config(self):
        default_config = {
            "game_window_title": GAME_WINDOW_TITLE,
            "game_process_name": GAME_PROCESS_NAME,
            "os_type": "Windows",
            "game_env": "聊天優先",
            "teleport_key": TELEPORT_CONFIG["teleport_key"],
            "login_config": LOGIN_CONFIG,
            "teleport_config": TELEPORT_CONFIG["events"],
            "training_config": TRAINING_CONFIG["events"]
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                    for event_name in LOGIN_CONFIG:
                        if event_name not in loaded_config["login_config"]:
                            loaded_config["login_config"][event_name] = LOGIN_CONFIG[event_name]
                    for event_name in TELEPORT_CONFIG["events"]:
                        if event_name not in loaded_config["teleport_config"]:
                            loaded_config["teleport_config"][event_name] = TELEPORT_CONFIG["events"][event_name]
                    for event_name in TRAINING_CONFIG["events"]:
                        if event_name not in loaded_config["training_config"]:
                            loaded_config["training_config"][event_name] = TRAINING_CONFIG["events"][event_name]
                    return loaded_config
            except:
                return default_config
        return default_config
    
    def save_config(self):
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
        self.log("所有配置已保存")
    
    def create_main_panels(self):
        """創建主要面板"""
        # 創建主要分割面板
        main_panel = ttk.Frame(self.root)
        main_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 創建容器來管理百分比
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)  # 設置根窗口行權重
        
        main_panel.grid_columnconfigure(0, weight=75)  # 左側面板寬度 75%
        main_panel.grid_columnconfigure(1, weight=25)  # 右側面板寬度 25%
        main_panel.grid_rowconfigure(0, weight=1)  # 設置面板行權重使其填滿高度
        
        # 左側面板 - 設定區域 (75%)
        left_panel = ttk.Frame(main_panel)
        left_panel.grid(row=0, column=0, sticky='nsew')
        
        # 右側面板 - 日誌區域 (25%)
        right_panel = ttk.Frame(main_panel)
        right_panel.grid(row=0, column=1, sticky='nsew')
        
        return main_panel, left_panel, right_panel

    def create_top_buttons(self, parent):
        """創建頂部按鈕欄"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.start_btn = ttk.Button(button_frame, text="啟動自動重連", command=self.toggle_auto_relogin)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="保存配置", command=self.save_config).pack(side=tk.LEFT, padx=5)
    
    def create_game_info_frame(self, parent):
        """創建遊戲資訊框架"""
        info_frame = ttk.LabelFrame(parent, text="遊戲資訊", padding=10)
        info_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(info_frame, text="遊戲窗口標題:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(info_frame, text=GAME_WINDOW_TITLE).grid(row=0, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(info_frame, text="遊戲進程名稱:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(info_frame, text=GAME_PROCESS_NAME).grid(row=1, column=1, sticky=tk.W, pady=2)
    
    def create_system_settings_frame(self, parent):
        """創建系統設定框架"""
        system_frame = ttk.LabelFrame(parent, text="系統設定", padding=10)
        system_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(system_frame, text="作業系統:").grid(row=0, column=0, sticky=tk.W, pady=2)
        os_combobox = ttk.Combobox(system_frame, values=["Windows"], state="readonly")
        os_combobox.grid(row=0, column=1, sticky=tk.W, pady=2)
        os_combobox.set("Windows")
    
    def create_scrollable_frame(self, parent):
        """創建可滾動的框架"""
        # 創建容器
        container = ttk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True)

        # 創建 Canvas 和 Scrollbar
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        # 設置滾動區域
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # 創建畫布視窗
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 使用pack布局
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        return scrollable_frame
    
    def create_login_frame(self, parent):
        """創建重新登入配置框架"""
        frame = ttk.LabelFrame(parent, text="重新登入配置", padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        return frame
    
    def create_teleport_frame(self, parent):
        """創建奇門遁甲捲配置框架"""
        teleport_frame = ttk.LabelFrame(parent, text="奇門遁甲捲配置", padding=10)
        teleport_frame.pack(fill=tk.X, pady=5)
        
        # 創建快捷鍵設定框架
        self.create_teleport_key_frame(teleport_frame)
        
        # 創建事件配置
        for event_name, description in [
            ("點擊移動場所分頁", "點擊移動場所分頁的座標"),
            ("點擊可移動場所名稱", "點擊可移動場所名稱的座標"),
            ("點擊移動按鈕", "點擊移動按鈕的座標")
        ]:
            frame = EventFrame(teleport_frame, event_name, description)
            frame.pack(fill=tk.X, pady=2)
            
            # 初始化為禁用狀態
            frame.record_btn.config(state="disabled")
            
            # 儲存事件框架
            self.event_frames[event_name] = frame
    
    def create_game_env_frame(self, parent):
        """創建遊戲環境設定框架"""
        env_frame = ttk.Frame(parent)
        env_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(env_frame, text="遊戲環境:").pack(side=tk.LEFT, padx=2)
        self.env_combobox = ttk.Combobox(env_frame, values=["聊天優先"], state="disabled", width=15)
        self.env_combobox.pack(side=tk.LEFT, padx=2)
        self.env_combobox.set("聊天優先")
        
        disabled_option = ttk.Label(env_frame, text="快捷鍵優先 (未啟用)", foreground="gray")
        disabled_option.pack(side=tk.LEFT, padx=10)
    
    def create_teleport_key_frame(self, parent):
        """創建奇門遁甲捲快捷鍵設定框架"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(frame, text="快捷鍵:").pack(side=tk.LEFT, padx=2)
        self.teleport_combobox = ttk.Combobox(frame, values=["不使用奇門遁甲捲"] + [f"F{i}" for i in range(1, 11)], state="readonly", width=15)
        self.teleport_combobox.pack(side=tk.LEFT, padx=2)
        self.teleport_combobox.set("不使用奇門遁甲捲")
        
        # 綁定更新事件
        self.teleport_combobox.bind("<<ComboboxSelected>>", self.update_teleport_key)
        
        # 初始化狀態
        self.update_teleport_key()
    
    def create_training_frame(self, parent):
        """創建自動狩獵配置框架"""
        frame = ttk.LabelFrame(parent, text="自動狩獵配置", padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        return frame
    
    def create_widgets(self, left_panel):
        """創建所有元件"""
        # 頂部按鈕欄
        self.create_top_buttons(left_panel)
        
        # 遊戲資訊框架
        self.create_game_info_frame(left_panel)
        
        # 系統設定框架
        self.create_system_settings_frame(left_panel)
        
        # 事件配置框架
        scrollable_frame = self.create_scrollable_frame(left_panel)
        
        # 創建各種配置框架
        login_frame = self.create_login_frame(scrollable_frame)
        teleport_frame = self.create_teleport_frame(scrollable_frame)
        training_frame = self.create_training_frame(scrollable_frame)
        
        # 創建事件配置項目
        self.event_frames = {}
        for i, (event_name, event_data) in enumerate(self.config["login_config"].items()):
            frame = ttk.Frame(login_frame)
            frame.pack(fill=tk.X, pady=2)
            
            # 事件名稱
            ttk.Label(frame, text=event_name, width=25).pack(side=tk.LEFT, padx=2)
            
            # 檢查間隔
            ttk.Label(frame, text="檢查間隔:").pack(side=tk.LEFT)
            frame.interval_spin = ttk.Spinbox(frame, from_=1, to=300, width=5)
            frame.interval_spin.pack(side=tk.LEFT, padx=2)
            frame.interval_spin.set(event_data["interval"])
            
            # 最大等待
            ttk.Label(frame, text="最大等待:").pack(side=tk.LEFT)
            frame.max_wait_spin = ttk.Spinbox(frame, from_=1, to=120, width=5)
            frame.max_wait_spin.pack(side=tk.LEFT, padx=2)
            frame.max_wait_spin.set(event_data["max_wait"])
            
            # 座標記錄按鈕
            frame.record_btn = ttk.Button(frame, text="記錄座標", 
                                        command=lambda e=event_name: self.start_recording(e))
            frame.record_btn.pack(side=tk.LEFT, padx=5)
            
            # 座標顯示
            frame.coord_label = ttk.Label(frame, text=f"({event_data['coords'][0]}, {event_data['coords'][1]})")
            frame.coord_label.pack(side=tk.LEFT)
            
            self.event_frames[event_name] = frame
        
        # 創建自動狩獵配置
        for i, (event_name, event_data) in enumerate(self.config["training_config"].items()):
            frame = ttk.Frame(training_frame)
            frame.pack(fill=tk.X, pady=2)
            
            # 事件名稱
            ttk.Label(frame, text=event_name, width=25).pack(side=tk.LEFT, padx=2)
            
            # 檢查間隔
            ttk.Label(frame, text="檢查間隔:").pack(side=tk.LEFT)
            frame.interval_spin = ttk.Spinbox(frame, from_=1, to=300, width=5)
            frame.interval_spin.pack(side=tk.LEFT, padx=2)
            frame.interval_spin.set(event_data["interval"])
            
            # 最大等待
            ttk.Label(frame, text="最大等待:").pack(side=tk.LEFT)
            frame.max_wait_spin = ttk.Spinbox(frame, from_=1, to=120, width=5)
            frame.max_wait_spin.pack(side=tk.LEFT, padx=2)
            frame.max_wait_spin.set(event_data["max_wait"])
            
            # 座標記錄按鈕
            frame.record_btn = ttk.Button(frame, text="記錄座標", 
                                        command=lambda e=event_name: self.start_recording(e))
            frame.record_btn.pack(side=tk.LEFT, padx=5)
            
            # 座標顯示
            frame.coord_label = ttk.Label(frame, text=f"({event_data['coords'][0]}, {event_data['coords'][1]})")
            frame.coord_label.pack(side=tk.LEFT)
            
            self.event_frames[event_name] = frame
        
        # 狀態欄
        self.status_var = tk.StringVar()
        self.status_var.set("狀態: 就緒")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, padx=10, pady=5)
    
    def create_log_area(self, parent):
        """創建日誌區域"""
        # 創建日誌框架
        log_frame = ttk.LabelFrame(parent, text="運行日誌")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 創建可滾動的文字區域
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, width=40, height=30)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 移除滾動條的外框
        self.log_text.configure(bd=0, highlightthickness=0)
    
    def start_recording(self, event_name):
        """開始記錄座標"""
        if self.recording_coords:
            messagebox.showwarning("警告", "正在記錄其他座標，請稍後再試")
            return
            
        self.record_target = event_name
        self.recording_coords = True
        self.status_var.set(f"狀態: 正在記錄 {event_name} 座標，請點擊目標位置...")
        
        # 禁用所有按鈕避免干擾
        for widget in [self.start_btn]:
            widget.config(state="disabled")
        
        for name, frame in self.event_frames.items():
            frame.record_btn.config(state="disabled")
        
        # 綁定滑鼠點擊和 Esc 鍵事件
        self.root.bind('<Button-1>', self.on_mouse_click)
        self.root.bind('<Escape>', self.cancel_recording)
        
        # 顯示取消提示
        self.status_var.set(f"狀態: 正在記錄 {event_name} 座標，請點擊目標位置... (按 Esc 取消)")
    
    def cancel_recording(self, event=None):
        """取消座標記錄"""
        if self.recording_coords:
            # 解除事件綁定
            self.root.unbind('<Button-1>')
            self.root.unbind('<Escape>')
            
            self.recording_coords = False
            self.record_target = None
            
            # 重新啟用按鈕
            for widget in [self.start_btn]:
                widget.config(state="normal")
            
            for name, frame in self.event_frames.items():
                frame.record_btn.config(state="normal")
            
            self.status_var.set("狀態: 已取消座標記錄")
            self.log("已取消座標記錄")
    
    def on_mouse_click(self, event):
        """當滑鼠點擊時記錄座標"""
        if self.recording_coords and self.record_target:
                # 解除滑鼠點擊和 Esc 鍵事件綁定
            self.root.unbind('<Button-1>')
            self.root.unbind('<Escape>')
            
            # 獲取點擊座標
            x, y = pyautogui.position()
            if self.record_target in self.config["login_config"]:
                self.config["login_config"][self.record_target]["coords"] = [x, y]
            elif self.record_target in self.config["teleport_config"]:
                self.config["teleport_config"][self.record_target]["coords"] = [x, y]
            elif self.record_target in self.config["training_config"]:
                self.config["training_config"][self.record_target]["coords"] = [x, y]
            
            # 更新GUI顯示
            if self.record_target in self.event_frames:
                frame = self.event_frames[self.record_target]
                frame.coord_label.config(text=f"({x}, {y})")
            
            self.save_config()
            self.status_var.set(f"狀態: 已記錄 {self.record_target} 座標 ({x}, {y})")
            self.log(f"已記錄 {self.record_target} 座標: ({x}, {y})")
            
            self.recording_coords = False
            self.record_target = None
            
            # 重新啟用按鈕
            for widget in [self.start_btn]:
                widget.config(state="normal")
            
            for name, frame in self.event_frames.items():
                frame.record_btn.config(state="normal")
    
    def toggle_auto_relogin(self):
        if self.is_running:
            self.stop_auto_relogin()
        else:
            self.start_auto_relogin()
    
    def start_auto_relogin(self):
        global GAME_WINDOW_TITLE, GAME_PROCESS_NAME, is_running
        GAME_WINDOW_TITLE = self.config["game_window_title"]
        GAME_PROCESS_NAME = self.config["game_process_name"]
        is_running = True
        
        self.is_running = True
        self.start_btn.config(text="停止自動重連")
        self.status_var.set("狀態: 自動重連運行中...")
        
        self.relogin_thread = threading.Thread(target=self.run_main_loop, daemon=True)
        self.relogin_thread.start()
        
        self.log("自動重連已啟動")
    
    def stop_auto_relogin(self):
        global is_running
        is_running = False
        self.is_running = False
        self.start_btn.config(text="啟動自動重連")
        self.status_var.set("狀態: 已停止")
        self.log("自動重連已停止")
    
    def run_main_loop(self):
        while self.is_running:
            if not is_relogining:
                if is_game_disconnected():
                    auto_relogin()
            time.sleep(1)  # 基礎檢查間隔
    
    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, log_message)
        self.log_text.config(state="disabled")
        self.log_text.see(tk.END)
    
    def on_closing(self):
        if self.is_running:
            if messagebox.askokcancel("退出", "自動重連正在運行，確定要退出嗎？"):
                self.stop_auto_relogin()
                self.root.destroy()
        else:
            self.root.destroy()
    
    def update_teleport_key(self, event=None):
        """更新快捷鍵設定"""
        key = self.teleport_combobox.get()
        self.config["teleport_key"] = key
        
        # 更新相關按鈕的狀態
        state = "disabled" if key == "不使用奇門遁甲捲" else "normal"
        
        # 更新事件框架的按鈕狀態
        teleport_events = [
            "點擊移動場所分頁",
            "點擊可移動場所名稱",
            "點擊移動按鈕"
        ]
        
        for event_name in teleport_events:
            if event_name in self.event_frames:
                self.event_frames[event_name].record_btn.config(state=state)
        self.save_config()

def click_game(x, y, clicks=1):
    debug_log(f"點擊位置: ({x}, {y})")
    try:
        for _ in range(clicks):
            pydirectinput.moveTo(x, y)
            pydirectinput.mouseDown()
            time.sleep(0.05)
            pydirectinput.mouseUp()
    except Exception as e:
        debug_log(f"點擊失敗: {e}")

def is_game_disconnected():
    try:
        for proc in psutil.process_iter(['pid', 'name']):           
            if proc.info['name'] == GAME_PROCESS_NAME:
                connections = proc.connections()
                debug_log('檢測遊戲是否正常運作...')
                if not connections:
                    debug_log("檢測到遊戲無網絡連接，可能已斷線！")
                    return True
        return False
    except Exception as e:
        debug_log(f"檢測網絡錯誤: {e}")
        return False

def restore_game_window():
    try:
        game_window = gw.getWindowsWithTitle(GAME_WINDOW_TITLE)[0]
        if game_window.isMinimized:
            debug_log('還原窗口')
            game_window.restore()
            time.sleep(1)
            debug_log('聚焦窗口')
        game_window.activate()
        return True
    except Exception as e:
        debug_log(f"恢復窗口失敗: {e}")
        return False

def is_network_ok():
    response = os.system("ping -n 2 8.8.8.8 > nul")
    return response == 0

def auto_relogin():
    global is_relogining
    is_relogining = True
    debug_log("開始自動重連...")
    
    try:
        if not restore_game_window():
            debug_log("無法恢復遊戲窗口")
            return
        
        events = app.config
        
        # 斷線確認
        debug_log('點擊斷線窗口的確認按鈕')
        time.sleep(events["login_config"]["斷線確認"]["max_wait"])
        click_game(*events["login_config"]["斷線確認"]["coords"])
        
        # 選擇伺服器
        time.sleep(events["login_config"]["選擇伺服器"]["max_wait"])
        debug_log('點擊青龍伺服器')
        click_game(*events["login_config"]["選擇伺服器"]["coords"])
        
        # 登入按鈕
        time.sleep(events["login_config"]["登入按鈕"]["max_wait"])
        debug_log('點擊登入按鈕')
        click_game(*events["login_config"]["登入按鈕"]["coords"])
        
        # 網路檢查
        if "網路失敗確認" in events["login_config"] and events["login_config"]["網路失敗確認"]["coords"][0] > 0:
            time.sleep(events["login_config"]["網路失敗確認"]["max_wait"])
            if not is_network_ok():
                debug_log('如果沒有網路，點擊"伺服器連線失敗"彈框的按鈕')
                click_game(*events["login_config"]["網路失敗確認"]["coords"])
                time.sleep(events["login_config"]["登入按鈕"]["max_wait"])
                debug_log('重新點擊登入按鈕')
                click_game(*events["login_config"]["登入按鈕"]["coords"])
                time.sleep(events["login_config"]["登入按鈕"]["max_wait"])
        
        # 記住登入
        debug_log("已經啟用記住帳號密碼功能，所以無需輸入，直接點擊登入按鈕")
        click_game(*events["login_config"]["記住登入"]["coords"])
        time.sleep(events["login_config"]["記住登入"]["max_wait"])
        
        # 二次密碼
        debug_log("輸入二次密碼start")
        click_game(*events["login_config"]["二次密碼(第一位)"]["coords"])
        time.sleep(0.5)
        click_game(*events["login_config"]["二次密碼(第二位)"]["coords"])
        time.sleep(0.5)
        click_game(*events["login_config"]["二次密碼(第三位)"]["coords"])
        time.sleep(0.5)
        click_game(*events["login_config"]["二次密碼(第四位)"]["coords"])
        debug_log("輸入二次密碼完成")
        
        # 二次確認
        click_game(*events["login_config"]["二次密碼確認按鈕"]["coords"])
        debug_log("確認完成")
        time.sleep(events["login_config"]["二次密碼確認按鈕"]["max_wait"])
        
        # 選擇角色
        debug_log("選擇角色")
        click_game(*events["login_config"]["選擇角色"]["coords"])
        time.sleep(events["login_config"]["選擇角色"]["max_wait"])
        
        # 進入遊戲
        click_game(*events["login_config"]["進入遊戲按鈕"]["coords"])
        debug_log("點擊進入遊戲按鈕")
        time.sleep(events["login_config"]["進入遊戲按鈕"]["max_wait"])
        
        # 選擇分流
        click_game(*events["login_config"]["選擇分流"]["coords"])
        debug_log("點擊1分流")
        time.sleep(events["login_config"]["選擇分流"]["max_wait"])
        
        # 分流確認
        debug_log("確定")
        click_game(*events["login_config"]["分流確認按鈕"]["coords"])
        time.sleep(events["login_config"]["分流確認按鈕"]["max_wait"])
        
        # 使用奇門遁甲卷
        if "點擊移動場所分頁" in events["teleport_config"] and events["teleport_config"]["點擊移動場所分頁"]["coords"][0] > 0:
            debug_log("使用奇門遁甲卷")
            click_game(*events["teleport_config"]["點擊移動場所分頁"]["coords"])
            time.sleep(events["teleport_config"]["點擊移動場所分頁"]["max_wait"])
            click_game(*events["teleport_config"]["點擊可移動場所名稱"]["coords"])
            time.sleep(events["teleport_config"]["點擊可移動場所名稱"]["max_wait"])
            click_game(*events["teleport_config"]["點擊移動按鈕"]["coords"])
            time.sleep(events["teleport_config"]["點擊移動按鈕"]["max_wait"])
        
        # 選擇分流2
        debug_log("點擊分流")
        click_game(*events["login_config"]["選擇分流"]["coords"])
        time.sleep(events["login_config"]["選擇分流"]["max_wait"])
        
        # 登入
        debug_log("點擊登入按鈕")
        click_game(*events["login_config"]["登入按鈕"]["coords"])
        time.sleep(events["login_config"]["登入按鈕"]["max_wait"])
        
        # 隨機點擊
        debug_log("隨意點一下地圖，讓角色走兩步路")
        click_game(*events["training_config"]["隨機點擊"]["coords"])
        time.sleep(events["training_config"]["隨機點擊"]["max_wait"])
        
        # 開始狩獵
        debug_log("點擊自動狩獵圖標")
        click_game(*events["training_config"]["狩獵圖標"]["coords"])
        time.sleep(events["training_config"]["狩獵圖標"]["max_wait"])
        
        debug_log("開始自動狩獵")
        click_game(*events["training_config"]["開始狩獵"]["coords"])
        debug_log("自動重連完成")
    except Exception as e:
        debug_log(f"自動重連失敗: {e}")
    finally:
        is_relogining = False

def debug_log(message):
    timestamp = time.strftime("%H:%M:%S")
    log_message = f"[{timestamp}] DEBUG: {message}"
    
    if 'app' in globals() and isinstance(app, MHSAutoReloginApp):
        app.log(log_message)
    else:
        print(log_message)

if __name__ == "__main__":
    root = tk.Tk()
    app = MHSAutoReloginApp(root)
    root.mainloop()