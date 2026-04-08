import os
import requests
import smtplib
from email.mime.text import MIMEText

# Secrets
API_KEY = os.getenv("GEMINI_API_KEY")
SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")

def run_bot():
    print("Bot suru bhayo (Stable API Method)...")
    
    # Model ko naam 'gemini-pro' ma change gareko ani version 'v1' banako
    # Yo sabai vanda stable URL ho
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": "Say 'The bot is finally working!' and give me one motivation for today."}]
        }]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        
        # Yadi 'gemini-pro' le pani 404 diyo bhane 'gemini-1.5-flash' try garne logic
        if response.status_code == 404:
            print("gemini-pro bhetena, flash try gardai...")
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
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
    msg['Subject'] = "Tender Bot - Status OK"
    msg['From'] = SENDER
    msg['To'] = SENDER

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(SENDER, PASSWORD)
        server.sendmail(SENDER, SENDER, msg.as_string())

if __name__ == "__main__":
    run_bot()
