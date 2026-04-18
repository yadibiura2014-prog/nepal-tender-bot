import os, requests, json, time, asyncio, textwrap, re
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

async def run_clean_bulletin():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 Clean Economics Bulletin Started for {today}...")

    # १. न्युज संकलन (Headline Only)
    headlines = []
    sources = ["https://ekantipur.com/business", "https://kathmandupost.com/money", "https://setopati.com/kinmel", "https://ratopati.com/category/economy", "https://baarakhari.com/category/business", "https://www.sharesansar.com/category/latest-news"]
    headers = {'User-Agent': 'Mozilla/5.0'}
    for u in sources:
        try:
            r = requests.get(u, headers=headers, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                for item in soup.find_all(['h1', 'h2', 'h3'])[:6]:
                    txt = item.get_text().strip()
                    if len(txt) > 25: headlines.append(txt)
        except: pass
    
    clean_news = "\n".join(list(set(headlines))[:15])

    # २. एआई विश्लेषण (Direct 6 News)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    
    prompt = f"""
    तिमी एक प्रतिष्ठित Economic Analyst हौ। आजको ६ वटा मुख्य आर्थिक समाचार छान। 
    नियम:
    १. कुनै 'Hook' वा गफ नगर्नु। सिधै ६ वटा समाचार लेख।
    २. सबै कुरा शुद्ध नेपालीमा लेख। अङ्ग्रेजी निषेध छ।
    ३. हरेक समाचार यो फर्म्याटमा लेख: "नम्बर: [नम्बर] | हेडलाइन: [हेडलाइन] | विवरण: [१-२ वाक्यको तथ्य]"
    ४. इन्ट्रो: "नमस्ते, आजका आर्थिक समाचारहरूमा स्वागत छ।"
    HEADLINES: {clean_news}
    """

    data_text = ""
    for attempt in range(5):
        try:
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
            if res.status_code == 200:
                data_text = res.json()['candidates'][0]['content']['parts'][0]['text']
                print(f"✅ एआई सफलता!")
                break
            else:
                print(f"⚠️ एआई व्यस्त (Error {res.status_code}), फेरि कोसिस गर्दै...")
                time.sleep(20)
        except: time.sleep(20)

    if not data_text:
        print("❌ एआईबाट जवाफ आएन।")
        return

    # ३. डाटा प्रोसेसिङ
    scenes = []
    for line in data_text.split('\n'):
        if '|' in line and 'हेडलाइन' in line:
            p = line.split('|')
            h = p[1].replace('हेडलाइन:', '').strip()
            d = p[2].replace('विवरण:', '').strip()
            scenes.append({'h': h, 'd': d})

    if not scenes:
        print("❌ डाटा बुझ्न सकिएन।")
        return

    # ४. भिडियो निर्माण
    os.system("wget -O font.ttf https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf")
    font_path = "font.ttf"
    final_clips = []

    def make_card(title, desc, num="", is_intro=False):
        img = Image.new('RGB', (1080, 1920), color=(15, 15, 15))
        draw = ImageDraw.Draw(img)
        try:
            f_h = ImageFont.truetype(font_path, 80)
            f_d = ImageFont.truetype(font_path, 45)
            if num: draw.text((80, 700), f"{num}.", font=f_h, fill=(255, 255, 0))
            
            y = 900 if is_intro else 820
            h_lines = textwrap.wrap(title, width=22)
            for line in h_lines[:3]:
                draw.text((80, y), line, font=f_h, fill=(255, 255, 0)); y += 110
            
            if not is_intro:
                y += 40
                for line in textwrap.wrap(desc, width=42)[:4]:
                    draw.text((80, y), line, font=f_d, fill=(230, 230, 230)); y += 70
            
            draw.text((320, 1820), "दैनिक आर्थिक समाचार", font=f_d, fill=(70, 70, 70))
        except: pass
        img.save("t.jpg")
        return ImageClip("t.jpg")

    # ५. अडियो र सिन सिङ्क
    # इन्ट्रो
    intro_txt = "नमस्ते, आजका आर्थिक समाचारहरूमा स्वागत छ।"
    await edge_tts.Communicate(intro_txt, "ne-NP-SagarNeural", rate="+7%", pitch="-5Hz").save("in.mp3")
    i_audio = AudioFileClip("in.mp3")
    final_clips.append(make_card("आर्थिक समाचार", "", is_intro=True).set_duration(i_audio.duration).set_audio(i_audio))

    # ६ समाचारहरू
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
    video.write_videofile(output, fps=24, codec="libx264", audio_codec="aac", bitrate="1500k", ffmpeg_params=["-pix_fmt", "yuv420p", "-crf", "28"])

    send_video_email(output, today)

def send_video_email(filepath, date):
    msg = MIMEMultipart(); msg['From'] = SENDER; msg['To'] = SENDER; msg['Subject'] = f"Economics Daily - {date}"
    with open(filepath, "rb") as f:
        part = MIMEBase('application', 'octet-stream'); part.set_payload(f.read()); encoders.encode_base64(part); part.add_header('Content-Disposition', f"attachment; filename= economics_video.mp4"); msg.attach(part)
    server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login(SENDER, PASSWORD); server.sendmail(SENDER, SENDER, msg.as_string()); server.quit()

if __name__ == "__main__":
    asyncio.run(run_clean_bulletin())
