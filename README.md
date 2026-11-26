# IMinvestor 股票模擬交易平台

資料庫管理（115-1）第 10 組期末專案。以臺灣證券交易所（TWSE）每日真實行情為基礎的模擬下單平台：
使用者以虛擬資金 1,000,000 元限價下單，**系統於每個交易日 15:00 自動抓取當日行情並結算**。

- 關聯式資料庫：PostgreSQL（11 張表，交易資料）
- NoSQL：MongoDB（使用者行為紀錄：搜尋、瀏覽、登入）
- 後端：Python 3.9+、FastAPI、psycopg 3（手寫 SQL）、APScheduler
- 前端：Vue 3（CDN，免建置），透過 REST API 與後端溝通

文件：[實作計畫書](IMPLEMENTATION_PLAN.md)｜[API 規格](docs/API.md)｜[開發約定](docs/CONVENTIONS.md)｜[分工](docs/TASKS.md)

## 專案結構

```
backend/
  app/            FastAPI：config, db, clock, market, fees, security, schemas, jobs, scheduler
    routers/      HTTP 端點（auth, market, quotes, watchlist, orders, admin）
    services/     業務邏輯與 SQL（每個檔案有負責模組）
  crawler/        TWSE 爬蟲（證券清單、每日行情、休市日）
  sql/            00_schema / 01_triggers / 02_indexes / 03_seed / analysis/
  scripts/        init_db, init_mongo, backfill, gen_synthetic, benchmark_index
  tests/
frontend/         index.html + js/（Vue 3 ES modules）+ css/
docs/             API 規格、開發約定、分工
backup/           資料庫備份（pg_dump / mongodump）
```

## 安裝

### 1. 需求

- PostgreSQL 16 以上（本機 `localhost:5432`）
- Python 3.9 以上
- MongoDB 7 以上（`localhost:27017`；沒有也能啟動，只是不會記錄行為資料）
- 能連上網路（爬蟲與前端 Vue CDN）

### 2. 建立資料庫帳號（只需一次）

以 PostgreSQL 超級使用者執行（會詢問 postgres 的密碼）：

```bash
psql -h localhost -U postgres -d postgres -c "CREATE ROLE iminvestor LOGIN PASSWORD 'iminvestor_dev' CREATEDB;" -c "CREATE DATABASE iminvestor OWNER iminvestor;"
```

> macOS 以 EDB 安裝程式安裝時，`psql` 位於 `/Library/PostgreSQL/18/bin/psql`。
> `iminvestor_dev` 是本機開發用密碼，與 `.env.example` 一致。

### 3. 後端

```bash
cp .env.example .env
```

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
cd backend && .venv/bin/python -m scripts.init_db
```

```bash
cd backend && .venv/bin/python -m scripts.backfill --from 2026-01-01
```

```bash
cd backend && .venv/bin/uvicorn app.main:app --port 8000
```

- `init_db` 會**重建所有資料表**並建立預設 Admin（帳密見 `.env` 的 `ADMIN_USERNAME` / `ADMIN_PASSWORD`）。
- `backfill` 只在安裝時執行一次；之後每天的行情由 15:00 自動排程取得。
- API 文件：<http://localhost:8000/docs>

### 4. 前端

```bash
cd frontend && python3 -m http.server 5173
```

開啟 <http://localhost:5173>。要展示併行控制時，開兩個瀏覽器視窗（或一般＋無痕）同時操作。

### 5. 測試

```bash
cd backend && .venv/bin/python -m pytest
```

## 使用說明（簡短示例）

1. 註冊帳號 → 自動取得 1,000,000 元虛擬資金。
2. 「行情」搜尋 `2330` → 進入個股頁，查看最新與歷史行情（開盤、最高、最低、收盤、成交量）；**漲跌以昨收（參考價，前一交易日收盤價）為基準**。
3. 在下單面板輸入價格（需在參考價 ±10% 內，參考價＝歸屬日前一交易日收盤價）與股數 → 送出。頂部狀態列顯示這筆委託的**歸屬交易日**。
4. 歸屬日 15:00，系統自動匯入當日行情並結算：買單「委託價 > 當日最低價」、賣單「委託價 < 當日最高價」即成交。
5. 「庫存」查看未實現損益與總資產；「委託」「成交／資金」查看明細。
6. Admin 登入後可管理證券、交易日曆、凍結帳戶、查看全站統計與每日自動結算紀錄。

## 市場時間規則

| 台北時間（交易日） | 狀態 | 新委託歸屬 |
|---|---|---|
| 09:00 前 | 盤前 | 當日 |
| 09:00–13:30 | 盤中 | 當日 |
| 13:30–15:00 | 收盤 | 當日 |
| 15:00 起至結算完成 | 結算中 | 暫停下單 |
| 結算完成後 | 盤後 | 下一交易日 |
| 非交易日 | 休市 | 下一交易日 |
