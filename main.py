import os
import google.generativeai as genai
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

# Secrets
API_KEY = os.getenv("GEMINI_API_KEY")
SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")

def run_bot():
    print("Bot suru bhayo...")
    try:
        # API Setup
        genai.configure(api_key=API_KEY)
        
        # Model ko naam simple rakheko (error hatauna)
        model = genai.GenerativeModel('gemini-1.5-flash') 
        
        # AI lai test reply garna lagaune
        response = model.generate_content("Say 'Bot is Working' and tell me 1 fun fact about Nepal.")
        content = response.text
        
        print("AI Content: " + content)
        
        # Email pathaune
        send_email(content)
        print("Email successfully sent!")
        
    except Exception as e:
        print(f"Error bhayo: {str(e)}")

def send_email(content):
    msg = MIMEText(content)
    msg['Subject'] = "Tender Bot - Setup Successful"
    msg['From'] = SENDER
    msg['To'] = SENDER

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(SENDER, PASSWORD)
        server.sendmail(SENDER, SENDER, msg.as_string())

if __name__ == "__main__":
    run_bot()
