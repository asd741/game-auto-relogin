import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext
import json
import os
import time
import threading
import pydirectinput
import pyautogui
import ctypes
import pygetwindow as gw
import win32gui
import win32con
import socket
import copy
import psutil
import sys

# 新的、符合您提供JSON結構的預設配置常量
EXACT_DEFAULT_CONFIG = {
    "game_env": "聊天優先",
    "game_process_name": "MHClient-Connect.exe",
    "game_window_title": "墨香 Online-16年在地經營 官方正版授權",
    "login_config": {
        "events": {
            "若登入失敗的確認按鈕(非必填)": { "coords": [973, 602], "wait_time": 10 },
            "點擊二次密碼(第一位)": { "coords": [944, 537], "wait_time": 1 },
            "點擊二次密碼(第三位)": { "coords": [944, 537], "wait_time": 1 },
            "點擊二次密碼(第二位)": { "coords": [944, 537], "wait_time": 1 },
            "點擊二次密碼(第四位)": { "coords": [944, 537], "wait_time": 1 },
            "點擊二次密碼確認按鈕": { "coords": [951, 571], "wait_time": 5 },
            "點擊伺服器": { "coords": [954, 422], "wait_time": 15 },
            "點擊分流": { "coords": [944, 420], "wait_time": 5 },
            "點擊斷線彈出框的確定按鈕": { "coords": [976, 602], "wait_time": 3 },
            "點擊登入按鈕": { "coords": [954, 695], "wait_time": 5 },
            "點擊角色暱稱": { "coords": [1809, 219], "wait_time": 5 },
            "點擊進入遊戲按鈕": { "coords": [1815, 378], "wait_time": 5 }
        }
    },
    "os_type": "Windows",
    "teleport_config": {
        "events": {
            "點擊奇門遁甲卷的分頁(I or II)": { "coords": [855, 659], "wait_time": 5 },
            "點擊移動場所名稱": { "coords": [940, 581], "wait_time": 5 },
            "點擊移動按鈕": { "coords": [952, 706], "wait_time": 5 }
        },
        "teleport_key": "不使用奇門遁甲卷" # 確保 teleport_key 在 teleport_config 中也有一份
    },
    "teleport_key": "不使用奇門遁甲卷",
    "training_config": {
        "events": {
            "點擊地面讓角色走路": { "coords": [313, 454], "wait_time": 5 },
            "點擊自動狩獵圖標": { "coords": [1392, 1061], "wait_time": 3 },
            "點擊開始自動狩獵按鈕": { "coords": [732, 760], "wait_time": 3 }
        }
    }
}

GAME_WINDOW_TITLE = EXACT_DEFAULT_CONFIG["game_window_title"]
GAME_PROCESS_NAME = EXACT_DEFAULT_CONFIG["game_process_name"]

