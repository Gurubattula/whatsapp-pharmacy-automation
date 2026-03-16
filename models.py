from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Medicine(Base):
    __tablename__ = "medicines"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    price = Column(Float)
    stock_quantity = Column(Integer)
    is_prescription_required = Column(Boolean, default=False)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    whatsapp_num = Column(String(50), unique=True, index=True)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    orders = relationship("Order", back_populates="user")

class ConversationState(Base):
    __tablename__ = "conversation_states"
    id = Column(Integer, primary_key=True, index=True)
    whatsapp_num = Column(String(50), unique=True, index=True)
    # States: IDLE, MENU_SHOWN, AWAITING_MEDICINE_NAME, AWAITING_QUANTITY, AWAITING_CONFIRM, AWAITING_ORDER_ID
    state = Column(String(50), default="IDLE")
    temp_medicine_name = Column(String(255), nullable=True)   # matched medicine name
    temp_medicine_id = Column(Integer, nullable=True)         # matched medicine DB id
    temp_quantity = Column(Integer, nullable=True)            # chosen quantity
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    whatsapp_num = Column(String(50))
    total_amount = Column(Float)
    status = Column(String(50), default="Pending")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    medicine_id = Column(Integer, ForeignKey("medicines.id"))
    quantity = Column(Integer)
    unit_price = Column(Float)
    order = relationship("Order", back_populates="items")
    medicine = relationship("Medicine")

class TrackDetail(Base):
    __tablename__ = "track_details"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    status = Column(String(100), default="Order Placed")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    notes = Column(Text, nullable=True)