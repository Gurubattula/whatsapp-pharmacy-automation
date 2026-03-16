# MedBuddy 🤖🏥

**MedBuddy** is an AI-powered WhatsApp Pharmacy Automation System designed to streamline medicine ordering and tracking. It integrates WhatsApp via Whapi.cloud and Google Gemini 1.5 Flash to provide a seamless, conversational interface for users to interact with a pharmacy.

---

## 🚀 Key Features

- **Conversational AI**: Uses Gemini 1.5 Flash to extract medicine names and quantities from natural language messages.
- **WhatsApp Integration**: Real-time communication via Whapi.cloud webhooks.
- **Automated Ordering**: Complete flow from medicine search to order confirmation and payment instructions (UPI).
- **Inventory Management**: MySQL-backed medicine catalog with fuzzy matching for misspelled names.
- **Order Tracking**: Real-time status updates for placed orders.
- **Persistent State**: Database-driven conversation state management ensures users can resume interactions.

---

## 🛠️ Tech Stack

- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python)
- **Database**: MySQL with [SQLAlchemy](https://www.sqlalchemy.org/) ORM
- **AI Engine**: [Google Gemini 1.5 Flash](https://ai.google.dev/)
- **Messaging**: [Whapi.cloud](https://whapi.cloud/) (WhatsApp Business API)
- **Fuzzy Matching**: [TheFuzz](https://github.com/seatgeek/thefuzz)
- **Testing**: [Pytest](https://docs.pytest.org/)

---

## 📂 Project Structure

```bash
MedBuddy_2/
├── main.py            # FastAPI entry point & Webhook handler
├── crud.py            # Database CRUD operations
├── models.py          # SQLAlchemy models
├── schemas.py         # Pydantic schemas (Data validation)
├── database.py        # Database connection setup
├── seeds.py           # Database seeding script (Demo data)
├── utils/
│   ├── gemini_ai.py   # AI parsing logic
│   └── whatsapp.py    # WhatsApp messaging utilities
├── tests/             # Automated test suite
├── .env               # Environment variables (API Keys, DB Credentials)
└── requirements.txt   # Python dependencies
```

---

## ⚙️ Setup & Installation

### 1. Prerequisites
- Python 3.8+
- MySQL Server
- Whapi.cloud account & API token
- Google AI (Gemini) API Key

### 2. Clone and Install Dependencies
```bash
git clone <repository-url>
cd MedBuddy_2
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory:
```env
DATABASE_URL=mysql+mysqlconnector://user:password@localhost/medbuddy_db
WHAPI_TOKEN=your_whapi_token
GEMINI_API_KEY=your_gemini_api_key
WHAPI_API_URL=https://gate.whapi.cloud
```

### 4. Database Initialization
Run the seeding script to create tables and add demo medicines:
```bash
python seeds.py
```

### 5. Running the API
```bash
uvicorn main:app --reload
```

---

## 🤖 Conversation Flow

1. **Greeting**: Say "Hi" or "MedBuddy" to see the main menu.
2. **Order**: Select "1" or say "Order medicine".
3. **Item**: Provide the medicine name (e.g., "I need 2 strips of Dolo 650").
4. **Quantity**: If not provided, MedBuddy will ask for it.
5. **Confirm**: Review the summary and reply "CONFIRM".
6. **Payment**: Receive UPI details and Order ID.
7. **Track**: Use the Order ID to check status anytime.

---

## 🧪 Testing

Run the test suite using `pytest`:
```bash
pytest tests/
```

---

## 📜 License
[MIT License](LICENSE)
