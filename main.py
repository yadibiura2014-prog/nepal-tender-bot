import os
import requests
import smtplib
import time
from email.mime.text import MIMEText
from datetime import datetime

# Secrets
API_KEY = os.getenv("GEMINI_API_KEY")
SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")

def run_bot():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"Bot started for {today}")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    prompt = f"""
    Today's date is {today}. Your task is to act as a Nepal Tender Expert. 
    Find and list all new tender notices published today in Nepal from:
    1. PPMO Bolpatra website (bolpatra.gov.np)
    2. Gorkhapatra and Kantipur Newspapers.
    
    Provide the data in a table:
    | Organization | Tender Description | Deadline | Source |
    
    If you cannot find live data for today, list 10 most recent active tenders from bolpatra.gov.np.
    """
    
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    # ५०३ एरर आएमा ५ पटक सम्म कोसिस गर्ने
    for attempt in range(5):
        try:
            response = requests.post(url, json=data)
            if response.status_code == 200:
                content = response.json()['candidates'][0]['content']['parts'][0]['text']
                send_email(content, today)
                print("SUCCESS: Email sent.")
                return 
            elif response.status_code == 503:
                print(f"Server busy (503). Retrying in 60 seconds... (Attempt {attempt + 1})")
                time.sleep(60) # १ मिनेट पर्खिने
            else:
                print(f"API Error: {response.status_code}")
                break
        except Exception as e:
            print(f"Error: {e}")
            break

def send_email(body, date):
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = f"Nepal Tender Report - {date}"
    msg['From'] = SENDER
    msg['To'] = SENDER

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(SENDER, PASSWORD)
        server.sendmail(SENDER, SENDER, msg.as_string())

if __name__ == "__main__":
    run_bot()
