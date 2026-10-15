# 📖 規範自動查檢系統 (Standardized Inspection System - SIS)

跨平台桌面自動化工具，專門定時監控與自動比對各國工程標準法規（IEC、ISO、ASTM 等 16 家機構）的最新版本異動狀態。

---

## ✨ 核心特色與功能

- **16 家權威標準來源自動爬取**：
  - 支援 `IEC`、`ISO`、`ASTM`、`DIN`、`EN`、`ETSI`、`DNV`、`JEDEC`、`JIS`、`MIL`、`RTCA`、`SAE`、`Telcordia`、`UN`、`ANSI`、`ISTA`。
  - 支援 UN 規範的 Cloudflare / 瀏覽器安全防護繞過。
- **Microsoft Teams Webhook 每日自動推播**：
  - 每日背景排程完成後，自動發送美觀 Adaptive Card 卡片通知。
  - 按機構分類彙整異動規範（`【機構】• Standard_ID：前次版本 xxxx ➔ 最新版本 yyyy`）。
  - 當日無更新時亦自動回報安全巡檢報告；手動更新不會觸發通知以防洗版。
- **NAS 集中式帳號與身分權限分級**：
  - **集中管理**：透過 `config.json` 設定公司 NAS 路徑，所有員工電腦共用同一份帳號資料庫（`users.json`），免除各自建帳號的困擾。
  - **管理員（admin）**：可新增/刪除員工帳號、重設密碼、設定登入 Windows 網域限制，並具備 Teams Webhook 與更新時間設定權限。
  - **一般人員（user）**：僅可設定個人電腦的每日自動更新時間與登出。
  - **安全防護**：密碼經業界標準 bcrypt 雜湊加密儲存。
- **公司內部網路防護**：
  - 啟動前自動探測公司內部網路（NAS 資料夾是否可達），防止非授權外網使用。
- **Excel 4 欄位無縫匯入與匯出**：
  - 一鍵匯入/匯出追蹤清單，相容 4 欄標準格式，版本日期自動格式化為 `YYYY / MM / DD`。
- **背景常駐與靜默巡檢**：
  - 支援最小化常駐系統匣（System Tray），有新規範異動時圖示自動亮紅點提示。

---

## 📊 Excel 匯入/匯出格式 (標準 4 欄)

匯入與匯出的 `.xlsx` 檔案均嚴格遵守以下 4 欄格式（由左至右）：

| Platform (平台) | Standard_ID (規範編號) | URL (追蹤網址) | Current_Version (目前版本) |
| :--- | :--- | :--- | :--- |
| `IEC` | `60068-2-1` | `https://webstore.iec.ch/...` | `2023 / 01 / 15` |
| `ISO` | `9001` | `https://www.iso.org/...` | `2025 / -- / --` |

> 💡 **提示**：
> - 第 1 欄 `Platform` 支援合併儲存格向下自動遞補。
> - 第 2 欄 `Standard_ID`、第 3 欄 `URL` 為必填。
> - 第 4 欄 `Current_Version` 初次匯入時將作為新舊版本比對的基準。

---

## 🛠️ 開發環境安裝

### 1. 基礎環境
- **Python 3.10+**（Windows 安裝時請務必勾選 **`Add python.exe to PATH`**）。
- **Google Chrome** 瀏覽器（部分爬蟲驗證需使用）。

### 2. 建立虛擬環境與安裝依賴
在專案根目錄下開啟終端機（Terminal）：

```bash
# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境 (Windows)
venv\Scripts\activate
# 啟動虛擬環境 (macOS)
source venv/bin/activate

# 安裝相依套件
pip install -r requirements.txt

# 安裝 Playwright 瀏覽器核心 (UN 規範防護驗證用)
playwright install
```

### 3. 本地啟動測試
```bash
python main.py
```

---

## 📦 打包與發布指南

### 情況 A：打包給 Windows 使用者 (產生 `SIS.exe`)
請在 **Windows 電腦**上啟動虛擬環境後執行：
```cmd
pip install pyinstaller

pyinstaller --noconfirm --windowed --name "SIS" ^
  --icon "assets/app_icon.png" ^
  --add-data "assets;assets" ^
  --collect-all "customtkinter" ^
  main.py
```
> 打包輸出於 **`dist/SIS/`** 資料夾。

### 情況 B：打包給 macOS 使用者 (產生 `SIS.app`)
在 Mac 終端機直接執行內建腳本：
```bash
chmod +x build_mac.sh
./build_mac.sh
```
> 打包輸出於 **`dist/SIS.app`**。

---

## 🚀 交付與部署規範

分發給終端使用者時，僅需提供包含以下檔案的 `SIS` 資料夾（可壓縮為 zip）：

```text
SIS/
├── SIS.exe           # 主執行檔
├── _internal/        # 核心依賴庫
├── assets/           # 圖示資源
└── config.json       # 【唯一必要設定檔】填入公司 NAS 路徑
```

#### `config.json` 內容範例：
```json
{
  "nas_folder": "\\\\192.168.1.100\\shared\\SIS"
}
```

> ⚠️ **注意事項**：
> - **切勿隨附 `rules.json`、`settings.json`**：這些檔案會在使用者首次啟動時於本機自動生成。
> - **切勿隨附 `users.json`**：帳號名單統一存放在 `config.json` 所指定的 NAS 資料夾中，集中共用。
