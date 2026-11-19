# IMinvestor REST API 規格

> 這份文件 = 前後端的合約。欄位定義以 `backend/app/schemas.py` 為準，前端呼叫一律經過 `frontend/js/api.js`。
> 改任何欄位：同一個 PR 內同時改 `schemas.py`、`api.js`、本文件，並通知前端負責人。
> 後端啟動後，互動式文件在 <http://localhost:8000/docs>。

## 共通規則

| 項目 | 規則 |
|---|---|
| Base URL | `http://localhost:8000` |
| 認證 | `Authorization: Bearer <access_token>`（由 login / register 取得） |
| 金額、價格 | JSON **字串**（Decimal），例如 `"1000000.00"`；前端只做顯示格式化，不做計算 |
| 時間 | 台北時間，無時區：`"2026-11-19T15:00:00"`；日期：`"2026-11-19"` |
| 錯誤 | `{"error": {"code": "INSUFFICIENT_CASH", "message": "可用餘額不足"}}` |
| 尚未實作 | HTTP **501**，`code = "NOT_IMPLEMENTED"`，message 註明負責模組；前端會顯示 🚧 |
| 列表分頁 | `limit`（預設 50）、`offset`（預設 0） |

### HTTP 狀態碼

| 碼 | 意義 |
|---|---|
| 400 | 業務規則不符（價格超出區間、餘額不足…） |
| 401 | 未登入或 token 失效 |
| 403 | 角色不符（User 打 Admin API，反之亦然） |
| 404 | 找不到資源 |
| 409 | 狀態衝突（`SETTLING` 結算中、重複資料、委託已非待成交） |
| 422 | 請求格式錯誤（FastAPI 驗證） |
| 501 | 尚未實作 |
| 503 | `CALENDAR_MISSING` 交易日曆未登錄 |

### 錯誤碼一覽（新增時請補在這裡）

`UNAUTHENTICATED` `FORBIDDEN` `BAD_CREDENTIALS` `USER_EXISTS` `NOT_FOUND` `NOT_IMPLEMENTED`
`SETTLING` `CALENDAR_MISSING` `ACCOUNT_FROZEN` `SECURITY_DISABLED` `NO_PRICE` `PRICE_OUT_OF_RANGE`
`INSUFFICIENT_CASH` `INSUFFICIENT_SHARES` `NOT_CANCELLABLE` `DUPLICATE` `HAS_PENDING_ORDERS`

---

## 端點總表

圖例：✅ 框架已實作　🚧 stub（回 501，等負責模組完成）

### Auth（公開／任何登入者）

| 方法 | 路徑 | 說明 | Request | Response | 狀態 |
|---|---|---|---|---|---|
| POST | `/api/auth/register` | 註冊 User 並配發 1,000,000 元 | `RegisterIn` | `TokenOut` 201 | ✅ |
| POST | `/api/auth/login` | 登入（寫一筆 login 行為紀錄） | `LoginIn` | `TokenOut` | ✅ |
| GET | `/api/auth/me` | 目前使用者 | — | `UserOut` | ✅ |
| POST | `/api/auth/password` | 修改密碼 | `ChangePasswordIn` | `OkOut` | ✅ |

### 市場時鐘（公開）

| 方法 | 路徑 | 說明 | Response | 狀態 |
|---|---|---|---|---|
| GET | `/api/market/status` | 台北時間、市場狀態、可否下單、新委託歸屬日 | `MarketStatusOut` | ✅ |

`phase` ∈ `HOLIDAY 休市 / PRE_OPEN 盤前 / OPEN 盤中 / CLOSED 收盤 / SETTLING 結算中 / SETTLED 盤後`
（規則見 `backend/app/market.py` 檔頭表格）。前端狀態列每 5 秒輪詢。

### 證券與行情（登入者）— 模組 A

| 方法 | 路徑 | 說明 | Response | 狀態 |
|---|---|---|---|---|
| GET | `/api/securities?q=&limit=` | 搜尋啟用中的證券（寫 search 行為紀錄） | `SecurityOut[]` | 🚧 |
| GET | `/api/securities/quotes?ids=2330,0050` | 多檔最新行情 | `QuoteOut[]` | 🚧 |
| GET | `/api/securities/{id}/quote` | 單檔最新行情（寫 view_security 行為紀錄） | `QuoteOut` | 🚧 |
| GET | `/api/securities/{id}/history?from=&to=` | 歷史行情，新到舊，預設 90 天 | `PriceBarOut[]` | 🚧 |
| GET | `/api/securities/{id}/order-rule` | 歸屬日、參考價、±10% 區間 | `OrderRuleOut` | ✅ |

