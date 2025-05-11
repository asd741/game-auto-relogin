# 墨香自動重連工具 🎮

[![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)

## 功能介紹 ✨

這是一個專為墨香線上設計的自動重連工具，具有以下特點：

- 🔄 自動檢測遊戲狀態並重新連線
- 🎯 支援自動練功配置
- 🗺️ 支援奇門遁甲捲傳送
- ⚙️ 可自訂各種事件配置
- 📝 即時運行日誌顯示

## 系統需求 💻

- Windows 作業系統
- Python 3.13 或以上版本
- 墨香線上遊戲客戶端

## 安裝方式 📥

1. 下載最新版本的執行檔
2. 直接執行 `墨香自動重連工具.exe`

## 開發者指南 👨‍💻

### 環境設置

```bash
# 安裝依賴套件
pip install {專案中使用到的套件}
```

### 打包方式

```bash
# 打包成單一執行檔
pyinstaller --onefile --windowed --name "墨香自動重連工具" --icon=NONE mhs_auto_relogin.py
```

> 注意：打包前建議先刪除 `build` 和 `dist` 資料夾以確保打包結果正確

## 使用說明 📖

1. 啟動工具
2. 設定遊戲環境和各項配置
3. 點擊開始執行
4. 工具會自動監控遊戲狀態並處理斷線重連

## 授權協議 📜

本專案採用 MIT 授權協議，詳見 [LICENSE](LICENSE) 文件。