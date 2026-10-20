import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from database import seed_db
from graph import build_graph
from schemas import CustomerRequest, ReviewRequest

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("refund-agent")
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_db()
    app.state.graph = build_graph(InMemorySaver())
    if not os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY") == "replace_with_your_key":
        logger.warning("GROQ_API_KEY not configured. Rule-based classification and template replies will be used.")
    yield


app = FastAPI(
    title="LangGraph Refund Agent",
    version="1.0.0",
    lifespan=lifespan
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


def format_result(graph, thread_id, result):
    snapshot = graph.get_state({"configurable": {"thread_id": thread_id}})
    interrupts = [item.value for item in result.get("__interrupt__", ())]
    values = snapshot.values or {}
    return {
        "thread_id": thread_id,
        "status": "awaiting_approval" if interrupts else "completed",
        "interrupts": interrupts,
        "decision": values.get("decision"),
        "response": values.get("response") if not interrupts else None,
    }


@app.post("/support")
def support(body: CustomerRequest):
    graph = app.state.graph
    config = {"configurable": {"thread_id": body.thread_id}}
    existing = graph.get_state(config)
    if existing.values:
        raise HTTPException(status_code=409, detail="Thread already exists. Use a new Request Reference.")
    try:
        result = graph.invoke(
            {
                "message": body.message,
                "request_id": str(uuid.uuid4()),
                "supplied_order_id": body.order_id,
            },
            config=config,
        )
        return format_result(graph, body.thread_id, result)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("POST /support failed for thread_id=%s", body.thread_id)
        raise HTTPException(
            status_code=500,
            detail=f"Request processing failed ({type(exc).__name__}). Check the server terminal for the full traceback.",
        ) from exc


@app.post("/review/{thread_id}")
def review(thread_id: str, body: ReviewRequest):
    graph = app.state.graph
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)
    if not snapshot.next or "human_review" not in snapshot.next:
        raise HTTPException(status_code=409, detail="No pending human review for this thread.")
    try:
        result = graph.invoke(Command(resume={"approved": body.approved}), config=config)
        return format_result(graph, thread_id, result)
    except Exception as exc:
        logger.exception("POST /review failed for thread_id=%s", thread_id)
        raise HTTPException(
            status_code=500,
            detail=f"Review processing failed ({type(exc).__name__}). Check the server terminal for the full traceback.",
        ) from exc
