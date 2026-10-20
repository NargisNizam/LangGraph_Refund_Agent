from typing import Literal, Optional
from pydantic import BaseModel, Field


class CustomerRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    thread_id: str = Field(min_length=1, max_length=200)
    order_id: Optional[str] = None


class ReviewRequest(BaseModel):
    approved: bool


class Classification(BaseModel):
    intent: Literal["refund", "tracking", "cancellation", "complaint", "general"]
    order_id: Optional[str] = None
