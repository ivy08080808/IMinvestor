# IMinvestor 實作計畫書（前後端 + 爬蟲 + 開盤時間）

> 版本：2026-11-26 v5　｜　依據：課程規格《DB115-1_project.pdf》、第 10 組《專案計劃書》
> 狀態：**待確認**（確認後才開始寫程式）
>
> v2 修改：移除模擬時鐘與 Admin「手動匯入並結算」；改為**每個交易日 15:00 全自動抓取一次行情並結算**。Demo 以歷史紀錄呈現。
> v3 修改：第 7 節三項已決定——不刪除使用者（以凍結代替、FK 改 Restrict）、回補自 2026-01-01 起、技術選型照第 1 節（RDBMS 為 PostgreSQL）。
> v4（架構實作時調整）：
> 1. 新增第 11 張表 `SETTLEMENT_RUN`（每日自動結算紀錄）：15:00 抓取失敗時當日沒有行情，無法再用「當日有無行情」判斷是否已結算；此表同時是「每天只跑一次」的保證。
> 2. 前端改用 Vue 3 CDN（免 Node.js 建置），本機沒有 Docker，改為直接使用本機 PostgreSQL。
> 3. 分工改為四個模組（A 行情與爬蟲、B 交易核心、C 帳務與管理、D 前端／NoSQL／分析），見 `docs/TASKS.md`。
> v5：`DAILY_PRICE` 新增 `open_price`（TWSE 真實開盤價）；前一交易日收盤價改稱「昨收（參考價）」`prev_close`，仍以 LAG 推算，作為漲跌、±10% 限制與今日損益的基準（§2）。

---

## 0. 本次變更摘要

| # | 變更 | 影響範圍 |
|---|------|----------|
| 1 | **開盤價存真實值；昨收（參考價）= 前一交易日收盤價**（`DAILY_PRICE` 新增 `open_price`，昨收以 window function 推算） | Schema、爬蟲、行情 API、前端行情頁、報告 1.1.2 與資料字典 |
| 2 | **爬蟲**：自 TWSE 抓取證券清單、每日行情、休市日 | 新增 `crawler/` 模組、回補腳本、每日排程 |
| 3 | **開盤時間感知＋全自動結算**：系統依台北時間判斷市場狀態與委託歸屬日；每個交易日 15:00 自動抓一次行情並結算，無任何手動步驟 | 新增 `clock` / `market` 模組、排程器、前端狀態列 |

Schema 相對報告的修改：`DAILY_PRICE` 新增 `open_price`（§2）、使用者相關 FK 刪除動作改 Restrict（§7）、新增 `SETTLEMENT_RUN`（v4）。

---

## 1. 技術選型

| 層 | 選擇 | 理由 |
|----|------|------|
| RDBMS | PostgreSQL 16 | 報告已採用（`bigserial`、保留字 USERS/ORDERS） |
| NoSQL | MongoDB 7 | 儲存行為紀錄（搜尋、瀏覽、登入），schema-less、寫入量大 |
| 後端 | Python 3.12 + FastAPI + psycopg 3（**手寫 SQL，不用 ORM**） | 課程要求報告列出 SQL；手寫 SQL 才能精確控制 `FOR UPDATE`、交易邊界 |
| 排程 | APScheduler（`Asia/Taipei`） | 每日 15:00 匯入行情＋結算 |
| 認證 | bcrypt（對應 `Password_hash char(60)`）+ JWT | — |
| 前端 | Vue 3（CDN ES module，免建置） | 前後端分離，透過 REST API 溝通；不需 Node.js，降低安裝風險 |
| 部署 | 本機 PostgreSQL + MongoDB，`uvicorn` 跑後端、`python -m http.server` 跑前端 | 降低助教安裝失敗風險（失敗最多扣 10 分），步驟見 README |

---

## 2. 變更一：開盤價與參考價（v5 修訂）

### 2.1 定義

兩個不同的值，**不可混用**：

| 名稱 | API 欄位 | 來源 | 用途 |
|---|---|---|---|
| 開盤價 | `open_price` | TWSE 當日真實開盤價，爬蟲匯入、**存在 `DAILY_PRICE`** | 行情頁顯示 |
| 昨收（參考價） | `prev_close` | 前一交易日收盤價，以 `LAG()` 推算、**不存** | 漲跌、±10% 下單限制、今日損益 |

