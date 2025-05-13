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
import keyboard
import traceback

# 全局變量
GAME_WINDOW_TITLE = "墨香 Online-16年在地經營 官方正版授權"
GAME_PROCESS_NAME = "MHClient-Connect.exe"
is_relogining = False
is_running = False

# 事件配置 (繁體中文顯示)
LOGIN_CONFIG = {
    "點擊斷線彈出框的確定按鈕": {"操作前等待 30 秒": True, "coords": [976, 602]},
    "點擊伺服器": {"操作前等待 15 秒": True, "coords": [954, 422]},
    "點擊登入按鈕": {"操作前等待 10 秒": True, "coords": [953, 689]},
    "若登入失敗的確認按鈕(非必填)": {"操作前等待 10 秒": True, "coords": [973, 602]},
    "點擊二次密碼(第一位)": {"操作前等待 1 秒": True, "coords": [944, 537]},
    "點擊二次密碼(第二位)": {"操作前等待 1 秒": True, "coords": [944, 537]},
    "點擊二次密碼(第三位)": {"操作前等待 1 秒": True, "coords": [944, 537]},
    "點擊二次密碼(第四位)": {"操作前等待 1 秒": True, "coords": [944, 537]},
    "點擊二次密碼確認按鈕": {"操作前等待 5 秒": True, "coords": [951, 571]},
    "點擊角色暱稱": {"操作前等待 5 秒": True, "coords": [1809, 219]},
    "點擊進入遊戲按鈕": {"操作前等待 5 秒": True, "coords": [1815, 378]},
    "點擊分流": {"操作前等待 5 秒": True, "coords": [944, 420]},
    "點擊登入按鈕": {"操作前等待 5 秒": True, "coords": [954, 695]}
}

TELEPORT_CONFIG = {
    "teleport_key": "不使用奇門遁甲卷",
    "events": {
        "點擊奇門遁甲卷的分頁(I or II)": {"操作前等待 5 秒": True, "coords": [855, 659]},
        "點擊移動場所名稱": {"操作前等待 5 秒": True, "coords": [940, 581]},
        "點擊移動按鈕": {"操作前等待 5 秒": True, "coords": [952, 706]}
    }
}

