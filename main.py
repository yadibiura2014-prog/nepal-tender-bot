import os
import requests
import google.generativeai as genai
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

# Secrets
API_KEY = os.getenv("GEMINI_API_KEY")
SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")

def run_bot():
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Aajako Date
    today = datetime.now().strftime("%Y-%m-%d")
    
    # AI lai Newspaper haru check garna lagaune
    # Note: Yo AI ko knowledge base ma adharit hunchha. 
    # Aglo step ma hami direct PDF download garne code thapnechau.
    prompt = f"""
    Today's date is {today}. Act as a Nepali Tender Analyst.
    Your task is to find and list all government and private tenders 
    published in today's major Nepali newspapers (Gorkhapatra, Kantipur, etc.).
    
    Provide the information in a table format:
    1. Organization Name
    2. Work Description (What is the tender for?)
    3. Deadline (Closing Date)
    4. Source (Newspaper Name)
    
    If you don't have access to live data, please list the links of 
    today's e-papers for the user to check manually.
    """
    
    try:
        response = model.generate_content(prompt)
        send_email(response.text)
        print("Bot successfully ran!")
    except Exception as e:
        print(f"Error: {e}")

def send_email(content):
    msg = MIMEText(content)
    msg['Subject'] = f"Daily Tender Report - {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = SENDER
    msg['To'] = SENDER

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(SENDER, PASSWORD)
        server.sendmail(SENDER, SENDER, msg.as_string())

if __name__ == "__main__":
    run_bot()
