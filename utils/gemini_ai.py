import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extract_medicine_details(user_text):
    model = genai.GenerativeModel('gemini-pro')
    
    # Use double {{ }} for the JSON structure so Python doesn't think they are variables
    prompt = f"""
    Extract medicine names and quantities from this user message: "{user_text}"
    
    Return ONLY a JSON list of objects like this:
    [
      {{"name": "aspirin", "quantity": "1 strip"}},
      {{"name": "dolo 650", "quantity": "2 tablets"}}
    ]
    
    If no medicines are found, return an empty list [].
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean the response text to ensure it's valid JSON
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except Exception as e:
        print(f"Gemini Error: {e}")
        return []