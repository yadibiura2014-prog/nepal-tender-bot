import os, requests, json, time, asyncio, textwrap
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

# Pillow Fix for MoviePy
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

async def run_smart_bulletin():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 Starting Smart Economics Process for {today}...")

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
                    if len(txt) > 25: headlines.append(txt)
        except: pass
    clean_input = "\n".join(list(set(headlines))[:15])

    # २. एआई मोडेल अटो-डिटेक्ट (४०४ एरर सधैँका लागि हटाउन)
    print("🔍 तपाईँको एकाउन्टमा उपलब्ध मोडेल खोज्दै...")
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    try:
        m_res = requests.get(list_url).json()
        # 'generateContent' सपोर्ट गर्ने मोडेलहरुको लिस्ट बनाउने
        usable_models = [m['name'] for m in m_res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
        
        if not usable_models:
            print("❌ तपाईँको API Key मा कुनै मोडेल भेटिएन।")
            return
            
        # सबैभन्दा राम्रो मोडेल रोज्ने (Priority: Flash 1.5 > Pro > Flash 1.0)
        chosen_model = usable_models[0]
        for m in usable_models:
            if "gemini-1.5-flash" in m:
                chosen_model = m
                break
        print(f"✅ मोडेल फेला पर्यो र छानियो: {chosen_model}")
    except Exception as e:
        print(f"❌ मोडेल लिस्ट तान्न सकिएन: {e}")
        return

    # ३. एआई विश्लेषण
    prompt = f"""
    तिमी एक प्रतिष्ठित Economic Analyst हौ। आजको ६ वटा मुख्य आर्थिक समाचार छान। 
    नियम:
    १. पहिलो खबर 'झड्का' दिने हेडलाइन (Hook) हुनुपर्छ।
    २. सबै कुरा शुद्ध नेपालीमा लेख।
    ३. हरेक समाचार यो फर्म्याटमा लेख: "HEADLINE: [हेडलाइन] | DETAILS: [१ वाक्यको तथ्य]"
    HEADLINES: {clean_input}
    """

    gen_url = f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={GEMINI_KEY}"
    data_text = ""
    for attempt in range(5):
        try:
            res = requests.post(gen_url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
            if res.status_code == 200:
                data_text = res.json()['candidates'][0]['content']['parts'][0]['text']
                print(f"✅ एआईले सफलतापूर्वक स्क्रिप्ट दियो!")
                break
            else:
                print(f"⚠️ एआई व्यस्त (Attempt {attempt+1}): {res.text[:100]}")
                time.sleep(25)
        except: time.sleep(25)

    if not data_text:
        print("❌ एआईबाट जवाफ आएन।")
        return

    # ४. डाटा प्रोसेसिङ र भिडियो निर्माण
    scenes = []
    for line in data_text.split('\n'):
        if '|' in line and 'HEADLINE' in line:
            p = line.split('|')
            h = p[0].replace('HEADLINE:', '').strip()
            d = p[1].replace('DETAILS:', '').strip()
            scenes.append({'h': h, 'd': d})

    if not scenes:
        print("❌ एआईको उत्तर बुझ्न सकिएन।")
        return

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
    print("🎙️ भिडियो र अडियो सिङ्क हुँदैछ...")
    for i, sc in enumerate(scenes[:6]):
        txt = f"{i+1}. . . {sc['h']}. . . {sc['d']}"
        v_file = f"v_{i}.mp3"
        await edge_tts.Communicate(txt, "ne-NP-SagarNeural", rate="+10%", pitch="-5Hz").save(v_file)
        a_clip = AudioFileClip(v_file)
        clip = make_card(sc['h'], sc['d'], num=str(i+1)).set_duration(a_clip.duration).set_audio(a_clip)
        final_clips.append(clip.resize(lambda t: 1 + 0.02 * t))

    # ६. एक्सपोर्ट
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
    asyncio.run(run_smart_bulletin())
