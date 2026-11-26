# 分析 SQL（報告 §4.2.3 用）

負責：**模組 D**。每支查詢一個檔案，檔頭註解寫：目的、使用者（Admin / 資料分析師）、預期輸出欄位。
報告要求至少 5 個業務功能 SQL + 5 個分析 SQL（至少 1 個用到 NoSQL）；業務功能 SQL 直接引用各 service 的實作。

| 檔案 | 分析內容 | 狀態 |
|---|---|---|
| `a1_security_fill_rate.sql` | 個股委託數、成交數、委託成交率（Admin 統計頁共用） | TODO |
| `a2_user_return_ranking.sql` | 使用者總資產報酬率排行 | TODO |
| `a3_price_deviation_vs_fill.sql` | 委託價偏離參考價（分桶）vs. 成交機率 | TODO |
| `a4_category_concentration.sql` | 各證券類別持股市值集中度 | TODO |
| `a5_order_time_distribution.sql` | 委託送出時段分布（盤前／盤中／收盤後） | TODO |
| （NoSQL）`behavior_log.view_to_order_conversion` | 瀏覽→下單轉換率 | TODO |

參考價（昨收）一律用 `LAG(close_price) OVER (PARTITION BY security_id ORDER BY trade_date)` 推算；開盤價直接讀 `daily_price.open_price`。