令證券 $s$ 的行情序列依交易日排序為 $d_1 < d_2 < \dots < d_n$（只含 `DAILY_PRICE` 有資料的日子，停牌日自動跳過）：

$$
\text{PrevClose}(s, d_k) = \text{Close}(s, d_{k-1}),\qquad
\text{Change}(s, d_k) = \text{Close}(s, d_k) - \text{PrevClose}(s, d_k)
$$

$k=1$ 時昨收顯示 `—`。使用者在交易日 $d$ 看到的最新行情是前一交易日的資料（含該日真實開盤價）；$d$ 下單時的參考價＝前一交易日收盤價，與 `market.reference_price` 為同一個值。

### 2.2 SQL

**個股歷史行情**（先算 window 再篩日期，否則區間第一天的 LAG 會是 NULL）：

```sql
SELECT trade_date, prev_close, open_price, high_price, low_price, close_price, volume,
       close_price - prev_close AS change,
       ROUND((close_price - prev_close) / prev_close * 100, 2) AS change_pct
FROM (
    SELECT trade_date, open_price, high_price, low_price, close_price, volume,
           LAG(close_price) OVER (PARTITION BY security_id ORDER BY trade_date) AS prev_close
    FROM daily_price
    WHERE security_id = %(sid)s
) t
WHERE trade_date BETWEEN %(from)s AND %(to)s
ORDER BY trade_date DESC;
```

**行情列表／自選股（每檔取最新兩筆）**：用 `LATERAL ... ORDER BY trade_date DESC LIMIT 2`，走 PK `(security_id, trade_date)` 的 index backward scan。
複雜度：$m$ 檔證券為 $O(m \log N)$（$N$ 為 `DAILY_PRICE` 筆數），不需掃全表。

### 2.3 報告需同步修改的地方

- 1.1.2 第 2 點：「……查看當日行情與歷史行情，包括開盤價、最高價、最低價、收盤價、成交量與漲跌（漲跌以前一交易日收盤價為基準）。」
- ER diagram：`DAILY_PRICE` 加上屬性 `Open_price`。
- Relational schema 圖與表 9（`DAILY_PRICE` 資料字典）：加一列 `Open_price｜開盤價｜numeric(10,2)｜Not Null｜> 0`，並註明 `Low_price ≤ Open_price ≤ High_price`。
- 表 11（FD）：`(Security_id, Trade_date) → {Open_price, High_price, Low_price, Close_price, Volume}`；正規化結論不變（仍為 BCNF）。
- 2.2 節文字：「……記錄開盤價（Open_price）、最高價……；前一交易日收盤價（參考價）可由前一筆行情推得，故不另外儲存。」

---

## 3. 變更二：TWSE 爬蟲

### 3.1 資料來源（2026-11-19 已實測可用）

| 用途 | Endpoint | 格式／重點 |
|------|----------|------------|
| 證券清單＋分類 | `https://isin.twse.com.tw/isin/C_public.jsp?strMode=2` | Big5 HTML；欄位含代號名稱、上市日、產業別、**CFICode** |
| 每日全市場行情（可指定歷史日期） | `https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date=YYYYMMDD&type=ALLBUT0999&response=json` | `tables[]` 中標題含「每日收盤行情」的那張；欄位：證券代號、成交股數、開/高/低/收… 約 1,390 檔 |
| 最新一日行情（備援） | `https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL` | JSON；只有最新交易日 |
| 休市日 | `https://www.twse.com.tw/rwd/zh/holidaySchedule/holidaySchedule?response=json` | 實測 `queryYear` 參數無效，只回傳最新公布年度（目前為 116 年 = 2027） |

### 3.2 處理規則

**證券分類**（對應 `SECURITY_CATEGORY`）：
- CFICode `ES*` → 普通股
- CFICode `CE*` 且代號結尾 `B`（如 `00679B`）→ 債券 ETF
- 其他 `CE*` → ETF
- 其餘（特別股、TDR、權證、受益證券）→ **不匯入**

