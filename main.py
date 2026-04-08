import os
import requests
import smtplib
from email.mime.text import MIMEText

# Secrets
API_KEY = os.getenv("GEMINI_API_KEY")
SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")

def run_bot():
    print("Bot suru bhayo (Ultimate Fix)...")
    
    # 1. Paila model bhetincha ki nai check garne
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    
    try:
        # Paila available models herne
        get_models = requests.get(list_url)
        content_to_send = ""
        
        if get_models.status_code == 200:
            models_data = get_models.json()
            # Sabai bhanda mathillo model line
            first_model = models_data['models'][0]['name']
            print(f"Model bhetiyo: {first_model}")
            
            # 2. Bhetiyeko model bata content generate garne
            gen_url = f"https://generativelanguage.googleapis.com/v1beta/{first_model}:generateContent?key={API_KEY}"
            data = {"contents": [{"parts": [{"text": "Say 'System is online' and give a small tender tip."}]}]}
            
            res = requests.post(gen_url, json=data)
            if res.status_code == 200:
                content_to_send = res.json()['candidates'][0]['content']['parts'][0]['text']
            else:
                content_to_send = f"AI le error diyo: {res.text}"
        else:
            content_to_send = "Google API connection issue, but bot script is running!"

        # 3. Email pathaune (Yo step AI fail bhaye pani chalcha)
        send_email(content_to_send)
        print("Email success!")

    except Exception as e:
        print(f"Galti bhayo: {str(e)}")
        # Error bhaye pani mail pathaune kosis garne
        send_email(f"Script chalyo tara error aayo: {str(e)}")

def send_email(body):
    msg = MIMEText(body)
    msg['Subject'] = "Tender Bot - Status Update"
    msg['From'] = SENDER
    msg['To'] = SENDER

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(SENDER, PASSWORD)
        server.sendmail(SENDER, SENDER, msg.as_string())

if __name__ == "__main__":
    run_bot()