> `open_price`（開盤價）＝**前一交易日收盤價**，以 `LAG()` 推算，資料庫不存。

### 自選股（User）— 模組 C

| 方法 | 路徑 | Request | Response | 狀態 |
|---|---|---|---|---|
| GET | `/api/watchlist` | — | `QuoteOut[]` | 🚧 |
| POST | `/api/watchlist` | `{"security_id": "2330"}` | `OkOut` 201 | 🚧 |
| DELETE | `/api/watchlist/{id}` | — | `OkOut` | 🚧 |

### 交易（User）— 模組 B（委託）、模組 C（帳務）

| 方法 | 路徑 | 說明 | Request | Response | 狀態 |
|---|---|---|---|---|---|
| POST | `/api/orders` | 限價下單 | `OrderCreateIn` | `OrderOut` 201 | 🚧 B |
| POST | `/api/orders/{order_id}/cancel` | 取消待成交委託 | — | `OrderOut` | 🚧 B |
| GET | `/api/orders?status=` | 我的委託 | — | `OrderOut[]` | 🚧 B |
| GET | `/api/trades` | 我的成交（含費用、收付金額） | — | `TradeOut[]` | 🚧 C |
| GET | `/api/account` | 可用／凍結現金、帳戶狀態 | — | `AccountOut` | ✅ |
| GET | `/api/portfolio` | 庫存、即時損益、總資產 | — | `PortfolioOut` | 🚧 C |

### Admin — 模組 C

| 方法 | 路徑 | 說明 | 狀態 |
|---|---|---|---|
| GET | `/api/admin/securities?q=` | 全部證券（含停用） | 🚧 |
| POST | `/api/admin/securities` | 新增證券 `SecurityUpsertIn` | 🚧 |
| PATCH | `/api/admin/securities/{id}` | 修改名稱／類別／狀態 `SecurityUpdateIn` | 🚧 |
| GET | `/api/admin/calendar?from=&to=` | 交易日曆 | 🚧 |
| PUT | `/api/admin/calendar` | 登錄休市日 `CalendarDayIn` | 🚧 |
| GET | `/api/admin/users?q=` | 使用者列表 `UserSummaryOut[]` | 🚧 |
| PUT | `/api/admin/users/{id}/status` | 凍結／解凍 `{"status": "凍結"}` | 🚧 |
| GET | `/api/admin/users/{id}/portfolio` | 任一使用者庫存（共用 C 的 service） | 🚧 |
| GET | `/api/admin/users/{id}/orders` | 任一使用者委託（共用 B 的 service） | 🚧 |
| GET | `/api/admin/users/{id}/trades` | 任一使用者成交（共用 C 的 service） | 🚧 |
| GET | `/api/admin/stats/securities?from=&to=` | 個股委託數、成交數、成交率 | 🚧 |
| GET | `/api/admin/settlement-runs` | 每日 15:00 自動結算紀錄（唯讀） | ✅ |

> 沒有「刪除使用者」與「手動匯入／結算」端點，這是刻意的設計（計畫書 v2、v3）。

---

## 主要資料結構（節錄，完整見 `schemas.py`）

```jsonc
// OrderCreateIn
{ "security_id": "2330", "side": "買", "price": "1050.00", "quantity": 100 }

// OrderOut
{ "order_id": 1, "security_id": "2330", "security_name": "台積電", "side": "買",
  "price": "1050.00", "quantity": 100, "submit_time": "2026-11-19T10:15:00",
  "belong_date": "2026-11-19", "status": "待成交" }

// QuoteOut  (open_price = previous close)
{ "security_id": "2330", "security_name": "台積電", "category_name": "普通股",
  "trade_date": "2026-11-18", "open_price": "1040.00", "high_price": "1060.00",
  "low_price": "1035.00", "close_price": "1055.00", "volume": 25000000,
  "change": "15.00", "change_pct": "1.44" }

// MarketStatusOut
{ "now": "2026-11-19T14:20:05", "today": "2026-11-19", "is_trading_day": true,
  "phase": "CLOSED", "phase_label": "收盤", "can_place_order": true,
  "order_belong_date": "2026-11-19", "latest_price_date": "2026-11-18", "message": "" }
```
