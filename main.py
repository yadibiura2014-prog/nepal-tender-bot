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
        genai.configure(api_key=API_KEY)
        
        # Flash model try garne, bhetene bhane Pro try garne
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content("Say 'System Online'")
        except:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content("Say 'System Online'")
            
        content = response.text
        print("AI Content: " + content)
        
        # Email function
        msg = MIMEText(f"Bot working fine. AI says: {content}")
        msg['Subject'] = "Tender Bot - Status OK"
        msg['From'] = SENDER
        msg['To'] = SENDER

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER, PASSWORD)
            server.sendmail(SENDER, SENDER, msg.as_string())
        
        print("Email successfully sent!")
        
    except Exception as e:
        print(f"Error bhayo: {str(e)}")

if __name__ == "__main__":
    run_bot()