**行情清洗**：去千分位逗號；收盤價為 `--`（當日無成交）→ 不寫入（符合報告「無行情＝停牌」）；`Volume = 0` 不寫入（符合 `Volume > 0` 約束）；只寫入 `SECURITY` 中已存在的代號。
寫入使用 `INSERT ... ON CONFLICT (security_id, trade_date) DO NOTHING`，重跑**冪等**。

**交易日曆**：
- 歷史日期：以 MI_INDEX 為準——當日 `stat == "OK"` 且有行情 → 交易日，否則非交易日（比休市表更可靠，且休市表抓不到舊年度）。
- 未來日期：週六日預設非交易日，再套用休市表；注意「市場無交易，僅辦理結算交割作業」也是**非交易日**，「開始交易日」「最後交易日」是**交易日**。
- Admin 仍可在後台手動修改（颱風假等臨時休市）。

**禮貌爬取**：TWSE 對高頻請求會暫時封鎖 IP。每次請求間隔 3–5 秒、失敗指數退避（最多 5 次）、原始 JSON 快取於 `data/raw/MI_INDEX/YYYYMMDD.json`，回補中斷可續跑。

### 3.3 回補（安裝時執行一次）

`python -m scripts.backfill --from 2026-01-01 --to today`

回補只在系統初次建置時執行一次，用來建立歷史行情；之後每天的新行情一律由 15:00 自動排程取得（見 4.3），不再手動抓取。

- 2026-01-01 至 11/19 約 215 個交易日 × 1 request，以 4 秒間隔約 **15 分鐘**。
- 預估 `DAILY_PRICE` ≈ 1,300 檔 × 215 日 ≈ **28 萬筆**，滿足「至少一張表上萬筆」；index 效能比較另以 `ORDERS`（約 50 萬筆合成資料）為主。
- 到 12/14 繳交時，排程會再自動累積約 18 個交易日的行情。

---

## 4. 變更三：開盤時間感知

### 4.1 時間來源與全自動原則

- 所有「現在時間」都經由 `clock.now()` 取得，**一律為真實的台北時間**（`Asia/Taipei`），不提供模擬時間。
- 行情匯入與結算**完全自動**：系統不提供 Admin「手動匯入」或「手動結算」功能。
- 每個交易日只在 **15:00 抓取一次**當日行情，抓完立即結算。
- 使用者時間軸：

| 時間 | 使用者看到的 |
|---|---|
| 交易日 $d$ 15:00 前 | 行情最新為前一交易日；委託歸屬 $d$ |
| $d$ 15:00 | 系統自動抓 $d$ 的行情 → 結算 $d$ 的委託（約數秒至一分鐘） |
| $d$ 15:00 結算完成後 | 可查到 $d$ 的行情、成交結果、更新後的庫存與資金；新委託歸屬下一交易日 |
| 下一交易日 $d'$ | 行情頁最新行情為 $d$（含 $d$ 的真實開盤價）；昨收（參考價）= $d$ 的收盤價，±10% 限制以此為基準 |

**Demo 方式**：以歷史紀錄呈現，不現場觸發結算。回補的真實歷史行情（2026 起）＋以結算引擎在歷史行情上重播產生的使用者委託／成交／持股（見第 6 節），讓助教可直接瀏覽各交易日的行情、委託成交結果與損益變化。現場可示範下單、取消、併行控制；該委託會在當日（或下一交易日）15:00 自動結算。

### 4.2 市場狀態機

令 $t$ 為現在時間、$d=\text{date}(t)$、$T(d)$ 表示 $d$ 是否為交易日、$\text{next}(d)$ 為 $d$ 之後最近的交易日。

| 狀態 | 條件 | 新委託歸屬日 | 可否下單 |
|------|------|--------------|----------|
| 休市 | $\lnot T(d)$ | $\text{next}(d)$ | 可 |
| 盤前 | $T(d)$, $t < 09{:}00$ | $d$ | 可 |
| 盤中 | $T(d)$, $09{:}00 \le t < 13{:}30$ | $d$ | 可 |
| 收盤 | $T(d)$, $13{:}30 \le t < 15{:}00$ | $d$ | 可 |
| **結算中** | $T(d)$, $t \ge 15{:}00$，且 $d$ 尚未結算完成 | — | **暫停**（見下） |
| 盤後 | $T(d)$, $t \ge 15{:}00$，且 $d$ 已結算完成 | $\text{next}(d)$ | 可 |

