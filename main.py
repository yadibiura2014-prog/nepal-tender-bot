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
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"Bot started for {today}...")
    
    # गुगलको सबैभन्दा नयाँ र चल्ने URL (v1 version)
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    prompt = f"Today is {today}. Find 5-10 new tenders in Nepal from PPMO (bolpatra.gov.np) and newspapers. List them in a clean table."
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, json=data)
        
        # यदि v1 ले काम गरेन भने v1beta कोसिस गर्ने (Back-up plan)
        if response.status_code != 200:
            url_beta = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
            response = requests.post(url_beta, json=data)

        if response.status_code == 200:
            result = response.json()
            content = result['candidates'][0]['content']['parts'][0]['text']
            send_email(content, today)
            print("SUCCESS: Data sent.")
        else:
            send_email(f"AI Error: {response.text}", today)
            
    except Exception as e:
        print(f"Error: {e}")

def send_email(body, date):
    # ईमेललाई राम्रो बनाउन Markdown बाट HTML मा सामान्य ढाँचा दिने
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = f"Nepal Tender Alert - {date}"
    msg['From'] = SENDER
    msg['To'] = SENDER

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(SENDER, PASSWORD)
    server.sendmail(SENDER, SENDER, msg.as_string())
    server.quit()

if __name__ == "__main__":
    run_bot()
