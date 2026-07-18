# tw-invest-copilot

台股投資輔助 dashboard（個人 side project）。追蹤指數/個股/ETF 走勢、均線、前高支撐買點、台指夜盤情緒，並用 AI agent 生成每日重點摘要。

## 開發狀態

v1（MVP）進行中，詳見開發計畫 `docs/plan.md`（如有）。目前只做痛點2的核心功能，痛點1/3/4 留待後續 session。

## 本機執行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # 填入 ANTHROPIC_API_KEY
streamlit run app.py
```