**為何「結算中」要暫停下單**：15:00 後的委託歸屬 $\text{next}(d)$，其 ±10% 價格限制以「歸屬日之前最近一筆行情」= $d$ 的收盤價為準；若 $d$ 的行情尚未匯入，系統會誤用 $d-1$ 的收盤價。暫停到結算完成即可避免。

**「已結算完成」的判定**（不需新增表）：$d$ 的 `DAILY_PRICE` 已有資料，且不存在 `belong_date = d AND status = '待成交'` 的委託。

> 盤中（09:00–13:30）在本系統中**不做即時撮合**（報告已明定以收盤後最高/最低價判斷），此狀態只供前端顯示，讓使用者知道真實市場正在交易。

### 4.3 排程

| 時間（台北） | Job | 說明 |
|---|---|---|
| 交易日 15:00 | `import_and_settle(d)` | 抓 MI_INDEX($d$) **一次** → 寫入 `DAILY_PRICE` → 結算 $d$ 的委託。不重試、不需人工介入 |
| 每日 06:00 | `sync_securities()` | 同步證券清單（新上市證券） |
| 每週一 06:00 | `sync_holidays()` | 更新休市表 |
| 後端啟動時 | `catch_up()` | 只處理伺服器停機而錯過 15:00 排程的交易日：依日期順序對每個錯過的日子各執行一次 `import_and_settle`（每日仍只抓一次） |

**15:00 抓取失敗時**：依報告假設「每日行情皆能順利取得」，正常情況不會發生（實測 TWSE 收盤行情約 14:00 前後即已公布）。若仍發生（如網路中斷），依報告「當日無行情資料者視為停牌，其委託不成交，並於當日失效」處理，並寫入錯誤 log。此為已知限制，報告中註明即可。

**防重複執行**：結算前取 `pg_try_advisory_lock(<settle_key>)`，即使誤開多個 worker 也只會有一個在結算。

### 4.4 委託歸屬日（報告規則的程式化）

```python
def belong_date(t: datetime) -> date:
    """依報告規則：交易日 15:00 前送出歸屬當日，否則歸屬下一個交易日。"""
    d = t.date()
    if is_trading_day(d) and t.time() < time(15, 0):
        return d
    return next_trading_day(d)  # SELECT MIN(calendar_date) ... WHERE > d AND is_trading_day
```

若 `TRADING_CALENDAR` 找不到下一個交易日（未來日曆未登錄），拒絕下單並提示 Admin 補日曆。

---

## 5. 核心交易邏輯與併行控制

### 5.1 鎖順序（避免 deadlock）

全系統固定以 **`ORDERS` → `ACCOUNT` → `HOLDING`** 的順序取得列鎖：

| 操作 | 取鎖 |
|------|------|
| 下單（買） | `ACCOUNT FOR UPDATE` → 檢查可用餘額 → 轉凍結 → `INSERT ORDERS` |
| 下單（賣） | `ACCOUNT FOR UPDATE`（檢查帳戶狀態）→ `HOLDING FOR UPDATE` → 檢查可賣股數 → 凍結 → `INSERT ORDERS` |
| 取消 | `ORDERS FOR UPDATE`（確認仍為待成交）→ `ACCOUNT`/`HOLDING` → 釋放凍結 |
| 結算單筆 | `ORDERS FOR UPDATE`（確認仍為待成交）→ `ACCOUNT` → `HOLDING` → 寫 `TRADE` |
| 凍結帳戶 | `ACCOUNT FOR UPDATE` |

下單不鎖既有 `ORDERS` 列，因此不會與取消／結算形成環狀等待。Isolation level 用預設 READ COMMITTED + 顯式列鎖。

### 5.2 結算演算法

對交易日 $d$：

