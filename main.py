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
    print(f"Aajako Date: {today} | Tender khojna suru bhayo...")
    
    # AI lai Nepal ko tender search garna lagaune target list
    papers = "Gorkhapatra, Kantipur, The Kathmandu Post, The Rising Nepal, The Himalayan Times, Annapurna Post, Nagarik, Naya Patrika, Karobar Economic Daily, Janakpur today, Chitwan Post, Madhyanha, Aarthik Dainik, Bolpatra Nepal"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    prompt = f"""
    Today's date is {today}. Your task is to find and summarize all new tender notices published today in Nepal from: {papers} and the PPMO Bolpatra website.
    
    Please provide the data in a clean Nepali/English Table:
    1. Organization Name
    2. Tender Description
    3. Deadline (Closing Date)
    4. Source Newspaper/Site
    
    If you cannot find specific ones for today, list the most important active tenders from PPMO (Public Procurement Monitoring Office) Nepal.
    """
    
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            content = response.json()['candidates'][0]['content']['parts'][0]['text']
            send_email(content, today)
            print("Email success!")
        else:
            send_email(f"AI Search failed today. Please check PPMO site manually. Error: {response.text}", today)
            
    except Exception as e:
        print(f"Error: {e}")

def send_email(body, date):
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = f"Daily Tender Alert Nepal - {date}"
    msg['From'] = SENDER
    msg['To'] = SENDER

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(SENDER, PASSWORD)
        server.sendmail(SENDER, SENDER, msg.as_string())

if __name__ == "__main__":
    run_bot()
