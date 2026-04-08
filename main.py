import os
import requests
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# Secrets
API_KEY = os.getenv("GEMINI_API_KEY")
SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")

def run_bot():
    print("Bot suru bhayo (Direct API Method)...")
    
    # Google API URL (Direct call, SDK chahindaina)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": "Say 'The system is finally working perfectly' and give me a 1-sentence tip for finding tenders in Nepal."}]
        }]
    }

    try:
        # API lai request pathaune
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            content = result['candidates'][0]['content']['parts'][0]['text']
            print("AI Response: " + content)
            
            # Email pathaune
            send_email(content)
            print("Email successfully sent!")
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Error bhayo: {str(e)}")

def send_email(content):
    msg = MIMEText(content)
    msg['Subject'] = "Tender Bot - 100% Success"
    msg['From'] = SENDER
    msg['To'] = SENDER

    # Port 587 is most stable for GitHub
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls() # Security
        server.login(SENDER, PASSWORD)
        server.sendmail(SENDER, SENDER, msg.as_string())

if __name__ == "__main__":
    run_bot()
