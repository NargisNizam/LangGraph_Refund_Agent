# RefundIQ — LangGraph Customer Support & Refund Agent

A learning project built with **Python, FastAPI, LangGraph, Groq, HTML, CSS, and JavaScript**. It classifies customer messages, looks up demo orders, checks a refund policy, pauses for human approval when needed, and records approved refunds in local CSV files.

> **Demo only:** This project does not connect to a payment processor and never transfers real money. Do not deploy the unauthenticated review endpoint publicly.

## Features

- Responsive customer support web UI and FastAPI API docs.
- Intent classification for refund, tracking, cancellation, complaint, and general questions.
- Order lookup against a generated CSV dataset.
- Seven-day refund window; automatic processing up to $100; human review above $100.
- LangGraph interrupt/resume workflow for human approval.
- CSV demo refund ledger with duplicate-refund checks.
- Groq-powered classification/replies when a valid key and model are available; safe rule-based/template fallback if the model call fails.
- Health endpoint and readable API errors.

## Project structure

```text
langgraph-refund-agent/
├── main.py
├── graph.py
├── agents.py
├── tools.py
├── database.py
├── schemas.py
├── requirements.txt
├── .env.example
├── .gitignore
└── static/
    ├── index.html
    ├── style.css
    └── script.js
```

## Windows setup (PowerShell)

Run these commands in the project folder:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and set your own Groq API key. Do not commit `.env` to GitHub. The app can still run with safe rule-based/template fallbacks if the key is missing or the model request fails.

## Run

```powershell
python -m py_compile main.py schemas.py agents.py graph.py tools.py database.py
python -m uvicorn main:app --reload
```

Open:
- Web UI: http://127.0.0.1:8000/
- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

If port 8000 is already in use, run `python -m uvicorn main:app --reload --port 8001` and use port 8001 in the browser.

## Test scenarios

Use a unique `thread_id` for each new request. The app generates IDs in the UI.

| Order | Demo behavior |
|---|---|
| `ORD-1001` | $75, recent delivery; eligible for automatic demo refund |
| `ORD-1002` | $120; human approval required |
| `ORD-1003` | $350; human approval required |
| `ORD-1004` | Older delivery; refund window expired |
| `ORD-1005` | Already refunded |

Order seed dates are generated when `data/orders.csv` is first created. Data persists between restarts. To reset the demo data, stop the server and remove `data/orders.csv` and `data/refunds.csv`, then restart.

## API example

`POST /support`:

```json
{
  "thread_id": "demo-unique-1",
  "message": "I want a refund for ORD-1001",
  "order_id": "ORD-1001"
}
```

For a request requiring human review, the API returns `status: "awaiting_approval"` and interrupt details. Continue with `POST /review/{thread_id}`:

```json
{"approved": true}
```

## Important limitations

- `InMemorySaver` means pending approvals are lost when the server restarts.
- CSV storage is for local learning only; it is not a production transactional database.
- Review endpoint has no authentication. Add authentication, authorization, audit logging, and a proper database before deployment.
- Groq model names and access can change. Set `GROQ_MODEL` in `.env` to a model currently available to your Groq account.
