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
    print(f"Bot started for {today}...")
    
    try:
        # १. उपलब्ध मोडेल खोज्ने
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
        response = requests.get(list_url)
        if response.status_code != 200:
            send_email(f"API Key Error: {response.text}", today)
            return

        models_data = response.json()
        available_models = [m['name'] for m in models_data.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
        
        if not available_models:
            send_email("No models found for this API Key.", today)
            return

        chosen_model = available_models[0]
        gen_url = f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={API_KEY}"
        prompt = f"Today is {today}. List 10 active tenders in Nepal from bolpatra.gov.np and newspapers in a clean table."
        data = {"contents": [{"parts": [{"text": prompt}]}]}

        # २. ५०३ एरर आएमा ५ पटकसम्म कोसिस गर्ने (Retry Logic)
        content = ""
        for attempt in range(5):
            res = requests.post(gen_url, json=data)
            if res.status_code == 200:
                content = res.json()['candidates'][0]['content']['parts'][0]['text']
                send_email(content, today)
                print("SUCCESS: Email sent!")
                return
            elif res.status_code == 503:
                print(f"Server busy (503). Retrying in 60s... (Attempt {attempt+1})")
                time.sleep(60) # १ मिनेट पर्खिने
            else:
                content = f"Model error: {res.text}"
                break
        
        send_email(content, today)

    except Exception as e:
        send_email(f"Script error: {str(e)}", today)

def send_email(body, date):
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = f"Nepal Tender Report - {date}"
    msg['From'] = SENDER
    msg['To'] = SENDER
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(SENDER, PASSWORD)
    server.sendmail(SENDER, SENDER, msg.as_string())
    server.quit()

if __name__ == "__main__":
    run_bot()
