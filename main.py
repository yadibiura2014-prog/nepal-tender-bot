import os
import requests
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import sys

# Secrets
API_KEY = os.getenv("GEMINI_API_KEY")
SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")

def run_bot():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"Bot started for {today}...")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    prompt = f"Today is {today}. List 5 active tenders from Nepal PPMO bolpatra.gov.np in a table."
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            content = response.json()['candidates'][0]['content']['parts'][0]['text']
            print("AI successfully generated data.")
            send_email(content, today)
        else:
            error_txt = f"AI Error: {response.status_code} - {response.text}"
            print(error_txt)
            send_email(error_txt, today)
            
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        # ईमेल पठाउन कोसिस गर्ने ताकी के एरर छ थाहा होस्
        try:
            send_email(f"Script Exception: {str(e)}", today)
        except:
            pass
        sys.exit(1) # GitHub लाई Fail बनाउने

def send_email(body, date):
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = f"Tender Update - {date}"
    msg['From'] = SENDER
    msg['To'] = SENDER

    print(f"Connecting to Gmail as {SENDER}...")
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER, PASSWORD)
        server.sendmail(SENDER, SENDER, msg.as_string())
        server.quit()
        print("--- EMAIL SENT SUCCESSFULLY! ---")
    except Exception as e:
        print(f"--- EMAIL FAILED: {str(e)} ---")
        raise e # यसले गर्दा GitHub रातो हुन्छ

if __name__ == "__main__":
    run_bot()