TRAINING_CONFIG = {
    "events": {
        "點擊地面讓角色走路": {"操作前等待 5 秒": True, "coords": [313, 454]},
        "點擊自動狩獵圖標": {"操作前等待 3 秒": True, "coords": [1392, 1061]},
        "點擊開始自動狩獵按鈕": {"操作前等待 3 秒": True, "coords": [732, 760]},
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
        # 查找源配置中的等待時間
        wait_time = 5  # 預設等待時間
        for key in source.keys():
            if key.startswith("操作前等待"):
                wait_time = int(key.split()[1])
                break
                
        # 確保目標配置有等待時間
        has_wait_time = False
        for key in list(target.keys()):
            if key.startswith("操作前等待"):
                has_wait_time = True
                break
                
        if not has_wait_time:
            target[f"操作前等待 {wait_time} 秒"] = True
            
        # 確保有座標
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
        
        # 保存配置按鈕
        save_btn = ttk.Button(button_frame,
                            text="保存配置",
                            command=self.save_config)
        save_btn.pack(side=tk.LEFT, padx=5)
        
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
            wait_time = 5  # 預設等待時間
            for key in event_data.keys():
                if key.startswith("操作前等待"):
                    wait_time = int(key.split()[1])
                    break
            event_data.setdefault(f"操作前等待 {wait_time} 秒", True)
            event_data.setdefault("coords", [0, 0])
            
            frame = ttk.Frame(parent)
            frame.pack(fill=tk.X, pady=2)
            
            # 事件名稱
            ttk.Label(frame, text=event_name, width=25).pack(side=tk.LEFT, padx=2)
            
            # 操作前等待時間
            ttk.Label(frame, text="操作前等待(秒)").pack(side=tk.LEFT)
            frame.wait_spin = ttk.Spinbox(frame, from_=1, to=300, width=5)
            frame.wait_spin.pack(side=tk.LEFT, padx=2)
            frame.wait_spin.set(wait_time)
            
            # 綁定等待時間變更事件
            frame.wait_spin.bind('<KeyRelease>', lambda e, f=frame, en=event_name, cn=config_name: self.on_wait_time_change(e, f, en, cn))
            frame.wait_spin.bind('<ButtonRelease-1>', lambda e, f=frame, en=event_name, cn=config_name: self.on_wait_time_change(e, f, en, cn))
            
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
        self.status_var.set(f"正在記錄: {event_name} 的座標")
        
        # 創建一個新的座標記錄視窗
        self.record_window = tk.Toplevel(self.root)
        self.record_window.title(f"記錄座標: {event_name}")
        self.record_window.geometry("400x250")
        self.record_window.resizable(False, False)
        self.record_window.transient(self.root)
        self.record_window.protocol("WM_DELETE_WINDOW", self.cancel_recording)
        
        # 顯示說明
        ttk.Label(self.record_window, text="每秒將在日誌區顯示目前滑鼠座標").pack(pady=5)
        
        # 座標輸入框架
        coord_frame = ttk.Frame(self.record_window)
        coord_frame.pack(pady=10, fill=tk.X, padx=20)
        
        # X 座標輸入
        ttk.Label(coord_frame, text="X 座標:").grid(row=0, column=0, padx=5, pady=5)
        self.x_entry = ttk.Entry(coord_frame, width=10)
        self.x_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Y 座標輸入
        ttk.Label(coord_frame, text="Y 座標:").grid(row=0, column=2, padx=5, pady=5)
        self.y_entry = ttk.Entry(coord_frame, width=10)
        self.y_entry.grid(row=0, column=3, padx=5, pady=5)
        
        # 使用目前滑鼠座標按鈕
        ttk.Button(self.record_window, text="使用目前滑鼠座標", command=self.use_current_mouse_position).pack(pady=5)
        
        # 確認按鈕
        ttk.Button(self.record_window, text="確認記錄座標", command=self.confirm_coordinates).pack(pady=5)
        
        # 取消按鈕
        ttk.Button(self.record_window, text="取消", command=self.cancel_recording).pack(pady=5)
        
        # 開始定時更新滑鼠座標
        self.update_mouse_position()
        
        # 綁定 Escape 鍵取消記錄
        self.root.bind('<Escape>', self.cancel_recording)
        
        self.log(f"開始記錄 {event_name} 的座標")
        
    def update_mouse_position(self):
        """定時更新滑鼠座標顯示"""
        if not self.recording_event or not hasattr(self, 'record_window'):
            return
            
        try:
            # 取得目前滑鼠的座標
            x, y = pyautogui.position()
            self.current_mouse_pos = (x, y)
            
            # 每秒在日誌區顯示目前滑鼠座標
            self.log(f"目前滑鼠座標: ({x}, {y})")
            
            # 每 1000ms (1秒) 更新一次
            self.record_window.after(1000, self.update_mouse_position)
            
        except Exception as e:
            self.log(f"更新滑鼠座標失敗: {str(e)}")
            
    def use_current_mouse_position(self):
        """使用目前滑鼠座標填充輸入框"""
        if hasattr(self, 'current_mouse_pos'):
            x, y = self.current_mouse_pos
            self.x_entry.delete(0, tk.END)
            self.x_entry.insert(0, str(x))
            self.y_entry.delete(0, tk.END)
            self.y_entry.insert(0, str(y))
            
    def confirm_coordinates(self):
        """確認記錄座標"""
        if not self.recording_event:
            return
            
        try:
            # 從輸入框取得座標
            try:
                x = int(self.x_entry.get())
                y = int(self.y_entry.get())
            except ValueError:
                messagebox.showerror("輸入錯誤", "請輸入有效的整數座標")
                return
                
            self.process_coordinates(x, y)
            
            # 關閉記錄視窗
            if hasattr(self, 'record_window'):
                self.record_window.destroy()
                
        except Exception as e:
            self.log(f"記錄座標失敗: {str(e)}")
            self.log(traceback.format_exc())
        
    def process_coordinates(self, game_x, game_y):
        """處理捕獲到的座標"""
        if not self.recording_event:
            return
            
        event_name = self.recording_event
        
        try:
            self.log(f"記錄座標: ({game_x}, {game_y})")
            
            # 統一處理所有類型的座標記錄
            if event_name in ["點擊奇門遁甲卷的分頁(I or II)", "點擊移動場所名稱", "點擊移動按鈕"]:
                # 處理奇門遁甲卷配置
                if "teleport_config" not in self.config:
                    self.config["teleport_config"] = {"events": {}}
                if "events" not in self.config["teleport_config"]:
                    self.config["teleport_config"]["events"] = {}
                self.config["teleport_config"]["events"][event_name] = {
                    "操作前等待 5 秒": True,
                    "coords": [game_x, game_y]
                }
                current_config = self.config["teleport_config"]["events"][event_name]
            
            elif event_name in ["點擊地面讓角色走路", "點擊自動狩獵圖標", "點擊開始自動狩獵按鈕"]:
                # 處理狩獵配置
                if "training_config" not in self.config:
                    self.config["training_config"] = {"events": {}}
                if "events" not in self.config["training_config"]:
                    self.config["training_config"]["events"] = {}
                self.config["training_config"]["events"][event_name] = {
                    "操作前等待 5 秒": True,
                    "coords": [game_x, game_y]
                }
                current_config = self.config["training_config"]["events"][event_name]
            
            else:
                # 處理登入配置
                if "login_config" not in self.config:
                    self.config["login_config"] = {"events": {}}
                if event_name not in self.config["login_config"]["events"]:
                    self.config["login_config"]["events"][event_name] = {
                        "操作前等待 5 秒": True,
                        "coords": [0, 0]
                    }
                self.config["login_config"]["events"][event_name]["coords"] = [game_x, game_y]
                current_config = self.config["login_config"]["events"][event_name]
            
            # 更新UI顯示
            if event_name in self.event_frames:
                frame = self.event_frames[event_name]
                frame.coord_label.config(text=f"({game_x}, {game_y})")
                
                # 更新等待時間
                if hasattr(frame, "wait_spin"):
                    wait_time = int(frame.wait_spin.get())
                    # 移除所有舊的等待時間鍵
                    for key in list(current_config.keys()):
                        if key.startswith("操作前等待"):
                            del current_config[key]
                    # 添加新的等待時間
                    current_config[f"操作前等待 {wait_time} 秒"] = True
            
            # 保存配置
            self.save_config()
            
            # 顯示成功消息
            self.log(f"已記錄 {event_name} 的座標: ({game_x}, {game_y})")
            
        except Exception as e:
            self.log(f"記錄座標失敗: {e}")
            import traceback
            self.log(traceback.format_exc())
        
        # 解除綁定並重置狀態
        self.root.unbind('<Button-1>')
        self.root.unbind('<Escape>')
        self.recording_event = None
        self.status_var.set("就緒")
        
    def cancel_recording(self, event=None):
        """取消座標記錄"""
        # 關閉記錄視窗
        if hasattr(self, 'record_window'):
            self.record_window.destroy()
            
        self.root.unbind('<Escape>')
        self.recording_event = None
        self.status_var.set("就緒")

    def create_game_info_frame(self, parent):
        """創建遊戲資訊框架"""
        info_frame = ttk.LabelFrame(parent, text="遊戲資訊", padding=10)
        info_frame.pack(fill=tk.X, pady=5)
        return info_frame
    
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
        global is_relogining
        while self.is_running:
            if not is_relogining:
                if is_game_disconnected():
                    self.log("[偵測到斷線] 開始自動重連流程...")
                    is_relogining = True
                    self.auto_relogin()
                    is_relogining = False
            time.sleep(1)  # 基礎檢查間隔
    
    def auto_relogin(self):
        """自動重連主流程"""
        global is_relogining
        
        if not self.check_prerequisites():
            is_relogining = False  # 重設重連狀態
            return
            
        self.prepare_for_relogin()
        
        try:
            self.log("開始執行重連步驟...")
            self.handle_disconnection()
            self.handle_server_selection()
            self.handle_login()
            self.handle_secondary_password()
            self.handle_character_selection()
            self.handle_channel_selection()
            self.log("重連成功完成!")
            
        except Exception as e:
            self.log(f"重連過程中發生錯誤: {str(e)}")
            self.debug_log(traceback.format_exc())
        finally:
            self.cleanup_after_relogin()
    
    def check_prerequisites(self):
        """檢查自動重連前置條件"""
        # 移除對 self.is_running 的檢查，因為重連運行時 is_running 本來就應該是 True
        # 改為使用全局變量 is_relogining 來避免重複重連
            
        if not self.is_game_running():
            self.log("遊戲未運行，請先啟動遊戲")
            return False
            
        return True
        
    def is_game_running(self):
        """檢查遊戲是否正在運行"""
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] == GAME_PROCESS_NAME:
                    return True
            return False
        except Exception as e:
            self.log(f"檢查遊戲運行狀態失敗: {e}")
            return False
    
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
    
    def on_wait_time_change(self, event, frame, event_name, config_name):
        """處理等待時間變更事件"""
        try:
            # 嘗試從 spinbox 獲取值
            wait_time = int(frame.wait_spin.get())
            
            # 驗證範圍
            if wait_time < 1:
                wait_time = 1
                frame.wait_spin.set(wait_time)
            elif wait_time > 300:
                wait_time = 300
                frame.wait_spin.set(wait_time)
            
            # 更新配置
            current_config = self.config[config_name]["events"][event_name]
            
            # 移除所有舊的等待時間鍵
            for key in list(current_config.keys()):
                if key.startswith("操作前等待"):
                    del current_config[key]
            
            # 添加新的等待時間
            current_config[f"操作前等待 {wait_time} 秒"] = True
            
            # 保存配置
            self.save_config()
            
        except ValueError:
            # 如果輸入的不是數字，恢復為預設值
            frame.wait_spin.set(5)
            self.on_wait_time_change(event, frame, event_name, config_name)  # 運行一次以確保配置更新
    
    def update_teleport_key(self, *args):
        """更新奇門遁甲卷快捷鍵設置"""
        key = self.teleport_var.get()
        self.config["teleport_key"] = key
        
        # 更新相關按鈕的狀態
        state = "disabled" if key == "不使用奇門遁甲卷" else "normal"
        
        # 更新事件框架的按鈕狀態
        teleport_events = [
            "點擊奇門遁甲卷的分頁(I or II)",
            "點擊移動場所名稱",
            "點擊移動按鈕"
        ]
        
        for event_name in teleport_events:
            if event_name in self.event_frames:
                self.event_frames[event_name].record_btn.config(state=state)
        self.save_config()

    def execute_event(self, event_name, event_config):
        """執行事件並嚴格遵守等待時間"""
        # 獲取等待時間（默認5秒）
        wait_sec = next((int(k.split()[1]) for k in event_config 
                       if k.startswith("操作前等待")), 5)
        
        # 分段等待以便及時響應停止指令
        start = time.time()
        while time.time() - start < wait_sec:
            if not self.is_running:
                return False
            time.sleep(0.1)  # 短間隔檢查
            
        # 執行點擊操作
        if self.is_running:
            x, y = event_config["coords"]
            self.click_game(x, y)
            return True
        return False

    def stop_relogin(self):
        """強制停止所有操作"""
        self.is_running = False
        
        # 確保執行緒停止
        if self.relogin_thread and self.relogin_thread.is_alive():
            try:
                self.relogin_thread.join(timeout=2.0)
                if self.relogin_thread.is_alive():
                    self.log("警告：執行緒未正常結束，強制終止中")
            except Exception as e:
                self.log(f"停止執行緒時出錯: {e}")
        
        self.log("已完全停止自動重連")
        self.update_ui_state()

    def restore_game_window(self):
        """多重恢復遊戲窗口到前台"""
        max_attempts = 3
        for attempt in range(1, max_attempts+1):
            try:
                windows = gw.getWindowsWithTitle(self.config["game_window_title"])
                if windows:
                    game_window = windows[0]
                    if game_window.isMinimized:
                        self.debug_log(f'還原窗口 (嘗試 {attempt}/{max_attempts})')
                        game_window.restore()
                        time.sleep(1)
                        self.debug_log(f'聚焦窗口 (嘗試 {attempt}/{max_attempts})')
                    game_window.activate()
                    time.sleep(0.5)  # 確保窗口完成聚焦
                    return True
            except Exception as e:
                self.debug_log(f"恢復窗口失敗 (嘗試 {attempt}/{max_attempts}): {e}")
                time.sleep(1)
        return False

    def click_game(self, x, y, clicks=1):
        """點擊遊戲窗口指定位置"""
        if not self.restore_game_window():
            self.log("警告：無法聚焦遊戲窗口")
            return False
        
        try:
            pyautogui.click(x, y, clicks=clicks)
            time.sleep(0.3)  # 點擊後固定等待時間
            return True
        except Exception as e:
            self.log(f"點擊遊戲失敗: {e}")
            return False

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