import requests
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Setup local logger for this utility
logger = logging.getLogger("whatsapp_utils")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler("whatsapp_debug.log")
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

def send_whatsapp_msg(to_chat_id, text):
    url = f"{os.getenv('WHAPI_API_URL')}/messages/text"
    headers = {
        "Authorization": f"Bearer {os.getenv('WHAPI_TOKEN')}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": to_chat_id,
        "body": text
    }
    logger.info(f"Attempting to send message to {to_chat_id}")
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        res_json = response.json()
        logger.info(f"Whapi Response for {to_chat_id}: {res_json}")
        return res_json
    except Exception as e:
        logger.error(f"WhatsApp Send Error to {to_chat_id}: {e}")
        return None