1. `SELECT order_id FROM orders WHERE belong_date = d AND status = '待成交' ORDER BY order_id`
2. 對每筆委託開**獨立交易**（失敗只回滾該筆，符合報告「任一步驟失敗則該筆回復」）：
   - 重新 `SELECT ... FOR UPDATE` 並確認仍為待成交（取消先拿到鎖 → 這裡跳過）
   - 帳戶凍結／證券停用／當日無行情 → 已失效、釋放凍結
   - 成交條件：買 $P > L_d$；賣 $P < H_d$（等於不成交）
   - 費用：$\text{fee} = \max\!\big(1, \lfloor 0.001425 \cdot Pq \rfloor\big)$，$\text{tax} = \lfloor r_c \cdot Pq \rfloor$（僅賣出）
   - 買進後平均成本：$\bar c' = \dfrac{\bar c \cdot Q + Pq + \text{fee}}{Q + q}$（保留 4 位）
   - 已實現損益：$Pq - \text{fee} - \text{tax} - \bar c \cdot q$
3. 不成交 → 已失效、釋放凍結。

複雜度：$K$ 筆待成交委託為 $O(K \log N)$（每筆皆走 PK／partial index）；交易數 $K$ 個、每個交易持鎖時間為常數。
所有金額用 `Decimal`／`numeric`，**禁止 float**。

### 5.3 前端資料同步

兩個以上前端連同一後端：前端每 5 秒輪詢「市場狀態＋自己的帳戶摘要」，任何操作成功後立即重新拉取。Demo 腳本：
1. 兩視窗同一帳號同時賣出超過持股 → 只有一筆成功（`HOLDING` 列鎖）。
2. 取消委託與 15:00 自動結算同時發生 → 只會有一方生效（現場不易剛好卡在 15:00，改以自動化測試腳本重現並錄影說明）。
3. Admin 凍結帳戶 → 使用者下一次下單即被拒。

---

## 6. 課程規格中尚未涵蓋、需一併完成的項目

| 規格要求 | 計畫 |
|---|---|
| NoSQL 資料庫 + 至少一項分析 | MongoDB `behavior_events`：`{user_id, type: search/view_security/login, security_id, query, ts}`；index `{type, ts}`、`{security_id, ts}`。分析：**「瀏覽→下單轉換率」**——近 7 日瀏覽次數 Top 20 證券 vs. 實際委託數 |
| ≥ 10 個功能的 SQL（≥5 使用者／業務、≥5 分析，≥1 用到 NoSQL） | 業務：下單、取消、結算、庫存損益、行情（開盤價＋昨收推算）、凍結帳戶。分析：個股成交統計與委託成交率、使用者報酬率排行、委託價偏離參考價 vs. 成交機率、各類別持股集中度、委託送出時段分布、瀏覽→下單轉換率（NoSQL） |
| Index 與效能比較 | `orders(belong_date) WHERE status='待成交'`（partial index，結算用）、`orders(user_id, submit_time DESC)`、`daily_price(trade_date)`、`security` 名稱搜尋用 `pg_trgm`。以 `EXPLAIN ANALYZE` 比較建立前後 |
| 大量資料 | `DAILY_PRICE` 約 28 萬筆（真實，2026 起）；另生成約 2,000 名使用者、約 50 萬筆委託（**用同一套結算引擎在 2026 歷史行情上重播**，保證持股／成交／資金一致） |
| GitHub + README + DB 備份 | `README.md`（安裝、啟動、測試帳號）、`backup/iminvestor.dump`（`pg_dump -Fc`）、Mongo `mongodump` |

---

## 7. 已決定事項

