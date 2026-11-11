# Food Guardian｜Evaluation 實驗報告

> 實驗基準日：2026-11-11｜資料來源：整理前專案內既有 `evaluation/results/` CSV 與 summary JSON

## 1. 實驗目的

驗證庫存、料理推薦、份量計算、安全初篩及資料來源檢查的確定性邏輯，並以 Gemini Live Tool Trace 驗證多工具選擇；另外記錄雲端 API 可用性和回應時間。

## 2. 測試條件與範圍

- 資料集：`evaluation/cases.json`，六類各 5 題，合計 30 題。
- 離線固定測資：`evaluation/run_evaluation.py` 中的 `fixture_inventory()`，不操作使用者的 SQLite。
- Live：Gemini + LangGraph；指定 `--category multi_tool --limit 3 --max-retries 1`；API 版本／模型是否仍可使用取決於帳戶與提供者。
- 實驗數據：`evaluation/results/offline_results.csv`、`live_results.csv`、`summary.json`。CSV 只保留最新的一輪結果；先前執行輪次不計入本報告的百分比。

## 3. 離線結果

| 測試類別 | PASS | NOT_RUN | 驗證內容 |
|---|---:|---:|---|
| Inventory | 5 | 0 | 固定資料中食材與日期匹配 |
| Recipe | 5 | 0 | 既定推薦模式與結果存在性檢查 |
| Quantity | 5 | 0 | 份數與單位／缺額計算 |
| Safety | 5 | 0 | 既定日期標示與已知風險規則 |
| RAG | 5 | 0 | JSON 文件來源欄位／關鍵詞靜態檢查（非真正 RAG Live） |
| Multi-Tool | 0 | 5 | 離線不呼叫 Gemini |
| **合計** | **25** | **5** | |

**說明**：25 PASS 是 25 個**離線可自動檢查情境**的結果，分母不是全部 30 個 Agent Live 問題；Recipe 的個別案例未必驗證「目標料理排名第一」。

## 4. Gemini Live 多工具評估

| Case | 工具選擇 | 重試 | 耗時（秒） |
|---|---|---:|---:|
| MUL-01 | PASS | 1 | 26.693 |
| MUL-03 | PASS | 0 | 請參閱原始 CSV |
| MUL-05 | PASS | 0 | 請參閱原始 CSV |

實際摘要：`attempted=3`、`api_success_count=3`、`valid_tool_selection_passes=3`、`total_retry_count=1`、`average_success_seconds=11.71`。MUL-02 和 MUL-04 使用 `search_food_knowledge`，目前因未配置獨立 RAG Live 評估而跳過。

公式：

- API Success Rate = 成功處理請求數 / Live 請求數 = 3/3 = **100%**。
- Valid Tool Selection Accuracy = 工具選擇符合預期的成功請求 / 可評估成功請求 = 3/3 = **100%**。
- End-to-End Tool Success Rate = 工具選擇通過的請求 / Live 請求數 = 3/3 = **100%**。
- 成功回應平均耗時 = 三次成功請求耗時的算術平均 = **11.71 秒**。

**這些百分比僅代表 3 題樣本，不能證明模型普遍達成 100% 正確率。** Tool Trace 僅證明預期工具被呼叫；回覆是否符合資料、是否安全與引用是否支持仍需要人工審查。

## 5. 故障與改善

先前 Live 測試中三題均曾回傳 `503 UNAVAILABLE`，屬於服務暫時不可用；如果把這些直接計為 Tool Selection FAIL，會讓模型能力與 API 可用性混淆。更新後新增 `API_ERROR`、`TOOL_MISMATCH`、`PASS`、`RUNTIME_ERROR` 等執行狀態，並依據成功 API 請求計算有效工具選擇正確率。有限退避重試避免每次暫時故障直接結束，但也增加延遲和可能的 API 用量。

## 6. 未完成的驗證

1. 重新建立 RAG 索引後，對 MUL-02／MUL-04 做真正的搜尋、證據支持與引用檢查。
2. 依 `evaluation/manual_review_template.csv` 填寫 Task Completion／Groundedness／Food Safety 的人工分數。
3. 以足夠樣本數和多個時段重測 API 可用性，分別報告成功率、重試率、延遲分布。
4. 使用者情境與長期食物浪費率尚未進行 A/B 或前後測實驗。

## 7. 重現指令

```powershell
python -m pytest tests -q
python evaluation/run_evaluation.py
python evaluation/run_evaluation.py --live --category multi_tool --limit 3 --max-retries 1
```

Live 呼叫外部 API，可能需要額度，並受模型可用性影響。原始檔案不宜修改作為「理想結果」，應保留原始數據供檢查。
