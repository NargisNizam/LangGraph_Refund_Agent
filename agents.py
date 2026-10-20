import os
import re
from langchain_groq import ChatGroq
from schemas import Classification


def llm():
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or api_key == "replace_with_your_key":
        raise RuntimeError("GROQ_API_KEY is missing. Add your Groq API key to .env.")
    return ChatGroq(
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        temperature=0,
        api_key=api_key,
    )


def _fallback_intent(message: str) -> str:
    text = message.lower()
    if any(word in text for word in ("refund", "money back", "return my money", "reimburse")):
        return "refund"
    if any(word in text for word in ("track", "where is my order", "delivery status", "shipping status")):
        return "tracking"
    if any(word in text for word in ("cancel", "cancellation")):
        return "cancellation"
    if any(word in text for word in ("complaint", "damaged", "broken", "unhappy", "bad service")):
        return "complaint"
    return "general"


def classify(message: str, supplied_order_id: str | None = None) -> dict:
    """Use Groq classification when available; fall back to simple rules if it fails."""
    match = re.search(r"\bORD-\d+\b", message, re.IGNORECASE)
    order_id = (supplied_order_id or (match.group(0) if match else None))
    if order_id:
        order_id = order_id.strip().upper()
    try:
        result = llm().with_structured_output(Classification).invoke([
            ("system", "Classify the customer support request. Extract an order ID like ORD-1001 if present. Never invent an ID."),
            ("human", message),
        ])
        return {
            "intent": result.intent,
            "order_id": order_id or result.order_id,
        }
    except Exception:
        # The API remains testable if the Groq model is temporarily unavailable.
        # The README explains that the fallback is rule-based, not an LLM response.
        return {"intent": _fallback_intent(message), "order_id": order_id}


def compose_reply(message: str, outcome: str, detail: str) -> str:
    """Generate a reply with Groq; use a safe, transparent template if the LLM fails."""
    try:
        response = llm().invoke([
            ("system", "Write a concise, courteous customer service reply. The outcome and detail are authoritative. Never say a payment was sent or money returned when only a demo ledger was updated. Never override the decision."),
            ("human", f"Customer: {message}\nOutcome: {outcome}\nDetail: {detail}"),
        ])
        content = response.content
        if isinstance(content, str) and content.strip():
            return content.strip()
    except Exception:
        pass

    if outcome == "recorded":
        return (
            f"Thank you for contacting support. Your refund request for {detail} "
            "has been recorded in the local demo ledger. No real payment was sent."
        )
    if outcome in ("rejected", "failed"):
        return f"Thank you for contacting support. We could not process this refund request. {detail} No money was transferred."
    if outcome == "review":
        return f"Thank you for contacting support. {detail} Please wait for a human reviewer to make a decision."
    return f"Thank you for contacting support. {detail}"
