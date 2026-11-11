# D 組期末簡報建議架構（7 頁）

> 簡報文字可依組別時間再精簡。成果數據以 `evaluation/results/summary.json` 為準。

## 1. 專題問題與 D 組目標
- 食材庫存可見，卻仍可能不知道如何利用或處理快到期食材。
- D 組負責 Domain AI Agent：理解自然語言、呼叫工具、結合資料與食品知識、解釋推薦結果。
- 不宣稱已透過使用者實驗證明食物浪費下降。

## 2. Agent 架構
- Streamlit → GeminiFoodAgent / LangGraph → ToolNode → Service / SQLite / JSON / ChromaDB。
- 七個唯讀工具；LLM 負責理解意圖與組織答案，數量和日期規則由 Python 計算。
- 使用 DESIGN.md 第 3 章 Mermaid 圖。

## 3. 推薦演算法
- `recommend_recipes_for_servings_tool` 依份數算出需求、庫存、缺額與未知單位。
- `balanced`、`ready_now`、`expiry_first` 三種排序，展示高麗菜炒蛋與番茄炒蛋的差異。
- 明確標示配方是示範數據，跨多道菜不共享扣除。

## 4. Food Safety 與領域知識
- Safety Validator 讀取真正 SQLite 庫存：`eligible`／`review`／`blocked`。
- Use By 過期不自動推薦；Best Before 與未知日期需人工確認。
- RAG 可附來源網址，但來源存在不等於內容正確或食用安全保證。

## 5. 實際 Demo 與 Tool Trace
- 問「兩人份、不要額外買」展示 `ready_now`；問「先消耗快到期」展示 `expiry_first`。
- 問「雞胸肉可否推薦」展示 `validate_inventory_safety_tool` 查詢。
- Tool Trace 截圖需要遮蔽 API Key、私密路徑與個人資料。

## 6. Evaluation 成果
- 30 題：25 個離線情境 PASS、5 個 Multi-Tool 離線未執行。
- 最新非 RAG Live：3/3 API 成功、3/3 Tool Selection 通過，平均 11.71 秒、重試 1 次。
- MUL-02／MUL-04 因 RAG Live 評估尚未配置而跳過。三題樣本過少，勿稱整體 100% 正確。

## 7. 限制與後續研究
- RAG 檢索準確率／回答 groundedness 尚未正式人工評分。
- 食品溫度與開封後保存缺少可靠感測資料；未知單位不推測。
- API 503 處理、資料規則可解釋性是目前成果；未來增設跨料理共享庫存與真實浪費減量成效追蹤。
