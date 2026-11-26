# 開發約定（大家都要遵守，才串得起來）

## 1. 分層與依賴方向

```
frontend (Vue)  ──HTTP/JSON──>  routers  ──>  services  ──>  PostgreSQL
                                   │             ├──> app.market / app.fees / app.clock（共用核心）
                                   │             └──> behavior_log ──> MongoDB
                                 schemas（合約）
scheduler ──> jobs ──> crawler.prices.import_daily_prices  ──> settlement.settle_day
```

- **routers**：只解析參數、檢查角色、呼叫 service。不寫 SQL。
- **services**：業務邏輯與 SQL。第一個參數一律是 `conn: psycopg.Connection`，**不自己開連線**。
- **共用核心**（框架已實作，改動前先在群組講）：
  - `app/clock.py`：唯一的「現在時間」來源 `clock.now()`（台北時間）。**禁止** `datetime.now()`。
  - `app/market.py`：交易日、市場狀態、委託歸屬日、參考價。
  - `app/fees.py`：手續費、交易稅、凍結金額、平均成本、已實現損益。**禁止**自己另寫公式。
  - `app/constants.py`：狀態字串、費率、時間。**禁止**在程式裡直接寫 `'待成交'` 這類字串。
- **service 函式簽名不要改**：router、scheduler、其他模組都依賴它。真的要改先開 issue。

## 2. 資料庫

- 連線是 **autocommit 模式**：單一 `conn.execute()` 立即生效；多步驟寫入一定要包
  `with conn.transaction():`（例外時自動 rollback）。
- 列鎖順序全系統固定：**ORDERS → ACCOUNT → HOLDING**（避免 deadlock），用 `SELECT ... FOR UPDATE`。
- 金額、價格一律 `Decimal` / `numeric`，**禁止 float**。
- 參數一律用 `%s` / `%(name)s` placeholder，**禁止**字串拼接 SQL（SQL injection）。
- 不刪除使用者、委託、成交、證券：用狀態欄位（`凍結`、`已取消`、`停用`）。自選股可以真的 DELETE。
- Schema 變更：改 `backend/sql/*.sql`，並在 PR 說明；改完全員跑一次 `python -m scripts.init_db`。

## 3. 錯誤處理

- 業務錯誤：`raise AppError("CODE", "給使用者看的中文訊息", status_code)`，code 補到 `docs/API.md`。
- 尚未完成：保留 `raise NotImplementedYet(...)`，前端會顯示 🚧，不會壞掉。

## 4. 回傳格式

- service 回傳 `dict` / `list[dict]`，key 與 `app/schemas.py` 的 response model **完全一致**。
- SQL 用 `AS` 把欄位命名成 schema 的 key（例如 `LAG(close_price) OVER (...) AS prev_close`）。
- `open_price`（真實開盤價，存在 DB）和 `prev_close`（昨收／參考價，LAG 推算）是兩個不同的值，不要混用。

## 5. 前端

- 只透過 `frontend/js/api.js` 呼叫後端；新增端點時先加在這裡。
- 金額只做顯示格式化（`format.js`），不做業務計算；需要計算的數字由後端提供。
- 台灣慣例：漲 = 紅（`.up`）、跌 = 綠（`.down`）。

## 6. Git 流程

- `main` 永遠可以跑。每人在自己的 branch 開發：`feat/A-crawler`、`feat/B-orders`…
- PR 前：`cd backend && .venv/bin/python -m pytest` 全過。
- 不要 commit：`.env`、`.venv/`、`data/raw/`、`__pycache__/`（已寫在 `.gitignore`）。
