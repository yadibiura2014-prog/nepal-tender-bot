import os
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# Secrets
API_KEY = os.getenv("GEMINI_API_KEY")
SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")

def run_bot():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"--- Process Started for {today} ---")
    
    combined_data = ""

    # १. पत्रिकाको डाटा तान्ने (User-Agent थपेर ताकी ब्लक नहोस्)
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        news_res = requests.get("https://tendernotice.com.np/", headers=headers, timeout=20)
        if news_res.status_code == 200:
            soup = BeautifulSoup(news_res.text, 'html.parser')
            combined_data += "NEWSPAPER DATA:\n" + soup.get_text()[:10000]
            print("Successfully fetched newspaper data.")
        else:
            print(f"Newspaper site returned status: {news_res.status_code}")
    except Exception as e:
        print(f"Newspaper fetch error: {e}")

    # २. एआईलाई कमान्ड दिने
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    prompt = f"Today is {today}. From the provided text, list all new tenders from Nepal newspapers (Kantipur, Nagarik, etc) and Bolpatra in a clean table. Data: {combined_data}"
    
    try:
        print("Sending data to AI...")
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        if response.status_code == 200:
            content = response.json()['candidates'][0]['content']['parts'][0]['text']
            print("AI response received.")
            send_email(content, today)
        else:
            print(f"AI Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"AI Connection error: {e}")

def send_email(body, date):
    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = f"Nepal Tender Report - {date}"
        msg['From'] = SENDER
        msg['To'] = SENDER

        print(f"Connecting to Gmail as {SENDER}...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER, PASSWORD)
        server.sendmail(SENDER, SENDER, msg.as_string())
        server.quit()
        print("!!! EMAIL SENT SUCCESSFULLY !!!")
    except Exception as e:
        print(f"!!! EMAIL FAILED: {str(e)} !!!")

if __name__ == "__main__":
    run_bot()
