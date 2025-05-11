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
    "點擊斷線彈出框的確定按鈕": {"interval": 30, "max_wait": 60, "coords": [976, 602]},
    "點擊伺服器": {"interval": 15, "max_wait": 30, "coords": [954, 422]},
    "點擊登入按鈕": {"interval": 10, "max_wait": 20, "coords": [953, 689]},
    "若登入失敗的確認按鈕(非必填)": {"interval": 10, "max_wait": 20, "coords": [973, 602]},
    "點擊二次密碼(第一位)": {"interval": 1, "max_wait": 5, "coords": [944, 537]},
    "點擊二次密碼(第二位)": {"interval": 1, "max_wait": 5, "coords": [944, 537]},
    "點擊二次密碼(第三位)": {"interval": 1, "max_wait": 5, "coords": [944, 537]},
    "點擊二次密碼(第四位)": {"interval": 1, "max_wait": 5, "coords": [944, 537]},
    "點擊二次密碼確認按鈕": {"interval": 5, "max_wait": 10, "coords": [951, 571]},
    "點擊角色暱稱": {"interval": 5, "max_wait": 10, "coords": [1809, 219]},
    "點擊進入遊戲按鈕": {"interval": 5, "max_wait": 10, "coords": [1815, 378]},
    "點擊分流": {"interval": 5, "max_wait": 10, "coords": [944, 420]},
    "點擊登入按鈕": {"interval": 5, "max_wait": 10, "coords": [954, 695]}
}

TELEPORT_CONFIG = {
    "teleport_key": "不使用奇門遁甲卷",
    "events": {
        "點擊奇門遁甲卷的分頁(若想移動場所在第二頁，就需要點擊II)": {"interval": 5, "max_wait": 10, "coords": [855, 659]},
        "點擊移動場所名稱": {"interval": 5, "max_wait": 10, "coords": [940, 581]},
        "點擊移動按鈕": {"interval": 5, "max_wait": 10, "coords": [952, 706]}
    }
}

TRAINING_CONFIG = {
    "events": {
        "開始狩獵": {"interval": 5, "max_wait": 10, "coords": [732, 760]},
        "結束狩獵": {"interval": 5, "max_wait": 10, "coords": [732, 760]}
    }
}

# 不再需要EventFrame類，已改為直接在函數中創建UI元件

