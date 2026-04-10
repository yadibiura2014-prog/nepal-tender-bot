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
    
    # १. तपाईँको की (Key) मा कुन मोडेल चल्छ भनेर खोज्ने
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    
    try:
        response = requests.get(list_url)
        if response.status_code != 200:
            send_email(f"API Key Error: {response.text}", today)
            return

        models_data = response.json()
        available_models = [m['name'] for m in models_data.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
        
        if not available_models:
            send_email("तपाईँको API Key मा कुनै पनि मोडेल भेटिएन। कृपया नयाँ Key निकाल्नुहोस्।", today)
            return

        # उपलब्ध मध्ये पहिलो मोडेल प्रयोग गर्ने (जस्तै gemini-1.5-flash वा gemini-pro)
        chosen_model = available_models[0]
        print(f"Using model: {chosen_model}")

        # २. टेन्डर खोज्ने काम सुरु गर्ने
        gen_url = f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={API_KEY}"
        prompt = f"Today is {today}. Find 5-10 active tenders in Nepal from bolpatra.gov.np and newspapers. List them in a table."
        data = {"contents": [{"parts": [{"text": prompt}]}]}

        res = requests.post(gen_url, json=data)
        if res.status_code == 200:
            content = res.json()['candidates'][0]['content']['parts'][0]['text']
            send_email(content, today)
            print("Email sent successfully with data!")
        else:
            send_email(f"Model error: {res.text}", today)

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
