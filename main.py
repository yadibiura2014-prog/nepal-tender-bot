import os
from google import genai
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

# Secrets
API_KEY = os.getenv("GEMINI_API_KEY")
SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")

def run_bot():
    print("Bot suru bhayo (New SDK)...")
    try:
        # Naya SDK use gareko
        client = genai.Client(api_key=API_KEY)
        
        # AI content generate garne
        response = client.models.generate_content(
            model="gemini-1.5-flash", 
            contents="Say 'Bot is finally working' and tell me one tender tip for Nepal."
        )
        
        content = response.text
        print("AI Content: " + content)
        
        # Email pathaune
        send_email(content)
        print("Email successfully sent!")
        
    except Exception as e:
        print(f"Error bhayo: {str(e)}")

def send_email(content):
    msg = MIMEText(content)
    msg['Subject'] = "Tender Bot - Status OK"
    msg['From'] = SENDER
    msg['To'] = SENDER

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(SENDER, PASSWORD)
        server.sendmail(SENDER, SENDER, msg.as_string())

if __name__ == "__main__":
    run_bot()