class MHSAutoReloginApp:
    def __init__(self, root):
        self.root = root
        self.root.title("墨香Online自動重連工具 v1.0")
        self.root.geometry("1200x800")
        
        # 運行狀態
        self.is_running = False
        self.relogin_thread = None
        self.recording_event = None
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
    
    def load_default_config(self):
        return {
            "game_window_title": GAME_WINDOW_TITLE,
            "game_process_name": GAME_PROCESS_NAME,
            "os_type": "Windows",
            "game_env": "聊天優先",
            "teleport_key": TELEPORT_CONFIG["teleport_key"],
            "login_config": {"events": LOGIN_CONFIG},
            "teleport_config": {"events": TELEPORT_CONFIG["events"]},
            "training_config": {"events": TRAINING_CONFIG["events"]}
        }
        
    def merge_config(self, default, loaded):
        """合併預設配置與載入的配置"""
        # 確保所有配置結構完整
        loaded.setdefault("login_config", {})
        loaded.setdefault("teleport_config", {"events": {}})
        loaded.setdefault("training_config", {"events": {}})
        
        self.merge_login_config(loaded)
        self.merge_teleport_config(loaded)
        self.merge_training_config(loaded)
        
        # 確保teleport_key存在
        loaded.setdefault("teleport_key", TELEPORT_CONFIG["teleport_key"])
        loaded["teleport_config"].setdefault("teleport_key", TELEPORT_CONFIG["teleport_key"])
        
        return loaded
        
    def merge_login_config(self, loaded):
        for event_name, event_data in LOGIN_CONFIG.items():
            if event_name not in loaded["login_config"]["events"]:
                loaded["login_config"]["events"][event_name] = event_data
            else:
                self.ensure_event_defaults(loaded["login_config"]["events"][event_name], event_data)
    
    def merge_teleport_config(self, loaded):
        for event_name, event_data in TELEPORT_CONFIG["events"].items():
            if event_name not in loaded["teleport_config"]["events"]:
                loaded["teleport_config"]["events"][event_name] = event_data
            else:
                self.ensure_event_defaults(loaded["teleport_config"]["events"][event_name], event_data)
    
    def merge_training_config(self, loaded):
        for event_name, event_data in TRAINING_CONFIG["events"].items():
            if event_name not in loaded["training_config"]["events"]:
                loaded["training_config"]["events"][event_name] = event_data
            else:
                self.ensure_event_defaults(loaded["training_config"]["events"][event_name], event_data)
    
    def ensure_event_defaults(self, target, source):
        """確保事件配置有預設值"""
        target.setdefault("interval", source["interval"])
        target.setdefault("max_wait", source["max_wait"])
        target.setdefault("coords", source["coords"])
    
    def load_config(self):
        """載入配置文件"""
        if not os.path.exists(self.config_file):
            return self.load_default_config()
            
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return self.merge_config(self.load_default_config(), json.load(f))
        except:
            return self.load_default_config()
    
    def save_config(self):
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
        self.log("所有配置已保存")
    
    def create_main_panels(self):
        """創建主要面板"""
        main_panel = self.create_main_frame()
        self.setup_panel_grid(main_panel)
        
        left_panel = self.create_left_panel(main_panel)
        right_panel = self.create_right_panel(main_panel)
        
        return main_panel, left_panel, right_panel
    
    def create_main_frame(self):
        """創建主框架"""
        main_panel = ttk.Frame(self.root)
        main_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        return main_panel
    
    def setup_panel_grid(self, main_panel):
        """設置面板網格布局"""
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        main_panel.grid_columnconfigure(0, weight=75)
        main_panel.grid_columnconfigure(1, weight=25)
        main_panel.grid_rowconfigure(0, weight=1)
    
    def create_left_panel(self, main_panel):
        """創建左側面板"""
        left_panel = ttk.Frame(main_panel)
        left_panel.grid(row=0, column=0, sticky='nsew')
        return left_panel
    
    def create_right_panel(self, main_panel):
        """創建右側面板"""
        right_panel = ttk.Frame(main_panel)
        right_panel.grid(row=0, column=1, sticky='nsew')
        return right_panel
    
    def create_widgets(self, parent):
        """創建所有UI元件"""
        self.create_top_buttons(parent)
        self.create_game_info_frame(parent)
        self.create_event_frames(parent)
    
    def create_top_buttons(self, parent):
        """創建頂部按鈕欄"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.start_btn = ttk.Button(button_frame, 
                                  text="啟動自動重連", 
                                  command=self.toggle_auto_relogin)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        # 狀態顯示
        self.status_var = tk.StringVar()
        self.status_var.set("狀態: 就緒")
        ttk.Label(button_frame, textvariable=self.status_var).pack(side=tk.RIGHT, padx=5)
    
    def create_event_frames(self, parent):
        """創建事件配置框架"""
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.create_login_frame(notebook)
        self.create_teleport_frame(notebook)
        self.create_training_frame(notebook)
    
    def create_login_frame(self, notebook):
        """創建登入事件框架"""
        frame = ttk.Frame(notebook)
        self.create_event_controls(frame, "login_config")
        notebook.add(frame, text="重新登入流程")
    
    def create_teleport_frame(self, notebook):
        """創建傳送事件框架"""
        frame = ttk.Frame(notebook)
        
        # 添加注意事項
        warning_label = ttk.Label(
            frame, 
            text="若要使用此功能，請在遊戲內設置選項中，環境分區設為聊天優先，而不是快捷鍵優先",
            foreground="red"
        )
        warning_label.pack(fill=tk.X, pady=5)
        
        # 創建快捷鍵選擇區域
        shortcut_frame = ttk.LabelFrame(frame, text="遁甲卷道具快捷鍵")
        shortcut_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 創建Radio按鈕
        self.teleport_var = tk.StringVar(value=self.config["teleport_key"])
        
        # 不使用選項
        ttk.Radiobutton(
            shortcut_frame, 
            text="不使用", 
            variable=self.teleport_var, 
            value="不使用奇門遁甲卷"
        ).pack(side=tk.LEFT, padx=5)
        
        # F1-F10按鍵選項
        for i in range(1, 11):
            ttk.Radiobutton(
                shortcut_frame, 
                text=f"F{i}", 
                variable=self.teleport_var, 
                value=f"F{i}"
            ).pack(side=tk.LEFT)
        
        # 綁定更新事件
        self.teleport_var.trace_add("write", self.update_teleport_key)
        
        # 創建事件控制項
        self.create_event_controls(frame, "teleport_config")
        notebook.add(frame, text="遁甲卷使用流程")
    
    def create_training_frame(self, notebook):
        """創建練功事件框架"""
        frame = ttk.Frame(notebook)
        self.create_event_controls(frame, "training_config")
        notebook.add(frame, text="自動狩獵流程")
    
    def create_event_controls(self, parent, config_name):
        """創建事件配置控件"""
        config = self.config[config_name]
        
        # 確保配置有events鍵
        if "events" not in config:
            config["events"] = {}
            
        for event_name, event_data in config["events"].items():
            # 確保event_data是字典
            if not isinstance(event_data, dict):
                event_data = {}
                config["events"][event_name] = event_data
                
            # 確保事件配置有預設值
            event_data.setdefault("interval", 5)
            event_data.setdefault("max_wait", 10)
            event_data.setdefault("coords", [0, 0])
            
            frame = ttk.Frame(parent)
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
    
    def create_game_info_frame(self, parent):
        """創建遊戲資訊框架"""
        info_frame = ttk.LabelFrame(parent, text="遊戲資訊", padding=10)
        info_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(info_frame, text="遊戲窗口標題:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(info_frame, text=GAME_WINDOW_TITLE).grid(row=0, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(info_frame, text="遊戲進程名稱:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(info_frame, text=GAME_PROCESS_NAME).grid(row=1, column=1, sticky=tk.W, pady=2)
        
        return info_frame
    
    def create_log_area(self, parent):
        """創建日誌區域"""
        log_frame = ttk.LabelFrame(parent, text="日誌", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # 創建日誌文本框
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            width=40,
            height=10,
            font=('Consolas', 10)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # 日誌級別選擇
        log_level_frame = ttk.Frame(log_frame)
        log_level_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(log_level_frame, text="日誌級別:").pack(side=tk.LEFT)
        self.log_level = tk.StringVar(value="INFO")
        ttk.Combobox(
            log_level_frame,
            textvariable=self.log_level,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            state="readonly",
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        return log_frame
    
    def start_recording(self, event_name):
        """開始記錄座標"""
        if self.recording_event:
            return
            
        self.recording_event = event_name
        self.status_var.set(f"準備記錄: {event_name} (請點擊遊戲視窗)")
        
        # 綁定滑鼠點擊事件
        self.root.bind('<Button-1>', lambda e: self.on_mouse_click(e.x, e.y))
        self.root.bind('<Escape>', self.cancel_recording)
        
    def on_mouse_click(self, x, y):
        """處理滑鼠點擊事件"""
        if not self.recording_event:
            return
            
        event_name = self.recording_event
        
        # 獲取遊戲窗口位置
        try:
            game_window = gw.getWindowsWithTitle(GAME_WINDOW_TITLE)[0]
            window_rect = game_window._rect
            
            # 計算相對於遊戲窗口的座標
            game_x = x - window_rect.left
            game_y = y - window_rect.top
            
            # 統一處理所有類型的座標記錄
            if event_name in ["點擊奇門遁甲卷的分頁(若想移動場所在第二頁，就需要點擊II)", "點擊移動場所名稱", "點擊移動按鈕"]:
                # 處理奇門遁甲卷配置
                if "teleport_config" not in self.config:
                    self.config["teleport_config"] = {"events": {}}
                if "events" not in self.config["teleport_config"]:
                    self.config["teleport_config"]["events"] = {}
                self.config["teleport_config"]["events"][event_name] = {
                    "interval": 5,
                    "max_wait": 10,
                    "coords": [game_x, game_y]
                }
                current_config = self.config["teleport_config"]["events"][event_name]
            
            elif event_name in ["開始狩獵", "結束狩獵"]:
                # 處理狩獵配置
                if "training_config" not in self.config:
                    self.config["training_config"] = {"events": {}}
                if "events" not in self.config["training_config"]:
                    self.config["training_config"]["events"] = {}
                self.config["training_config"]["events"][event_name] = {
                    "interval": 5,
                    "max_wait": 10,
                    "coords": [game_x, game_y]
                }
                current_config = self.config["training_config"]["events"][event_name]
            
            else:
                # 處理登入配置
                if "login_config" not in self.config:
                    self.config["login_config"] = {"events": {}}
                if event_name not in self.config["login_config"]["events"]:
                    self.config["login_config"]["events"][event_name] = {
                        "interval": 5,
                        "max_wait": 10,
                        "coords": [0, 0]
                    }
                self.config["login_config"]["events"][event_name]["coords"] = [game_x, game_y]
                current_config = self.config["login_config"]["events"][event_name]
            
            # 更新UI顯示
            if event_name in self.event_frames:
                frame = self.event_frames[event_name]
                frame.coord_label.config(text=f"({game_x}, {game_y})")
                
                # 更新間隔和等待時間
                if hasattr(frame, "interval_spin") and hasattr(frame, "max_wait_spin"):
                    current_config["interval"] = int(frame.interval_spin.get())
                    current_config["max_wait"] = int(frame.max_wait_spin.get())
            
            # 保存配置
            self.save_config()
            
            # 顯示成功消息
            self.log(f"已記錄 {event_name} 的座標: ({game_x}, {game_y})")
            
        except Exception as e:
            self.log(f"記錄座標失敗: {e}")
        
        # 解除綁定並重置狀態
        self.root.unbind('<Button-1>')
        self.root.unbind('<Escape>')
        self.recording_event = None
        self.status_var.set("就緒")
        
    def cancel_recording(self, event=None):
        """取消座標記錄"""
        self.root.unbind('<Button-1>')
        self.root.unbind('<Escape>')
        self.recording_event = None
        self.status_var.set("就緒")
    
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
                    self.auto_relogin()
            time.sleep(1)  # 基礎檢查間隔
    
    def auto_relogin(self):
        """自動重連主流程"""
        if not self.check_prerequisites():
            return
            
        self.prepare_for_relogin()
        
        try:
            self.handle_disconnection()
            self.handle_server_selection()
            self.handle_login()
            self.handle_secondary_password()
            self.handle_character_selection()
            self.handle_channel_selection()
            
        except Exception as e:
            self.log(f"重連過程中發生錯誤: {str(e)}")
            self.debug_log(traceback.format_exc())
        finally:
            self.cleanup_after_relogin()
    
    def check_prerequisites(self):
        """檢查自動重連前置條件"""
        if self.is_running:
            self.log("自動重連已在運行中")
            return False
            
        if not self.is_game_running():
            self.log("遊戲未運行，請先啟動遊戲")
            return False
            
        return True
    
    def prepare_for_relogin(self):
        """準備自動重連"""
        global is_relogining
        is_relogining = True
        self.is_running = True
        self.log("開始自動重連流程...")
    
    def handle_disconnection(self):
        """處理斷線確認"""
        self.log("等待斷線確認...")
        self.wait_and_click("點擊斷線彈出框的確定按鈕")
    
    def handle_server_selection(self):
        """處理伺服器選擇"""
        self.log("點擊伺服器...")
        self.wait_and_click("點擊伺服器")
    
    def handle_login(self):
        """處理登入按鈕"""
        self.log("點擊登入按鈕...")
        self.wait_and_click("點擊登入按鈕")
    
    def handle_secondary_password(self):
        """處理二次密碼"""
        if not self.config.get("enable_secondary_password", False):
            return
            
        self.log("輸入二次密碼...")
        for i in range(1, 5):
            self.wait_and_click(f"點擊二次密碼(第{i}位)")
            
        self.wait_and_click("點擊二次密碼確認按鈕")
    
    def handle_character_selection(self):
        """處理角色選擇"""
        self.log("點擊角色暱稱...")
        self.wait_and_click("點擊角色暱稱")
        self.wait_and_click("點擊進入遊戲按鈕")
    
    def handle_channel_selection(self):
        """處理分流選擇"""
        self.log("點擊分流...")
        self.wait_and_click("點擊分流")
        self.wait_and_click("點擊登入按鈕")
    
    def cleanup_after_relogin(self):
        """重連完成後清理"""
        global is_relogining
        is_relogining = False
        self.is_running = False
        self.log("自動重連完成")
    
    def wait_and_click(self, event_name):
        """等待並點擊指定事件"""
        event_config = self.config["login_config"]["events"].get(event_name, {})
        interval = event_config.get("interval", 5)
        max_wait = event_config.get("max_wait", 10)
        coords = event_config.get("coords", [0, 0])
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                self.click_game(*coords)
                self.log(f"已點擊 {event_name} ({coords[0]}, {coords[1]})")
                return
            except:
                time.sleep(interval)
                
        raise TimeoutError(f"等待 {event_name} 超時")
    
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
    
    def update_teleport_key(self, *args):
        """更新奇門遁甲卷快捷鍵設置"""
        key = self.teleport_var.get()
        self.config["teleport_key"] = key
        
        # 更新相關按鈕的狀態
        state = "disabled" if key == "不使用奇門遁甲卷" else "normal"
        
        # 更新事件框架的按鈕狀態
        teleport_events = [
            "點擊奇門遁甲卷的分頁(若想移動場所在第二頁，就需要點擊II)",
            "點擊移動場所名稱",
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