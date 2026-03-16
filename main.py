from fastapi import FastAPI, Request, Depends
from sqlalchemy.orm import Session
from database import get_db, engine, Base
import models
import crud
import re
import datetime
import logging
from utils.gemini_ai import extract_medicine_details
from utils.whatsapp import send_whatsapp_msg

logging.basicConfig(filename='main_debug.log', level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# Create tables in MySQL on startup
@app.on_event("startup")
def startup_event():
    models.Base.metadata.create_all(bind=engine)

@app.post("/webhook")
async def handle_whatsapp(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
    except Exception as e:
        return {"error": "Invalid JSON", "details": str(e)}

    try:
        if "messages" in data:
            for msg in data["messages"]:
                if msg.get("from_me"): continue # Don't reply to self
                
                chat_id = msg.get("chat_id")
                if not chat_id:
                    logger.warning(f"No chat_id in message: {msg}")
                    continue
                
                user_text = msg.get("text", {}).get("body", "").strip().lower()
                whatsapp_num = chat_id.split("@")[0] # e.g., "919876543210"
                logger.info(f"Received message from {whatsapp_num} ({chat_id}): {user_text}")
                
                # --- Business Logic: Conversation Flow ---
                
                # 1. Get or Create User
                user = crud.get_or_create_user(db, whatsapp_num)
                
                # 2. Get State
                conv = crud.get_state(db, whatsapp_num)
                
                # Global Cancel/Reset Command
                if user_text in ["cancel", "reset", "menu"]:
                    crud.reset_state(db, whatsapp_num)
                    send_whatsapp_msg(chat_id, "Conversation reset. Say 'hii medbuddy' to start over.")
                    continue

                # State Machine Dispatch
                if conv.state == "IDLE":
                    greetings = ["hi", "hello", "hii", "hey", "medbuddy", "start", "menu"]
                    if any(word in user_text for word in greetings):
                        crud.set_state(db, whatsapp_num, "MENU_SHOWN")
                        msg = "👋 *Welcome to MedBuddy!*🤖🏥\n\nPlease choose an option by replying with a number:\n1️⃣. Order Medicine\n2️⃣. Track Your Order"
                        send_whatsapp_msg(chat_id, msg)
                    else:
                        # Optional: Respond to direct numbers if they skip the greeting
                        if user_text == "1":
                            crud.set_state(db, whatsapp_num, "AWAITING_MEDICINE_NAME")
                            send_whatsapp_msg(chat_id, "Great! Please type the *name of the medicine* you want to order.")
                        elif user_text == "2":
                            crud.set_state(db, whatsapp_num, "AWAITING_ORDER_ID")
                            send_whatsapp_msg(chat_id, "Please enter your *Order ID* to track your order.")
                        else:
                            send_whatsapp_msg(chat_id, "Please say 'hii medbuddy' to see the menu.")
                
                elif conv.state == "MENU_SHOWN":
                    if "1" in user_text or "order" in user_text:
                        crud.set_state(db, whatsapp_num, "AWAITING_MEDICINE_NAME")
                        send_whatsapp_msg(chat_id, "Great! Please type the *name of the medicine* you want to order.")
                    elif "2" in user_text or "track" in user_text:
                        crud.set_state(db, whatsapp_num, "AWAITING_ORDER_ID")
                        send_whatsapp_msg(chat_id, "Please enter your *Order ID* to track your order.")
                    else:
                        send_whatsapp_msg(chat_id, "Invalid option. Please reply with *1* (Order) or *2* (Track).")

                elif conv.state == "AWAITING_MEDICINE_NAME":
                    # Use Gemini and fuzzy match
                    requested_items = extract_medicine_details(user_text)
                    
                    extracted_qty = None
                    if not requested_items:
                        # If Gemini couldn't extract anything, try raw user input as fallback
                        match = crud.get_medicine_fuzzy(db, user_text)
                    else:
                        # We only process the first item for now to keep the flow simple
                        first_item = requested_items[0]
                        first_item_name = first_item['name']
                        match = crud.get_medicine_fuzzy(db, first_item_name)
                        
                        # Also try to extract quantity if provided (e.g., "2 Dolo")
                        raw_qty = first_item.get('quantity', '')
                        qty_match = re.search(r'\d+', str(raw_qty))
                        if qty_match:
                            extracted_qty = int(qty_match.group())
                        
                    if match:
                        if match.stock_quantity > 0:
                            if extracted_qty and extracted_qty > 0:
                                # Skip AWAITING_QUANTITY if we already have it!
                                total = round(match.price * extracted_qty, 2)
                                crud.set_state(db, whatsapp_num, "AWAITING_CONFIRM", 
                                             temp_medicine_name=match.name, 
                                             temp_medicine_id=match.id,
                                             temp_quantity=extracted_qty)
                                
                                bill_msg = f"✅ *{match.name}* is Available.\n\n"
                                bill_msg += f"🧾 *Order Summary*\n"
                                bill_msg += f"Medicine: {match.name}\nQuantity: {extracted_qty}\nPrice: ₹{match.price}\n"
                                bill_msg += f"*Total: ₹{total}*\n\n"
                                bill_msg += "Reply *CONFIRM* to place your order."
                                send_whatsapp_msg(chat_id, bill_msg)
                            else:
                                crud.set_state(db, whatsapp_num, "AWAITING_QUANTITY", 
                                             temp_medicine_name=match.name, 
                                             temp_medicine_id=match.id)
                                send_whatsapp_msg(chat_id, f"✅ *{match.name}* is Available at ₹{match.price} per unit.\n\n*How many* units do you need?")
                        else:
                            crud.reset_state(db, whatsapp_num)
                            send_whatsapp_msg(chat_id, f"❌ Sorry, *{match.name}* is currently Out of Stock.\nType 'menu' to start again.")
                    else:
                        crud.reset_state(db, whatsapp_num)
                        send_whatsapp_msg(chat_id, f"❓ Sorry, we couldn't find that medicine in our pharmacy.\nType 'menu' to start again.")

                elif conv.state == "AWAITING_QUANTITY":
                    numbers = re.findall(r'\d+', user_text)
                    if numbers:
                        qty = int(numbers[0])
                        if qty <= 0:
                            send_whatsapp_msg(chat_id, "Please enter a valid quantity greater than 0.")
                            continue
                            
                        # Calculate bill
                        med = crud.get_medicine_by_id(db, conv.temp_medicine_id)
                        total = round(med.price * qty, 2)
                        
                        crud.set_state(db, whatsapp_num, "AWAITING_CONFIRM", temp_quantity=qty)
                        
                        bill_msg = f"🧾 *Order Summary*\n\n"
                        bill_msg += f"Medicine: {med.name}\nQuantity: {qty}\nPrice unit: ₹{med.price}\n\n"
                        bill_msg += f"*Total Amount: ₹{total}*\n\n"
                        bill_msg += "Reply *CONFIRM* to place your order or *CANCEL* to stop."
                        send_whatsapp_msg(chat_id, bill_msg)
                    else:
                        send_whatsapp_msg(chat_id, "Please reply with a valid *number* for the quantity (e.g., '2 strips' or just '2').")

                elif conv.state == "AWAITING_CONFIRM":
                    if user_text == "confirm":
                        order = crud.create_order(
                            db=db,
                            user_id=user.id,
                            whatsapp_num=whatsapp_num,
                            medicine_id=conv.temp_medicine_id,
                            quantity=conv.temp_quantity
                        )
                        crud.reset_state(db, whatsapp_num)
                        send_whatsapp_msg(chat_id, f"✅ *Order Placed Successfully!*\n\nYour Order ID is *#{order.id}*.\nTotal to pay: ₹{order.total_amount}.\nPlease pay securely via UPI to our pharmacy handle: pharmacy@okicici.\n\nThank you for choosing MedBuddy! Type 'menu' to start a new action.")
                    else:
                        send_whatsapp_msg(chat_id, "Reply *CONFIRM* to place the order, or *CANCEL* to stop.")

                elif conv.state == "AWAITING_ORDER_ID":
                    # Try to extract numbers from the input, handling things like "#4"
                    numbers = re.findall(r'\d+', user_text)
                    if numbers:
                        order_id = int(numbers[0])
                        order = crud.get_order(db, order_id)
                        if order and order.whatsapp_num == whatsapp_num:
                            crud.reset_state(db, whatsapp_num)
                            send_whatsapp_msg(chat_id, f"📦 *Track Order #{order.id}*\n\nStatus: *{order.status}*\nTotal: ₹{order.total_amount}\nPlaced on: {order.created_at.strftime('%Y-%m-%d %H:%M')}")
                        else:
                            send_whatsapp_msg(chat_id, "❌ We couldn't find an order with that ID for your number. Please try again or type 'cancel'.")
                    else:
                        send_whatsapp_msg(chat_id, "Please reply with a valid *numeric* Order ID (e.g., 4).")

    except Exception as e:
        return {"status": "error", "error": str(e)}

    return {"status": "success"}