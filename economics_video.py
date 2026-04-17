import os, requests, json, time, asyncio, textwrap
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

# Pillow Fix
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
SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")

async def run_final_reset():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 Hard-Reset Economics Process Started for {today}...")

    # १. न्युज संकलन (Headline Only)
    headlines = []
    sources = ["https://ekantipur.com/business", "https://kathmandupost.com/money", "https://setopati.com/kinmel", "https://www.sharesansar.com/category/latest-news"]
    headers = {'User-Agent': 'Mozilla/5.0'}
    for u in sources:
        try:
            r = requests.get(u, headers=headers, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                for item in soup.find_all(['h1', 'h2', 'h3'])[:5]:
                    txt = item.get_text().strip()
                    if len(txt) > 30: headlines.append(txt)
        except: pass
    
    clean_news = "\n".join(list(set(headlines))[:12])

    # २. एआई विश्लेषण (With Safety Override)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    
    prompt = f"""
    तिमी एक प्रतिष्ठित Economic Analyst हौ। आजको ६ वटा मुख्य आर्थिक समाचार छान। 
    नियम:
    १. पहिलो खबर 'झड्का' दिने हेडलाइन (Hook) हुनुपर्छ।
    २. सबै कुरा शुद्ध नेपालीमा लेख।
    ३. हरेक समाचार यो फर्म्याटमा लेख: "HEADLINE: [हेडलाइन] | DETAILS: [१ वाक्यको तथ्य]"
    HEADLINES: {clean_news}
    """

    # Safety settings लाई हटाउने कमान्ड (BLOCK_NONE)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }

    data_text = ""
    for attempt in range(5):
        try:
            res = requests.post(url, json=payload, timeout=30)
            res_json = res.json()
            if res.status_code == 200 and 'candidates' in res_json:
                data_text = res_json['candidates'][0]['content']['parts'][0]['text']
                print(f"✅ एआईले सफलतापूर्वक उत्तर दियो!")
                break
            else:
                print(f"⚠️ गुगल एरर मेसेज: {res.text}")
                time.sleep(20)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(20)

    if not data_text:
        print("❌ एआईबाट जवाफ आएन।")
        return

    # ३. डाटा प्रोसेसिङ
    scenes = []
    for line in data_text.split('\n'):
        if '|' in line and 'HEADLINE' in line:
            p = line.split('|')
            h = p[0].replace('HEADLINE:', '').strip()
            d = p[1].replace('DETAILS:', '').strip()
            scenes.append({'h': h, 'd': d})

    if not scenes:
        print("❌ डाटा बुझ्न सकिएन।")
        return

    # ४. भिडियो निर्माण
    os.system("wget -O font.ttf https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf")
    font_path = "font.ttf"
    final_clips = []

    def make_card(title, desc, num=""):
        img = Image.new('RGB', (1080, 1920), color=(15, 15, 15))
        draw = ImageDraw.Draw(img)
        try:
            f_h = ImageFont.truetype(font_path, 80)
            f_d = ImageFont.truetype(font_path, 45)
            if num: draw.text((80, 700), f"{num}.", font=f_h, fill=(255, 255, 0))
            y = 820
            for line in textwrap.wrap(title, width=22)[:3]:
                draw.text((80, y), line, font=f_h, fill=(255, 255, 0)); y += 110
            y += 40
            for line in textwrap.wrap(desc, width=42)[:4]:
                draw.text((80, y), line, font=f_d, fill=(230, 230, 230)); y += 70
            draw.text((320, 1820), "दैनिक आर्थिक समाचार", font=f_d, fill=(80, 80, 80))
        except: pass
        img.save("t.jpg")
        return ImageClip("t.jpg")

    # ५. अडियो र सिन सिङ्क
    print("🎙️ अडियो र भिडियो सिङ्क हुँदैछ...")
    for i, sc in enumerate(scenes[:6]):
        txt = f"{i+1}. . . {sc['h']}. . . {sc['d']}"
        v_file = f"v_{i}.mp3"
        await edge_tts.Communicate(txt, "ne-NP-SagarNeural", rate="+10%", pitch="-5Hz").save(v_file)
        
        a_clip = AudioFileClip(v_file)
        clip = make_card(sc['h'], sc['d'], num=str(i+1)).set_duration(a_clip.duration).set_audio(a_clip)
        final_clips.append(clip.resize(lambda t: 1 + 0.02 * t))

    # ६. एक्सपोर्ट र ईमेल
    video = concatenate_videoclips(final_clips, method="compose")
    output = "economics_final.mp4"
    video.write_videofile(output, fps=24, codec="libx264", audio_codec="aac", bitrate="1500k", ffmpeg_params=["-pix_fmt", "yuv420p"])

    send_video_email(output, today)

def send_video_email(filepath, date):
    msg = MIMEMultipart(); msg['From'] = SENDER; msg['To'] = SENDER; msg['Subject'] = f"Economics Daily - {date}"
    with open(filepath, "rb") as f:
        part = MIMEBase('application', 'octet-stream'); part.set_payload(f.read()); encoders.encode_base64(part); part.add_header('Content-Disposition', f"attachment; filename= economics_video.mp4"); msg.attach(part)
    server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login(SENDER, PASSWORD); server.sendmail(SENDER, SENDER, msg.as_string()); server.quit()

if __name__ == "__main__":
    asyncio.run(run_final_reset())
