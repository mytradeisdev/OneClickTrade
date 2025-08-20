from typing import List, Optional
from pydantic import BaseModel

class OrderLeg(BaseModel):
    side: str  # BUY or SELL
    symbol: str
    qty: int

class AlertBody(BaseModel):
    token: str
    title: Optional[str] = None
    body: Optional[str] = None
    rec_id: Optional[str] = None
    orders: List[OrderLeg] = []

class TestBody(BaseModel):
    token: str
