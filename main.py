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

    # १. पत्रिकाको डाटा तान्ने
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        news_res = requests.get("https://tendernotice.com.np/", headers=headers, timeout=20)
        soup = BeautifulSoup(news_res.text, 'html.parser')
        # अनावश्यक स्पेस हटाएर डाटा सफा गर्ने
        text = ' '.join(soup.get_text().split())
        combined_data = text[:15000] # १५ हजार अक्षर मात्र लिने
        print("Successfully fetched newspaper data.")
    except Exception as e:
        print(f"Newspaper fetch error: {e}")

    # २. एआईलाई कमान्ड दिने (Stable v1 URL प्रयोग गरेर)
    # v1beta को साटो v1 प्रयोग गरिएको छ ताकी ४०४ एरर नआओस्
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    prompt = f"Today is {today}. From the following text of Nepal newspapers, extract all tender notices in a clean table with columns: Organization, Description, Deadline, and Source Newspaper. Data: {combined_data}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        print("Calling Gemini AI (v1)...")
        response = requests.post(url, json=payload, timeout=30)
        
        # यदि v1 ले काम गरेन भने v1beta कोसिस गर्ने (Back-up)
        if response.status_code == 404:
            print("v1 failed, trying v1beta...")
            url_beta = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
            response = requests.post(url_beta, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            content = result['candidates'][0]['content']['parts'][0]['text']
            print("AI response received successfully.")
            send_email(content, today)
        else:
            error_msg = f"AI Error: {response.status_code} - {response.text}"
            print(error_msg)
            send_email(error_msg, today)
            
    except Exception as e:
        print(f"Critical Error: {e}")

def send_email(body, date):
    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = f"Nepal Tender Report - {date}"
        msg['From'] = SENDER
        msg['To'] = SENDER

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
