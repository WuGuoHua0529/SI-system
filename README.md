# 📖 規範版本監控系統 (Standardized Inspection System) 

跨平台桌面自動化工具，專門監控與追蹤各國標準規範 (IEC, ISO, ASTM 等) 的最新版本發布狀態。

## ✨ 核心功能
* **多來源爬蟲**：支援 15+ 種規範來源。
* **背景定時更新**：可自訂每日自動比對時間，不干擾作業。
* **狀態燈與通知**：更新時介面將亮起綠底，同時系統匣圖示切換為紅點。
* **企業網域鎖定**：限定授權的 Windows 網域才可開啟軟體。
* **Excel 無縫匯入**：一鍵匯入追蹤清單。

---

## 📊 Excel 匯入格式 (必備 4 欄)

請確保 `.xlsx` 遵守以下格式（由左至右）：

| Platform (平台) | Standard_ID (規範編號) | URL (追蹤網址) | Current_Version (目前版本) |
| :--- | :--- | :--- | :--- |
| `IEC` | `60068-2-1` | `https://...` | `2023-01` |

> 💡 **Tip**: 第 1 欄支援合併儲存格；第 2、3 欄為必填；第 4 欄作為更新比對的舊版基準。

---

## 🚀 開發與部署指南 (Windows 專屬)

請嚴格依照以下順序建立乾淨的編譯環境：

### 1. 基礎環境安裝
* 下載並安裝 [Python 3.10+](https://www.python.org/downloads/)。
  ⚠️ **極度重要**：安裝時畫面下方的 **`Add python.exe to PATH` 務必打勾**。
* 下載並安裝 Google Chrome 瀏覽器。
* 安裝 VSCode，並於左側擴充功能 (`Ctrl+Shift+X`) 安裝微軟官方的 **Python** 擴充套件。

### 2. 建立虛擬環境
在 VSCode 開啟本專案，並於終端機輸入：
```bash
python -m venv venv
```
*(執行後無文字輸出屬正常現象，左側會多出 venv 資料夾)*

**啟動環境**：
1. 按下 `Ctrl + Shift + P`。
2. 搜尋並執行 `Python: Select Interpreter`。
3. 選擇路徑包含 `venv/Scripts/python.exe` 的選項。
4. 關閉當前終端機，開啟新終端機 (`Terminal -> New Terminal`)，確認游標前方出現 `(venv)`。

### 3. 安裝依賴套件
確認在 `(venv)` 狀態下，依序執行：
```bash
# 安裝清單內的所有套件
pip install -r requirements.txt

# 下載 UN 爬蟲必備的瀏覽器核心
playwright install
```

---

## 📦 測試與打包

**啟動測試**：
```bash
python main.py
```

**轉為獨立執行檔 (.exe)**：
```bash
pyinstaller --noconfirm --windowed --icon=assets/app_icon.png --add-data "assets;assets" main.py
```
> 打包產出物位於 `dist/main.exe`，此檔案可直接交由客戶使用，不需安裝 Python。