# 移除了舊的 LOGIN_CONFIG, TELEPORT_CONFIG, TRAINING_CONFIG 全域變數定義
# 因為它們的功能已被 EXACT_DEFAULT_CONFIG 取代

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
        
        # 確保 script_dir 是絕對路徑
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(script_dir, "mhs_config.json")
        
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
        return copy.deepcopy(EXACT_DEFAULT_CONFIG)
        
    def merge_config(self, default, loaded):
        """合併預設配置與載入的配置"""
        # 確保頂層key存在
        for key in default.keys():
            if key not in loaded:
                loaded[key] = copy.deepcopy(default[key]) # 如果顶层key不存在，则从默认配置深拷贝
            elif isinstance(default[key], dict) and isinstance(loaded[key], dict):
                # 如果是字典，遞歸合併
                self.deep_merge_dicts(default[key], loaded[key])
            # else loaded[key] 的值将被保留

        # 特別處理 events，確保所有預設事件都存在，並且每個事件都有 coords 和 wait_time
        for config_key in ["login_config", "teleport_config", "training_config"]:
            if config_key in default and config_key in loaded:
                default_events = default[config_key].get("events", {})
                loaded_events = loaded[config_key].setdefault("events", {})

                for event_name, default_event_data in default_events.items():
                    if event_name not in loaded_events:
                        loaded_events[event_name] = copy.deepcopy(default_event_data)
                    else:
                        # 如果事件已存在，確保它有 coords 和 wait_time
                        loaded_events[event_name].setdefault("coords", default_event_data.get("coords", [0,0]))
                        loaded_events[event_name].setdefault("wait_time", default_event_data.get("wait_time", 5))
            elif config_key in default and config_key not in loaded: # 如果加載的配置中缺少整個config_key
                 loaded[config_key] = copy.deepcopy(default[config_key])
        
        # 確保 teleport_key 在 teleport_config 和頂層都存在且一致
        default_teleport_key = default.get("teleport_key", "不使用奇門遁甲卷")
        loaded.setdefault("teleport_key", default_teleport_key)
        if "teleport_config" in loaded:
            loaded["teleport_config"].setdefault("teleport_key", default_teleport_key)
        elif "teleport_config" in default: # 如果加載的配置沒有teleport_config，但預設有
            loaded["teleport_config"] = copy.deepcopy(default["teleport_config"])
            loaded["teleport_config"].setdefault("teleport_key", default_teleport_key)
            
        return loaded

    def deep_merge_dicts(self, default_dict, user_dict):
        """輔助函數：深度合併字典，優先使用 user_dict 的值"""
        for key, default_value in default_dict.items():
            if key not in user_dict:
                user_dict[key] = copy.deepcopy(default_value)
            elif isinstance(default_value, dict) and isinstance(user_dict.get(key), dict):
                self.deep_merge_dicts(default_value, user_dict[key])
            # 如果 user_dict[key] 已存在且不是字典（或 default_value 不是字典），則保留 user_dict[key] 的值

    def ensure_event_defaults(self, target, source):
        """確保事件配置有預設值，特別是 coords 和 wait_time"""
        # 這個方法在新的 merge_config 邏輯下可能不再直接需要，
        # 因為合併時會直接從 default_event_data 獲取並 setdefault。
        # 但保留以防萬一其他地方調用。
        target.setdefault("coords", source.get("coords", [0, 0]))
        target.setdefault("wait_time", source.get("wait_time", 5))
    
    def load_config(self):
        """載入配置文件"""
        try:
            if not os.path.exists(self.config_file):
                self.log(f"配置文件 {self.config_file} 不存在，將創建新的預設配置。")
                default_config = self.load_default_config()
                self.config = default_config # 先將 self.config 設為預設值
                
                # 現在 save_config 應該能正確處理檔案不存在的情況
                if self.save_config(): # 嘗試保存這個預設配置到 self.config_file
                    self.log(f"預設配置已成功創建並保存到 {self.config_file}")
                else:
                    self.log(f"警告: 創建預設配置文件 {self.config_file} 失敗。程式將使用記憶體中的預設配置。")
                return default_config # 返回預設配置
            
            # 如果文件存在，正常讀取和合併
            self.log(f"從 {self.config_file} 載入配置")
            with open(self.config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
            
            default_for_merge = self.load_default_config()
            merged_config = self.merge_config(default_for_merge, loaded_config)
            self.config = merged_config # 更新當前運行的配置
            self.log("配置載入並合併完成。")
            return merged_config

        except json.JSONDecodeError:
            self.log(f"錯誤: 配置文件 {self.config_file} 格式損壞。將載入預設配置並嘗試覆蓋。")
            default_config = self.load_default_config()
            self.config = default_config
            self.save_config() # 嘗試用預設配置覆蓋損壞的檔案
            return default_config
        except Exception as e:
            self.log(f"載入配置時發生錯誤: {e}. 將載入預設配置。")
            default_config = self.load_default_config()
            self.config = default_config
            # 這裡可以選擇是否在載入失敗時也嘗試保存一次預設配置
            # self.save_config()
            return default_config

    def save_config(self, filepath_override=None):
        """保存當前配置到文件。可以接受一個覆蓋的路徑參數用於測試。"""
        target_file = filepath_override if filepath_override else self.config_file
        current_config_content = {} # 初始化為空字典

        try:
            # 確保目標目錄存在
            os.makedirs(os.path.dirname(target_file), exist_ok=True)

            if os.path.exists(target_file):
                self.log(f"配置文件 {target_file} 存在，將讀取並合併後保存。")
                try:
                    with open(target_file, 'r', encoding='utf-8') as f:
                        current_config_content = json.load(f)
                except json.JSONDecodeError:
                    self.log(f"警告: 配置文件 {target_file} 格式錯誤，將使用當前程序配置覆蓋。")
                    # 如果JSON解碼失敗，current_config_content 保持為空，後面會用 self.config 完全覆蓋
                except Exception as e:
                    self.log(f"讀取配置文件 {target_file} 時發生未知錯誤: {e}，將使用當前程序配置覆蓋。")
                    # 其他讀取錯誤，也用 self.config 覆蓋
            else:
                self.log(f"配置文件 {target_file} 不存在，將直接使用當前程序配置創建。")
                # 如果檔案不存在，current_config_content 保持為空，意味著 self.config 將成為檔案的全部內容

            # 準備要寫入的內容
            # 如果 current_config_content 非空 (即成功讀取了舊配置)，則進行合併
            # 否則 (檔案不存在或讀取失敗)，直接使用 self.config
            if current_config_content: 
                # 深度合併配置（只更新現有key），以 self.config 為主，補充到 current_config_content
                # 這裡的邏輯是，UI上所做的更改 (self.config) 應該優先於檔案中的舊值
                # 我們創建一個新的字典來保存合併結果，避免修改 self.config
                config_to_save = copy.deepcopy(current_config_content) # 從檔案內容開始
                self.deep_merge_dicts(self.config, config_to_save) # 將 self.config 的更改合併進去
            else:
                config_to_save = copy.deepcopy(self.config) # 直接使用當前的程式配置
            
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=4, ensure_ascii=False)
            self.log(f"配置已成功保存到 {target_file}")
            return True # 表示保存成功

        except Exception as e:
            self.log(f"保存配置到 {target_file} 失敗: {e}")
            print(f"[ERROR] 保存配置到 {target_file} 失敗: {e}", file=sys.stderr)
            return False # 表示保存失敗

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
                
            frame = ttk.Frame(parent)
            frame.pack(fill=tk.X, pady=2)
            
            # 事件名稱
            ttk.Label(frame, text=event_name, width=25).pack(side=tk.LEFT, padx=2)
            
            # 等待時間 Spinbox
            frame.wait_label = ttk.Label(frame, text="操作前等待(秒):")
            frame.wait_label.pack(side=tk.LEFT, padx=(0, 5))
            
            # 從配置中獲取 wait_time (event_data 是從 self.config[config_name]["events"][event_name] 來的)
            current_wait_time = event_data.get("wait_time", 5) 
            
            frame.wait_spin_var = tk.IntVar(value=current_wait_time)
            frame.wait_spin = ttk.Spinbox(frame, from_=0, to=300, textvariable=frame.wait_spin_var, width=5)
            frame.wait_spin.pack(side=tk.LEFT, padx=5) # <--- 新增這一行來顯示 Spinbox
            
            # 綁定等待時間變更事件
            frame.wait_spin.bind('<KeyRelease>', lambda e, f=frame, en=event_name, cn=config_name: self.on_wait_time_change(e, f, en, cn))
            frame.wait_spin.bind('<ButtonRelease-1>', lambda e, f=frame, en=event_name, cn=config_name: self.on_wait_time_change(e, f, en, cn))
            
            # 座標記錄按鈕
            frame.record_btn = ttk.Button(frame, text="記錄座標", 
                                        command=lambda e=event_name: self.start_recording(e))
            frame.record_btn.pack(side=tk.LEFT, padx=5)
            
            # 座標顯示
            frame.coord_label = ttk.Label(frame, text=f"({event_data.get('coords', [0, 0])[0]}, {event_data.get('coords', [0, 0])[1]})")
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
        
        # 解除綁定並重置狀態
        self.root.unbind('<Button-1>')
        self.root.unbind('<Escape>')
        self.recording_event = None
        self.status_var.set("就緒")
        
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
                    "wait_time": 5,
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
                    "wait_time": 5,
                    "coords": [game_x, game_y]
                }
                current_config = self.config["training_config"]["events"][event_name]
            
            else:
                # 處理登入配置
                if "login_config" not in self.config:
                    self.config["login_config"] = {"events": {}}
                if event_name not in self.config["login_config"]["events"]:
                    self.config["login_config"]["events"][event_name] = {
                        "wait_time": 5,
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
                    wait_time = int(frame.wait_spin_var.get())
                    # 移除所有舊的等待時間鍵
                    for key in list(current_config.keys()):
                        if key.startswith("操作前等待"):
                            del current_config[key]
                    # 添加新的等待時間
                    current_config["wait_time"] = wait_time
            
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
                is_relogining = True
                self.auto_relogin()
                is_relogining = False
                # if is_game_disconnected():
                #     self.log("[偵測到斷線] 開始自動重連流程...")
                #     is_relogining = True
                #     self.auto_relogin()
                #     is_relogining = False
            time.sleep(1)  # 基礎檢查間隔
    
    def auto_relogin(self):
        """自動重連主流程"""
        if not self.is_running:
            return
            
        if not self.check_prerequisites():
            is_relogining = False  # 重設重連狀態
            return
            
        self.prepare_for_relogin()
        
        try:
            self.log("開始執行重連步驟...")
            
            # 使用短路邏輯，任一步驟失敗立即返回
            if not self.handle_disconnection():
                return
                
            if not self.handle_server_selection():
                return
                
            if not self.handle_login():
                return
                
            if not self.handle_secondary_password():
                return
                
            if not self.handle_character_selection():
                return
                
            if not self.handle_channel_selection():
                return
                
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
        if not self.is_running:
            return
            
        self.log("等待斷線確認...")
        return self.wait_and_click("點擊斷線彈出框的確定按鈕")
    
    def handle_server_selection(self):
        """處理伺服器選擇"""
        if not self.is_running:
            return
            
        self.log("點擊伺服器...")
        return self.wait_and_click("點擊伺服器")
    
    def handle_login(self):
        """處理登入按鈕"""
        if not self.is_running:
            return
            
        self.log("點擊登入按鈕...")
        return self.wait_and_click("點擊登入按鈕")
    
    def handle_secondary_password(self):
        """處理二次密碼"""
        if not self.is_running:
            return
            
        if not self.config.get("enable_secondary_password", False):
            return
            
        self.log("輸入二次密碼...")
        for i in range(1, 5):
            if not self.wait_and_click(f"點擊二次密碼(第{i}位)"):
                return
        return self.wait_and_click("點擊二次密碼確認按鈕")
    
    def handle_character_selection(self):
        """處理角色選擇"""
        if not self.is_running:
            return
            
        self.log("點擊角色暱稱...")
        if not self.wait_and_click("點擊角色暱稱"):
            return
        return self.wait_and_click("點擊進入遊戲按鈕")
    
    def handle_channel_selection(self):
        """處理分流選擇"""
        if not self.is_running:
            return
            
        self.log("點擊分流...")
        if not self.wait_and_click("點擊分流"):
            return
        return self.wait_and_click("點擊登入按鈕")
    
    def cleanup_after_relogin(self):
        """重連完成後清理"""
        global is_relogining
        is_relogining = False
        self.is_running = False
    
    def wait_and_click(self, event_name, config_type="login"):
        """等待並點擊指定事件"""
        if not self.is_running:
            return False
            
        # 統一讀取配置結構
        config = self.config.get(f"{config_type}_config", {})
        if not config:
            raise ValueError(f"缺少 {config_type}_config 配置節點")
            
        events = config.get("events", {})
        if not events:
            raise ValueError(f"{config_type}_config 中缺少 events 配置")
            
        event_config = events.get(event_name)
        if event_config is None:
            raise ValueError(f"events 中缺少 {event_name} 事件配置")
        
        if "wait_time" not in event_config:
            raise ValueError(f"{event_name} 事件缺少 wait_time 配置")
        if "coords" not in event_config:
            raise ValueError(f"{event_name} 事件缺少 coords 配置")
            
        wait_sec = event_config["wait_time"]
        coords = event_config["coords"]
        
        time.sleep(wait_sec)
        if not self.is_running:
            return False
        try:
            self.click_game(*coords)
            self.log(f"已點擊 {event_name} ({coords[0]}, {coords[1]})")
            return True
        except Exception as e:
            raise RuntimeError(f"點擊 {event_name} 失敗: {str(e)}")
    
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
            new_wait_value = int(frame.wait_spin_var.get()) # 從 IntVar 獲取值
            if new_wait_value < 0:
                new_wait_value = 0
            
            self.config[config_name]["events"][event_name]["wait_time"] = new_wait_value
            self.log(f"事件 '{event_name}' 的等待時間更新為: {new_wait_value} 秒")
            self.save_config() 
        except ValueError:
            self.log("錯誤：等待時間必須是有效的數字")
        except Exception as e:
            self.log(f"更新等待時間時出錯: {str(e)}")

    def perform_event(self, event_name, event_data):
        """執行事件並嚴格遵守等待時間"""
        if not self.is_running:
            return False

        coords = event_data.get("coords")
        # 從 event_data 獲取 wait_time，如果不存在則預設為0
        wait_seconds = event_data.get("wait_time", 0)

        if coords and len(coords) == 2:
            x, y = coords
            self.log(f"執行事件: {event_name} - 座標 ({x}, {y}), 操作前等待 {wait_seconds} 秒")
            
            # 操作前等待
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            
            if not self.is_running: # 等待後再次檢查狀態
                self.log(f"操作在等待 {event_name} 後被停止")
                return False

            # 執行點擊
            if not self.click_game(x, y):
                self.log(f"事件 {event_name} 的點擊操作失敗，可能未找到遊戲窗口。")
                # 根據需要，這裡可以決定是否要拋出錯誤或僅記錄並繼續
                # raise RuntimeError(f"點擊 {event_name} 失敗: 遊戲窗口無法聚焦") 
                return False # 或者標記為失敗並允許流程繼續
            return True
        else:
            self.log(f"事件 {event_name} 的座標配置無效: {coords}")
            return False

    def update_teleport_key(self, *args):
        """更新奇門遁甲卷快捷鍵設置，並同步UI狀態"""
        try:
            key = self.teleport_var.get()
            self.config["teleport_key"] = key
            self.config["teleport_config"]["teleport_key"] = key # 確保兩處同步
            self.log(f"奇門遁甲卷使用方式更新為: {key}")

            # 更新相關按鈕的狀態
            # 這裡的 state 決定按鈕是否可點擊
            new_state = tk.DISABLED if key == "不使用奇門遁甲卷" else tk.NORMAL

            # 定義哪些事件與奇門遁甲相關
            teleport_related_events = [
                "點擊奇門遁甲卷的分頁(I or II)",
                "點擊移動場所名稱",
                "點擊移動按鈕"
            ]

            # 遍歷所有事件框架，更新相關按鈕的狀態
            # 確保 self.event_frames 已被正確填充
            if hasattr(self, 'event_frames'):
                for event_name, frame_controls in self.event_frames.items():
                    if event_name in teleport_related_events:
                        if hasattr(frame_controls, 'record_btn') and frame_controls.record_btn:
                            frame_controls.record_btn.config(state=new_state)
                        if hasattr(frame_controls, 'test_btn') and frame_controls.test_btn:
                             frame_controls.test_btn.config(state=new_state)
            
            self.save_config()
        except Exception as e:
            self.log(f"更新奇門遁甲卷設定時出錯: {e}")

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
        if not self.is_running:
            return False
            
        if not self.restore_game_window():
            self.log("警告：無法聚焦遊戲窗口")
            return False
        
        try:
            pydirectinput.moveTo(x, y)  # 先移動到位置
            time.sleep(0.5)     
            self.log(f"移動到位置 ({x}, {y})")
            pydirectinput.mouseDown()   # 按下鼠標
            time.sleep(0.05)            # 保持按下狀態（有些遊戲需要）
            pydirectinput.mouseUp()     # 放開鼠標
            return True
        except Exception as e:
            self.log(f"點擊遊戲失敗: {e}")
            return False

    def is_game_disconnected(self):
        """檢查遊戲是否斷線"""
        try:
            if not self.is_game_running():
                return True
                
            # 檢查斷線彈窗
            hwnd = win32gui.FindWindow(None, GAME_WINDOW_TITLE)
            if hwnd == 0:
                return True
                
            # 檢查網絡狀態
            if not self.is_network_ok():
                return True
                
            return False
        except:
            return True
    
    def is_network_ok(self):
        """檢查網絡是否正常"""
        try:
            # 簡單的網絡檢查邏輯
            socket.create_connection(("www.google.com", 80), timeout=5)
            return True
        except:
            return False
    
    def debug_log(self, message):
        """調試日誌"""
        if DEBUG:
            self.log(f"[DEBUG] {message}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MHSAutoReloginApp(root)
    root.mainloop()