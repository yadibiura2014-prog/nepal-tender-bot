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
    Today's date is {today}. Act as a Nepal Tender Expert. 
    Task: Find all new tender notices published today in Nepal from:
    1. PPMO Bolpatra website (bolpatra.gov.np)
    2. Gorkhapatra and Kantipur Newspapers.
    
    Please provide a detailed list in a table:
    | Organization | Description of Work | Deadline | Source |
    
    Important: If you cannot find live data for today, provide the most recent 10 active tenders from bolpatra.gov.np for construction and consulting works.
    """
    
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    # Retry logic: Error aayo bhane 3 choti samma try garne
    for i in range(3):
        try:
            response = requests.post(url, json=data)
            if response.status_code == 200:
                content = response.json()['candidates'][0]['content']['parts'][0]['text']
                send_email(content, today)
                print("SUCCESS: Email sent.")
                return 
            elif response.status_code == 503:
                print(f"Server busy (503), retrying in 30 seconds... (Attempt {i+1})")
                time.sleep(30)
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
