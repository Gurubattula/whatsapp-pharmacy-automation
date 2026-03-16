import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, ANY
from main import app
import models
import datetime

client = TestClient(app)

# Helper to generate simulated WhatsApp payload
def make_payload(text, from_me=False):
    return {
        "messages": [
            {
                "from_me": from_me,
                "chat_id": "919876543210@c.us",
                "text": {"body": text}
            }
        ]
    }

# Mocking the CRUD operations and external utilities

@pytest.fixture
def mock_crud():
    with patch("main.crud") as mock:
        
        # Default mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock.get_or_create_user.return_value = mock_user

        # State management (simulate DB)
        state_store = {"state": "IDLE"}
        
        def mock_get_state(db, num):
            s = MagicMock()
            s.state = state_store["state"]
            s.temp_medicine_name = "Paracetamol"
            s.temp_medicine_id = 1
            s.temp_quantity = None
            return s
            
        def mock_set_state(db, num, st, **kwargs):
            state_store["state"] = st
            
        def mock_reset_state(db, num):
            state_store["state"] = "IDLE"

        mock.get_state.side_effect = mock_get_state
        mock.set_state.side_effect = mock_set_state
        mock.reset_state.side_effect = mock_reset_state
        
        yield mock

@pytest.fixture
def mock_whatsapp():
    with patch("main.send_whatsapp_msg") as mock:
        yield mock

@pytest.fixture
def mock_gemini():
    with patch("main.extract_medicine_details") as mock:
        # Default empty extraction so fallback to raw text happens
        mock.return_value = []
        yield mock

# --- Tests ---

def test_webhook_greet_shows_menu(mock_crud, mock_whatsapp, mock_gemini):
    response = client.post("/webhook", json=make_payload("hii medbuddy"))
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    
    # Assert state changed to MENU_SHOWN
    mock_crud.set_state.assert_called_with(ANY, "919876543210", "MENU_SHOWN")
    # Assert WhatsApp message sent
    assert mock_whatsapp.call_count == 1
    call_args = mock_whatsapp.call_args[0]
    assert "Welcome to MedBuddy" in call_args[1]

def test_webhook_menu_select_order(mock_crud, mock_whatsapp, mock_gemini):
    # Simulate user in MENU_SHOWN state
    mock_crud.get_state.side_effect = lambda db, num: MagicMock(state="MENU_SHOWN")
    
    response = client.post("/webhook", json=make_payload("1"))
    
    mock_crud.set_state.assert_called_with(ANY, "919876543210", "AWAITING_MEDICINE_NAME")
    assert "name of the medicine" in mock_whatsapp.call_args[0][1]

def test_webhook_medicine_found_instock(mock_crud, mock_whatsapp, mock_gemini):
    mock_crud.get_state.side_effect = lambda db, num: MagicMock(state="AWAITING_MEDICINE_NAME")
    
    # Mock finding a medicine
    mock_med = MagicMock()
    mock_med.name = "Dolo 650"
    mock_med.id = 2
    mock_med.price = 45.0
    mock_med.stock_quantity = 50
    mock_crud.get_medicine_fuzzy.return_value = mock_med
    
    response = client.post("/webhook", json=make_payload("dolo"))
    
    mock_crud.set_state.assert_called_with(ANY, "919876543210", "AWAITING_QUANTITY", 
                                          temp_medicine_name="Dolo 650", temp_medicine_id=2)
    assert "Available" in mock_whatsapp.call_args[0][1]

def test_webhook_medicine_out_of_stock(mock_crud, mock_whatsapp, mock_gemini):
    mock_crud.get_state.side_effect = lambda db, num: MagicMock(state="AWAITING_MEDICINE_NAME")
    
    # Mock finding an out-of-stock medicine
    mock_med = MagicMock()
    mock_med.name = "Cetirizine"
    mock_med.stock_quantity = 0
    mock_crud.get_medicine_fuzzy.return_value = mock_med
    
    response = client.post("/webhook", json=make_payload("cetirizine"))
    
    # Assert it resets state and says out of stock
    mock_crud.reset_state.assert_called_once()
    assert "Out of Stock" in mock_whatsapp.call_args[0][1]

def test_webhook_medicine_not_found(mock_crud, mock_whatsapp, mock_gemini):
    mock_crud.get_state.side_effect = lambda db, num: MagicMock(state="AWAITING_MEDICINE_NAME")
    mock_crud.get_medicine_fuzzy.return_value = None
    
    response = client.post("/webhook", json=make_payload("unknownmed"))
    
    mock_crud.reset_state.assert_called_once()
    assert "couldn't find" in mock_whatsapp.call_args[0][1].lower()

def test_webhook_quantity_shows_bill(mock_crud, mock_whatsapp, mock_gemini):
    mock_crud.get_state.side_effect = lambda db, num: MagicMock(
        state="AWAITING_QUANTITY", temp_medicine_id=1
    )
    
    mock_med = MagicMock()
    mock_med.name = "Paracetamol"
    mock_med.price = 30.0
    mock_crud.get_medicine_by_id.return_value = mock_med
    
    response = client.post("/webhook", json=make_payload("2"))
    
    # 2 qty * 30.0 = 60.0 total
    mock_crud.set_state.assert_called_with(ANY, "919876543210", "AWAITING_CONFIRM", temp_quantity=2)
    msg_sent = mock_whatsapp.call_args[0][1]
    assert "Order Summary" in msg_sent
    assert "₹60.0" in msg_sent

def test_webhook_confirm_creates_order(mock_crud, mock_whatsapp, mock_gemini):
    mock_crud.get_state.side_effect = lambda db, num: MagicMock(
        state="AWAITING_CONFIRM", temp_medicine_id=1, temp_quantity=2
    )
    
    mock_order = MagicMock()
    mock_order.id = 99
    mock_order.total_amount = 60.0
    mock_crud.create_order.return_value = mock_order
    
    response = client.post("/webhook", json=make_payload("confirm"))
    
    # Order should be created
    mock_crud.create_order.assert_called_once()
    mock_crud.reset_state.assert_called_once()
    
    msg_sent = mock_whatsapp.call_args[0][1]
    assert "Successfully" in msg_sent
    assert "#99" in msg_sent

def test_webhook_track_order_found(mock_crud, mock_whatsapp, mock_gemini):
    mock_crud.get_state.side_effect = lambda db, num: MagicMock(state="AWAITING_ORDER_ID")
    
    mock_order = MagicMock()
    mock_order.id = 99
    mock_order.status = "Dispatched"
    mock_order.total_amount = 60.0
    mock_order.whatsapp_num = "919876543210"
    mock_order.created_at = datetime.datetime(2026, 3, 10, 15, 30)
    mock_crud.get_order.return_value = mock_order
    
    response = client.post("/webhook", json=make_payload("track order 99"))
    
    mock_crud.get_order.assert_called_with(ANY, 99)
    msg_sent = mock_whatsapp.call_args[0][1]
    assert "Track Order #99" in msg_sent
    assert "Dispatched" in msg_sent

def test_webhook_cancel_command(mock_crud, mock_whatsapp, mock_gemini):
    # Doesn't matter what state they are in
    response = client.post("/webhook", json=make_payload("cancel"))
    mock_crud.reset_state.assert_called_once()
    assert "reset" in mock_whatsapp.call_args[0][1].lower()

def test_ignore_from_me_messages(mock_crud, mock_whatsapp, mock_gemini):
    response = client.post("/webhook", json=make_payload("hii", from_me=True))
    # Should completely skip processing
    mock_crud.get_state.assert_not_called()
    mock_whatsapp.assert_not_called()
