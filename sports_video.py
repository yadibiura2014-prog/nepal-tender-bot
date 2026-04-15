import os, requests, json, time, asyncio, textwrap
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

# Compatibility fix
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import edge_tts
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# --- Secrets ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
PEXELS_KEY = os.getenv("PEXELS_KEY")
SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")

async def run_sports_bulletin():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"⚽ Context-Aware Sports Process Started for {today}...")

    # १. न्युज संकलन
    combined_news = []
    sources = ["https://ekantipur.com/sports", "https://ratopati.com/category/sport", "https://setopati.com/khel", "https://www.hamrokhelkud.com/"]
    headers = {'User-Agent': 'Mozilla/5.0'}
    for u in sources:
        try:
            r = requests.get(u, headers=headers, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                for item in soup.find_all(['h1', 'h2', 'h3'])[:10]:
                    title = item.get_text().strip()
                    p = item.find_next('p')
                    desc = p.get_text().strip() if p else ""
                    if len(title) > 25: combined_news.append(f"HEADLINE: {title} | INFO: {desc}")
        except: pass

    news_data = "\n".join(list(set(combined_news)))

    # २. एआई विश्लेषण (Identifying Sport & Context)
    prompt = f"""
    तिमी एक विशेषज्ञ स्पोर्ट्स एनालिस्ट हौ। आजका ५ मुख्य समाचार छान।
    
    नियमहरू:
    १. समाचारको भाव बुझ (जस्तै: ए डिभिजन लिग = Football, नेप्से होइन)।
    २. फोटोको लागि एकदमै 'Specific' अंग्रेजी कीवर्ड देउ। यदि खेलाडीको नाम छ भने नाम लेख।
    ३. भाषा: शुद्ध र ठेट नेपाली।
    
    मलाई यो 'json' मा उत्तर देउ: 
    {{
      "intro": "नमस्ते, दैनिक खेलकुद बुलेटिनमा स्वागत छ।",
      "bulletin": [
        {{"num": "१", "headline": "...", "details": "...", "search_query": "Asian football action match"}}
      ],
      "outro": "धन्यवाद, भोलि भेटौँला।"
    }}
    DATA: {news_data}
    """
    
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    m_res = requests.get(list_url).json()
    usable = [m['name'] for m in m_res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
    chosen_model = next((m for m in usable if "gemini-1.5-flash" in m), usable[0])

    res = requests.post(f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={GEMINI_KEY}", 
                        jso
