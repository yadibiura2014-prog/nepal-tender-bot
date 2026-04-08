import os
import google.generativeai as genai
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

# Secrets haru read garne
API_KEY = os.getenv("GEMINI_API_KEY")
SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")

def run_bot():
    # Gemini AI setup
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # AI lai instructions (Prompt)
    # Suru ma hami AI lai testing ko lagi normal request garchau
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = f"Today's date is {today}. Act as a Tender expert in Nepal. Please provide a short guide on where to find tenders in Nepal and say 'The bot is working!'"
    
    try:
        response = model.generate_content(prompt)
        content = response.text
        
        # Email pathaune
        send_email(content)
        print("Bot successfully ran and email sent!")
        
    except Exception as e:
        print(f"Error bhayo: {e}")

def send_email(content):
    msg = MIMEText(content)
    msg['Subject'] = f"Tender Bot Test - {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = SENDER
    msg['To'] = SENDER

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(SENDER, PASSWORD)
        server.sendmail(SENDER, SENDER, msg.as_string())

if __name__ == "__main__":
    run_bot()
