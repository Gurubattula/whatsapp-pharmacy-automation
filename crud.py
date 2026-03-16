from sqlalchemy.orm import Session
import models
from utils.fuzzy_logic import find_best_match
import datetime

# ─── User ─────────────────────────────────────────────────────────────────────
def get_or_create_user(db: Session, whatsapp_num: str) -> models.User:
    user = db.query(models.User).filter(models.User.whatsapp_num == whatsapp_num).first()
    if not user:
        user = models.User(whatsapp_num=whatsapp_num)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

# ─── Conversation State ────────────────────────────────────────────────────────
def get_state(db: Session, whatsapp_num: str) -> models.ConversationState:
    state = db.query(models.ConversationState).filter(
        models.ConversationState.whatsapp_num == whatsapp_num
    ).first()
    if not state:
        state = models.ConversationState(whatsapp_num=whatsapp_num, state="IDLE")
        db.add(state)
        db.commit()
        db.refresh(state)
    return state

def set_state(db: Session, whatsapp_num: str, state: str,
              temp_medicine_name=None, temp_medicine_id=None, temp_quantity=None):
    conv = get_state(db, whatsapp_num)
    conv.state = state
    conv.updated_at = datetime.datetime.utcnow()
    if temp_medicine_name is not None:
        conv.temp_medicine_name = temp_medicine_name
    if temp_medicine_id is not None:
        conv.temp_medicine_id = temp_medicine_id
    if temp_quantity is not None:
        conv.temp_quantity = temp_quantity
    db.commit()
    db.refresh(conv)
    return conv

def reset_state(db: Session, whatsapp_num: str):
    """Reset conversation to IDLE and clear all temp fields."""
    conv = get_state(db, whatsapp_num)
    conv.state = "IDLE"
    conv.temp_medicine_name = None
    conv.temp_medicine_id = None
    conv.temp_quantity = None
    conv.updated_at = datetime.datetime.utcnow()
    db.commit()

# ─── Medicine ─────────────────────────────────────────────────────────────────
def get_medicine_fuzzy(db: Session, user_input: str):
    """
    Fuzzy-match user_input against all medicine names in DB.
    Returns the Medicine ORM object if a good match is found, else None.
    """
    all_meds = db.query(models.Medicine).all()
    if not all_meds:
        return None
    db_names = [m.name for m in all_meds]
    best_name = find_best_match(user_input, db_names)
    if not best_name:
        return None
    return db.query(models.Medicine).filter(models.Medicine.name == best_name).first()

def get_medicine_by_id(db: Session, medicine_id: int):
    return db.query(models.Medicine).filter(models.Medicine.id == medicine_id).first()

# ─── Order ────────────────────────────────────────────────────────────────────
def create_order(db: Session, user_id: int, whatsapp_num: str,
                 medicine_id: int, quantity: int) -> models.Order:
    """Create an Order + OrderItem and deduct stock. Returns the Order."""
    med = get_medicine_by_id(db, medicine_id)
    total = round(med.price * quantity, 2)

    order = models.Order(
        user_id=user_id,
        whatsapp_num=whatsapp_num,
        total_amount=total,
        status="Pending"
    )
    db.add(order)
    db.flush()  # get order.id before commit

    item = models.OrderItem(
        order_id=order.id,
        medicine_id=medicine_id,
        quantity=quantity,
        unit_price=med.price
    )
    db.add(item)

    # Deduct stock
    med.stock_quantity = max(0, med.stock_quantity - quantity)

    # Add a track entry
    track = models.TrackDetail(order_id=order.id, status="Order Placed")
    db.add(track)

    db.commit()
    db.refresh(order)
    return order

def get_order(db: Session, order_id: int):
    return db.query(models.Order).filter(models.Order.id == order_id).first()