1. **不刪除使用者，以凍結代替**
   系統不提供刪除使用者的功能；要停用帳戶時由 Admin 將 `ACCOUNT.Status` 設為「凍結」，所有委託、成交、持股紀錄完整保留。資料庫層同步把使用者相關 FK 的 On Delete 改為 **Restrict**，即使有人直接下 `DELETE` 也會被擋下（課程規格第 4 頁註腳的反例）：

   | FK | On Delete（原 → 新） | On Update |
   |---|---|---|
   | `ACCOUNT.User_id` → `USERS` | Cascade → **Restrict** | Cascade |
   | `HOLDING.User_id` → `ACCOUNT` | Cascade → **Restrict** | Cascade |
   | `ORDERS.User_id` → `ACCOUNT` | Cascade → **Restrict** | Cascade |
   | `TRADE.Order_id` → `ORDERS` | Cascade → **Restrict** | Cascade |
   | `WATCHLIST.User_id` → `ACCOUNT` | Cascade（不變，自選股非交易紀錄） | Cascade |

   **報告需同步修改**：
   - 2.3 節第一段改為：「……屬於使用者的資金帳戶、持股、委託與成交紀錄，於被參考的使用者或委託被刪除時一律拒絕刪除（Restrict）；系統不提供刪除使用者的功能，使用者停用以帳戶凍結代替，以保留完整的交易歷史。自選股則隨帳戶一併刪除（Cascade）……」
   - 表 2、3、5、6 的 On Delete 欄依上表修改。
   - 1.1.3 第 3 點補充：「……被凍結的帳戶無法下單；系統不提供刪除使用者，凍結即為停用帳戶的方式。」

2. **回補區間**：2026-01-01 至今（見 3.3）。

3. **技術選型**：照第 1 節。RDBMS 為 PostgreSQL；另因課程規格 3.2 節要求「至少一個 NoSQL 資料庫儲存行為資料」，仍需搭配 MongoDB（只存行為紀錄，交易資料全在 PostgreSQL）。

---

## 8. 專案目錄

```
final project/
├── docker-compose.yml          # postgres:16, mongo:7
├── README.md
├── backup/                     # pg_dump / mongodump
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI 入口
│   │   ├── config.py           # 環境變數（DB 連線、排程時間等）
│   │   ├── db.py               # psycopg connection pool、Mongo client
│   │   ├── clock.py            # 台北時間 now()
│   │   ├── market.py           # 交易日曆、市場狀態、belong_date
│   │   ├── routers/            # auth, quotes, watchlist, orders, portfolio, admin
│   │   └── services/           # order_service, settlement, pricing, behavior_log
│   ├── crawler/                # twse_client, securities, prices, holidays
│   ├── scheduler.py
│   ├── sql/
│   │   ├── schema.sql          # 10 張表 + constraints
│   │   ├── triggers.sql        # Role 檢查、Realized_profit 檢查
│   │   ├── indexes.sql
│   │   └── analysis/           # 報告用的 10+ 條 SQL
│   ├── scripts/                # backfill.py, gen_synthetic.py, benchmark_index.py
│   └── tests/                  # 費用計算、歸屬日、併行（多執行緒同時下單）
└── frontend/
    └── src/pages/              # Login, Market, SecurityDetail, Watchlist, Orders,
                                # Trades, Portfolio, Cash, admin/*
```

**前端重點畫面**：頂部狀態列顯示台北時間、市場狀態徽章（休市／盤前／盤中／收盤／結算中／盤後）、距 15:00 截止倒數、「新委託將歸屬：11/20（四）」；下單面板即時顯示允許價格區間 $[0.9C,\ 1.1C]$ 與預估凍結金額。

---

## 9. 時程（C1 截止 12/14）

| 階段 | 日期 | 產出 |
|---|---|---|
| M1 資料層 | 11/19 – 11/23 | `schema.sql`、爬蟲、回補完成、交易日曆 |
| M2 後端 | 11/24 – 11/30 | 所有 API、下單／取消／結算、15:00 自動排程、單元測試 |
| M3 前端 | 12/1 – 12/6 | 全部頁面（**12/4 諮詢時可展示雛形**） |
| M4 資料與效能 | 12/7 – 12/10 | 合成資料、Mongo 分析、index benchmark、併行測試 |
| M5 交付 | 12/11 – 12/14 | README、DB 備份、報告第 4.2.3 節素材、影片腳本 |

---

## 10. 實作順序（確認後我會依此進行）

1. `docker-compose.yml` + `schema.sql`（含第 7 節的 FK Restrict 修改）
2. 爬蟲 + 回補腳本，先抓 2026 年 1 月驗證，再回補至今
3. `clock` / `market` 模組 + 單元測試（歸屬日、狀態機邊界：14:59:59、15:00:00、週五 15:00 後、連假前）
4. 下單／取消／結算 service + 併行測試
5. FastAPI routers
6. React 前端
7. MongoDB 行為紀錄 + 分析
8. 合成資料、index benchmark、README、備份
