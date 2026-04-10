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
    
    # १. कुन मोडेल उपलब्ध छ भनेर गुगललाई सोध्ने (Model Discovery)
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    
    try:
        model_res = requests.get(list_url)
        if model_res.status_code != 200:
            send_email(f"API Key Error: {model_res.text}", today)
            return

        models_list = model_res.json().get('models', [])
        # 'generateContent' सपोर्ट गर्ने मोडेल छान्ने
        usable_models = [m['name'] for m in models_list if 'generateContent' in m.get('supportedGenerationMethods', [])]
        
        if not usable_models:
            send_email("तपाईँको API Key मा कुनै पनि मोडेल भेटिएन।", today)
            return

        # उपलब्ध मध्ये सबैभन्दा राम्रो मोडेल रोज्ने (Priority: Flash 1.5 > Pro)
        chosen_model = usable_models[0]
        for m in usable_models:
            if 'gemini-1.5-flash' in m:
                chosen_model = m
                break
        
        print(f"Using Model: {chosen_model}")

        # २. पत्रिकाको डाटा तान्ने
        headers = {'User-Agent': 'Mozilla/5.0'}
        news_res = requests.get("https://tendernotice.com.np/", headers=headers, timeout=20)
        soup = BeautifulSoup(news_res.text, 'html.parser')
        combined_data = ' '.join(soup.get_text().split())[:15000]

        # ३. छानिएको मोडेल प्रयोग गरेर एआईलाई बोलाउने
        gen_url = f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={API_KEY}"
        prompt = f"Today is {today}. Extract all tender notices from this Nepal newspaper text into a clean table (Organization, Description, Deadline, Source). Text: {combined_data}"
        
        response = requests.post(gen_url, json={"contents": [{"parts": [{"text": prompt}]}]})
        
        if response.status_code == 200:
            content = response.json()['candidates'][0]['content']['parts'][0]['text']
            send_email(content, today)
        else:
            send_email(f"AI Generation Error: {response.text}", today)

    except Exception as e:
        print(f"Critical Error: {e}")
        send_email(f"Script Error: {str(e)}", today)

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
        print("!!! EMAIL SENT !!!")
    except Exception as e:
        print(f"!!! MAIL FAIL: {e} !!!")

if __name__ == "__main__":
    run_bot()
