from pydantic import BaseModel
from typing import Optional, List
import datetime

# ─── Medicine ────────────────────────────────────────────────────────────────
class MedicineBase(BaseModel):
    name: str
    price: float
    stock_quantity: int
    is_prescription_required: bool = False

class MedicineOut(MedicineBase):
    id: int
    class Config:
        from_attributes = True

# ─── User ─────────────────────────────────────────────────────────────────────
class UserBase(BaseModel):
    whatsapp_num: str
    name: Optional[str] = None

class UserOut(UserBase):
    id: int
    created_at: datetime.datetime
    class Config:
        from_attributes = True

# ─── OrderItem ────────────────────────────────────────────────────────────────
class OrderItemBase(BaseModel):
    medicine_id: int
    quantity: int
    unit_price: float

class OrderItemOut(OrderItemBase):
    id: int
    class Config:
        from_attributes = True

# ─── Order ────────────────────────────────────────────────────────────────────
class OrderBase(BaseModel):
    whatsapp_num: str
    total_amount: float
    status: str = "Pending"

class OrderOut(OrderBase):
    id: int
    created_at: datetime.datetime
    items: List[OrderItemOut] = []
    class Config:
        from_attributes = True

# ─── TrackDetail ─────────────────────────────────────────────────────────────
class TrackDetailOut(BaseModel):
    id: int
    order_id: int
    status: str
    updated_at: datetime.datetime
    notes: Optional[str] = None
    class Config:
        from_attributes = True
