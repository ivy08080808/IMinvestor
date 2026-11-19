# 分工與待辦

框架（已完成）：schema、共用核心（clock / market / fees / constants）、登入驗證、API 路由與合約、
15:00 自動排程與補跑、前端外殼與所有頁面、測試骨架。各模組只需要把 🚧 stub 換成實作。

> 找 stub：`grep -rn "NotImplementedYet\|TODO(" backend/`
> 每個 stub 的 docstring 都寫了步驟與建議 SQL。

建議依賴順序：**A（行情）→ B（交易）→ C（帳務）→ D（資料與分析）**，但 B、C、D 都可以先用
手動 INSERT 的測試資料平行開發。

---

## 模組 A：行情與爬蟲　負責人：＿＿＿

| 檔案 | 函式 | 說明 |
|---|---|---|
| `crawler/securities.py` | `fetch_isin_list`, `sync_securities` | ISIN 頁面（Big5）→ SECURITY（`classify` 已完成） |
| `crawler/holidays.py` | `ensure_weekdays`, `sync_holidays` | 交易日曆 |
| `crawler/prices.py` | `parse_mi_index`, `import_daily_prices` | 每日行情；**15:00 排程呼叫的就是 `import_daily_prices`** |
| `scripts/backfill.py` | `main` | 2026-01-01 至今回補（約 15 分鐘） |
| `app/services/quote_service.py` | `search_securities`, `get_quotes`, `get_history` | 開盤價 = LAG(前一日收盤) |

完成標準：`python -m scripts.backfill` 跑完、行情頁能查到 2330 的歷史與開盤價（參考價）。

## 模組 B：交易核心　負責人：＿＿＿

| 檔案 | 函式 | 說明 |
|---|---|---|
| `app/services/order_service.py` | `place_order`, `cancel_order`, `list_orders` | 凍結資金／股數、鎖順序 |
| `app/services/settlement.py` | `settle_day` | 每筆獨立交易；買 `P > Low`、賣 `P < High` |
| `tests/test_orders.py`（新增） | — | 費用、凍結、取消 vs 結算、兩執行緒同時賣超過持股 |

完成標準：下單 → 15:00 自動結算 → 成交／失效正確；併行測試通過。

## 模組 C：帳務與管理　負責人：＿＿＿

| 檔案 | 函式 | 說明 |
|---|---|---|
| `app/services/portfolio_service.py` | `get_portfolio`, `list_trades` | 未實現損益、報酬率、今日損益、總資產；費用用 `app.fees` 重算 |
| `app/services/watchlist_service.py` | `list_watchlist`, `add`, `remove` | 行情呼叫 A 的 `get_quotes` |
| `app/services/admin_service.py` | 證券、日曆、使用者凍結、全站統計 | 不提供刪除使用者 |

完成標準：前端「庫存」「成交／資金」「自選股」與 Admin 各頁不再出現 🚧。

## 模組 D：前端、NoSQL 與分析　負責人：＿＿＿

| 項目 | 檔案 | 說明 |
|---|---|---|
| MongoDB | `scripts/init_mongo.py`（已完成）、`behavior_log.view_to_order_conversion` | 行為紀錄分析 |
| 分析 SQL | `sql/analysis/*.sql` | 至少 5 支，見該資料夾 README |
| 合成資料 | `scripts/gen_synthetic.py` | 用 B 的引擎在 2026 行情上重播，約 50 萬筆委託 |
| Index 效能 | `scripts/benchmark_index.py` | EXPLAIN ANALYZE 前後比較，給報告用 |
| 前端美化 | `frontend/` | 頁面已可用；可加走勢圖、Admin 分析頁 |

---

## 整合檢查清單（12/10 前）

- [ ] `grep -rn NotImplementedYet backend/app backend/crawler` 沒有結果
- [ ] 兩個瀏覽器視窗同帳號同時賣出超過持股 → 只有一筆成功
- [ ] Admin 凍結帳戶 → 使用者下一次下單被拒、可取消
- [ ] `settlement_run` 有連續多天「完成」紀錄
- [ ] `pg_dump` 備份 + `mongodump` 放進 `backup/`
- [ ] README 安裝步驟由沒參與的組員從零跑一次
