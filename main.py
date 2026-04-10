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
    print(f"Searching Tenders for {today}...")
    
    combined_data = ""

    # १. पत्रिकाको टेन्डरहरू सङ्कलन गर्ने वेबसाइटबाट डाटा तान्ने
    try:
        header = {'User-Agent': 'Mozilla/5.0'}
        # यो साइटले कान्तिपुर, अन्नपूर्ण, नागरिक सबैको डाटा राख्छ
        news_res = requests.get("https://tendernotice.com.np/", headers=header, timeout=15)
        soup = BeautifulSoup(news_res.text, 'lxml')
        combined_data += "--- NEWSPAPER TENDER DATA ---\n" + soup.get_text()[:15000]
    except Exception as e:
        print(f"Newspaper fetch error: {e}")

    # २. बोलपत्र (PPMO) बाट डाटा तान्ने
    try:
        ppmo_res = requests.get("https://bolpatra.gov.np/egp/", timeout=15)
        combined_data += "\n--- PPMO BOLPATRA DATA ---\n" + ppmo_res.text[:10000]
    except:
        pass

    # ३. एआईलाई सबै डाटा दिएर विश्लेषण गर्न लगाउने
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    prompt = f"""
    Today's date is {today}. 
    I have provided raw text from Nepal's tender aggregation sites and PPMO.
    
    DATA PROVIDED:
    {combined_data}
    
    TASK:
    1. Extract all tender notices published TODAY or RECENTLY.
    2. Identify the source for each (e.g., Kantipur, Annapurna Post, Nagarik, or PPMO).
    3. Provide a clean Markdown Table with columns: Organization, Description, Deadline, and Source Newspaper.
    
    Rule: Only list real tenders found in the data. If specific newspaper data is missing, focus on Bolpatra but clearly mention the source.
    """
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
        if response.status_code == 200:
            content = response.json()['candidates'][0]['content']['parts'][0]['text']
            send_email(content, today)
            print("SUCCESS: Tender Report Sent.")
        else:
            print(f"AI Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

def send_email(body, date):
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = f"Nepal Daily Tender Report (Newspapers + Bolpatra) - {date}"
    msg['From'] = SENDER
    msg['To'] = SENDER
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(SENDER, PASSWORD)
    server.sendmail(SENDER, SENDER, msg.as_string())
    server.quit()

if __name__ == "__main__":
    run_bot()
