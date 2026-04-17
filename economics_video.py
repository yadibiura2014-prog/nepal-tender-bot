import os, requests, json, time, asyncio, textwrap, re
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
SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")

async def run_final_system():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 Starting Final Robust Process for {today}...")

    # १. न्युज संकलन (Headline Only)
    headlines = []
    sources = ["https://ekantipur.com/business", "https://kathmandupost.com/money", "https://setopati.com/kinmel", "https://ratopati.com/category/economy", "https://baarakhari.com/category/business", "https://www.sharesansar.com/category/latest-news"]
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    for u in sources:
        try:
            r = requests.get(u, headers=headers, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                for item in soup.find_all(['h1', 'h2', 'h3'])[:5]:
                    txt = item.get_text().strip()
                    if len(txt) > 25: headlines.append(txt)
        except: pass
    
    clean_input = "\n".join(list(set(headlines))[:15])

    # २. एआई विश्लेषण (Simple Text Response to avoid 400/KeyError)
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    
    prompt = f"""
    तिमी एक प्रतिष्ठित Economic Analyst हौ। १५ वटा हेडलाइनबाट ६ वटा मात्र मुख्य समाचार छान। 
    
    नियम:
    १. सुरुमा एउटा कडा 'Hook' हेडलाइन र विवरण लेख।
    २. त्यसपछि ५ वटा अन्य समाचार लेख। 
    ३. हरेक समाचार यसरी लेख: "नम्बर: [नम्बर] | हेडलाइन: [हेडलाइन] | विवरण: [१ वाक्यको तथ्य]"
    ४. सबै कुरा शुद्ध नेपालीमा लेख। अङ्ग्रेजी निषेध छ।
    
    HEADLINES: {clean_input}
    """

    data_text = ""
    for attempt in range(5):
        try:
            response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
            if response.status_code == 200:
                data_text = response.json()['candidates'][0]['content']['parts'][0]['text']
                print(f"✅ एआईले सफलतापूर्वक उत्तर दियो!")
                break
            else:
                print(f"⚠️ कोसिस गर्दै... {attempt+1}")
                time.sleep(20)
        except: time.sleep(20)

    if not data_text:
        print("❌ एआईबाट जवाफ आएन।")
        return

    # ३. एआईको उत्तरलाई टुक्रा पार्ने (Parsing)
    # हामी रेगुलर एक्सप्रेसन प्रयोग गरेर हेडलाइन र विवरण निकाल्छौँ
    scenes = []
    lines = data_text.split('\n')
    for line in lines:
        if '|' in line and 'हेडलाइन' in line:
            parts = line.split('|')
            h = parts[1].replace('हेडलाइन:', '').strip()
            d = parts[2].replace('विवरण:', '').strip()
            scenes.append({'h': h, 'd': d})

    if not scenes:
        print("❌ एआईको उत्तर बुझ्न सकिएन।")
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
    print("🎙️ आवाज र भिडियो सिङ्क हुँदैछ...")
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
    asyncio.run(run_final_system())
