# TradeBotX — How to Run

This guide covers how to start the project locally (frontend dashboard + backend API server).

---

## Prerequisites

Make sure you have these installed:

- **Python 3.10+**
- **Node.js 18+** (for the React frontend)

---

## Step 1 — Clone & Set Up Python Environment

```powershell
# 1. Clone the repo (skip if already done)
git clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents

# 2. Create a virtual environment
python -m venv venv

# 3. Activate it
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 4. Install the package and all dependencies
pip install -e .
```

---

## Step 2 — Configure API Keys

Copy the example env file and fill in your keys:

```powershell
copy .env.example .env
```

Then open `.env` and add your keys. At minimum you need one LLM provider key:

```env
OPENAI_API_KEY=sk-...          # OpenAI (GPT models) — default provider
GOOGLE_API_KEY=...             # Google (Gemini) — optional
ANTHROPIC_API_KEY=...          # Anthropic (Claude) — optional
XAI_API_KEY=...                # xAI (Grok) — optional
OPENROUTER_API_KEY=...         # OpenRouter — optional
ALPHA_VANTAGE_API_KEY=...      # Alpha Vantage (paid data) — optional, yfinance is the free default
```

> **Note:** Data fetching (stock prices, fundamentals, news) works out of the box via **yfinance** — no extra key needed.

---

## Step 3 — Start the Backend API Server

This is the FastAPI server the React dashboard talks to. Run it from the project root with your venv active:

```powershell
# Make sure venv is active — you should see (venv) in your terminal
venv\Scripts\activate

python api_server.py
```

The server starts at **http://localhost:8000**. Keep this terminal open.

> ⚠️ Do **not** run `python main.py` for the dashboard — that is just a standalone demo script (see below).

---

## Step 4 — Start the Frontend Dashboard

Open a **second terminal** and run:

```powershell
cd frontend
npm install          # only needed the first time
npm run dev
```

The dashboard opens at **http://localhost:5173**. 

---

## Step 5 — Use the Dashboard

1. Open **http://localhost:5173** in your browser.
2. Pick an NSE index (e.g. *NIFTY 50*) and click **Scan Market**.
3. The screener fetches live stock data and flags interesting stocks (RSI extremes, volume spikes, price action).
4. Click **Analyse** next to any flagged stock to launch the full **13-agent AI pipeline**.
5. Watch the pipeline progress live and get a final **BUY / OVERWEIGHT / HOLD / UNDERWEIGHT / SELL** recommendation.

---

## What is `main.py`?

`main.py` is a **standalone Python demo script** — it runs the entire 13-agent LLM pipeline directly from the command line **without** the dashboard:

```powershell
python main.py
```

- It is useful for **testing** that your API keys work and the pipeline runs end-to-end.
- It **will** make real LLM API calls (costs money, takes ~2–5 minutes per stock).
- It is **not** the right way to use the dashboard — use `api_server.py` + `npm run dev` for that.

---

## Quick Reference

| Goal | Command |
|---|---|
| Activate venv | `venv\Scripts\activate` |
| Install / update deps | `pip install -e .` |
| Start backend API | `python api_server.py` |
| Start frontend | `cd frontend && npm run dev` |
| Open dashboard | http://localhost:5173 |
| Test pipeline directly (no UI) | `python main.py` |

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `ModuleNotFoundError` | Make sure venv is active and `pip install -e .` was run |
| `OPENAI_API_KEY not found` | Check your `.env` file — key must be set |
| `Failed to connect to backend` | Make sure `python api_server.py` is running |
| `KeyboardInterrupt` in `main.py` | You pressed Ctrl+C — it was working fine, pipeline was mid-run |
| Frontend shows blank page | Check that `npm install` was run inside `frontend/` |
