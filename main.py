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
    
    prompt = f"Today is {today}. Find and list 5-10 new tender notices from Nepal PPMO (bolpatra.gov.np) and newspapers. Provide details in a table."
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    # गुगलको ३ वटा फरक ठेगाना (URLs) हरू - एउटा न एउटाले पक्का काम गर्छ
    urls = [
        f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}",
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}",
        f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={API_KEY}"
    ]

    content = ""
    success = False

    for url in urls:
        try:
            print(f"Trying URL: {url.split('models/')[1].split(':')[0]}")
            response = requests.post(url, json=data)
            if response.status_code == 200:
                result = response.json()
                content = result['candidates'][0]['content']['parts'][0]['text']
                success = True
                print("SUCCESS: Data found!")
                break
            else:
                print(f"Failed with status: {response.status_code}")
        except Exception as e:
            print(f"Error on this URL: {e}")
            continue

    if not success:
        content = "AI model error (404). Please check your Gemini API key permissions or try again later. For now, please check bolpatra.gov.np manually."

    # ईमेल पठाउने
    send_email(content, today)

def send_email(body, date):
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = f"Nepal Tender Alert - {date}"
    msg['From'] = SENDER
    msg['To'] = SENDER

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(SENDER, PASSWORD)
    server.sendmail(SENDER, SENDER, msg.as_string())
    server.quit()
    print("Email sent.")

if __name__ == "__main__":
    run_bot()
