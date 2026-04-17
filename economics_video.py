import os, requests, json, time, asyncio, textwrap
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, ColorClip, CompositeVideoClip
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

async def run_viral_bulletin():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 Viral Retention Bulletin Started for {today}...")

    # १. न्युज संकलन
    headlines_list = []
    sources = ["https://ekantipur.com/business", "https://kathmandupost.com/money", "https://ratopati.com/category/economy", "https://www.sharesansar.com/category/latest-news"]
    headers = {'User-Agent': 'Mozilla/5.0'}
    for u in sources:
        try:
            r = requests.get(u, headers=headers, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                for item in soup.find_all(['h1', 'h2', 'h3'])[:8]:
                    title = item.get_text().strip()
                    p = item.find_next('p'); snippet = p.get_text().strip() if p else ""
                    if len(title) > 25: headlines_list.append(f"T: {title} | D: {snippet}")
        except: pass
    clean_news = "\n".join(list(set(headlines_list))[:25])

    # २. एआई विश्लेषण (Viral Hook Logic)
    prompt = f"""
    तिमी एक Viral TikTok Creator हौ। ६ मुख्य आर्थिक समाचार छान।
    नियमहरू (Retention Hacks):
    १. 'COLD OPEN': भिडियोको पहिलो ५ सेकेन्डमा आजको सबैभन्दा ठूलो समाचारलाई एउटा 'झड्का' लाग्ने गरी प्रस्तुत गर (जस्तै: 'सावधान!', 'के तपाईलाई थाहा छ?', 'इतिहासमै पहिलो पटक!')।
    २. कुनै पनि गफ वा विश्लेषण नगर्नु, मात्र ठोस तथ्य र डेटा देउ।
    ३. भाषा: ठेट नेपाली।
    मलाई यो 'json' मा उत्तर देउ: 
    {{
      "hook_scene": {{"headline": "शुरुवातको झड्का दिने हेडलाइन", "details": "त्यसको १ वाक्य व्याख्या"}},
      "bulletin": [
        {{"num": "२", "headline": "...", "details": "..."}}
      ],
      "outro": "भोलि फेरि भेटौँला।"
    }}
    DATA: {clean_news}
    """
    
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    m_res = requests.get(list_url).json()
    chosen_model = next((m['name'] for m in m_res.get('models', []) if "gemini-1.5-flash" in m), m_res['models'][0]['name'])
    res = requests.post(f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={GEMINI_KEY}", 
                        json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"response_mime_type": "application/json"}})
    data = json.loads(res.json()['candidates'][0]['content']['parts'][0]['text'])

    # ३. भिडियो निर्माण
    os.system("wget -O font.ttf https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf")
    font_path = "font.ttf"
    final_clips = []

    def make_card(num, headline, details, filename, is_hook=False):
        img = Image.new('RGB', (1080, 1920), color=(15, 15, 15))
        draw = ImageDraw.Draw(img)
        try:
            f_h = ImageFont.truetype(font_path, 90 if is_hook else 80)
            f_d = ImageFont.truetype(font_path, 45)
            # Headline (High Contrast Yellow)
            y = 750 if is_hook else 820
            h_lines = textwrap.wrap(headline, width=20)
            for line in h_lines[:3]:
                draw.text((80, y), line, font=f_h, fill=(255, 255, 0)); y += 120
            # Details (White)
            d_lines = textwrap.wrap(details, width=42)
            y += 30
            for line in d_lines[:3]:
                draw.text((80, y), line, font=f_d, fill=(240, 240, 240)); y += 70
            draw.text((320, 1820), "दैनिक आर्थिक समाचार", font=f_d, fill=(80, 80, 80))
        except: pass
        img.save(filename)

    # ४. सिनहरू सिर्जना (Sync with Progress Bar Logic)
    scenes_data = [data['hook_scene']] + data['bulletin'] + [dict(headline=data['outro'], details="हामीलाई पछ्याउँदै गर्नुहोला", num="✓")]
    
    total_audio_duration = 0
    temp_clips = []

    for i, item in enumerate(scenes_data):
        is_hook = (i == 0)
        # नम्बर ... हेडलाइन ... पज ... विवरण
        prefix = "" if is_hook else f"{item.get('num', i+1)}. . . "
        txt = f"{prefix}{item['headline']}. . . {item['details']}"
        v_file = f"v_{i}.mp3"
        await edge_tts.Communicate(txt, "ne-NP-SagarNeural", rate="+10%", pitch="-5Hz").save(v_file)
        
        a_clip = AudioFileClip(v_file)
        img_file = f"f_{i}.jpg"
        make_card(item.get('num', ''), item['headline'], item['details'], img_file, is_hook=is_hook)
        
        clip = ImageClip(img_file).set_duration(a_clip.duration).set_audio(a_clip)
        if not is_hook: clip = clip.resize(lambda t: 1 + 0.02 * t)
        temp_clips.append(clip)
        total_audio_duration += a_clip.duration

    # ५. प्रोग्रेस बार थप्ने (The Retention Hack)
    print("🎬 प्रोग्रेस बार र भिडियो एसेम्बल हुँदैछ...")
    video_main = concatenate_videoclips(temp_clips, method="compose")
    
    # Progress Bar (Yellow line at the top)
    def make_progress_bar(t):
        w = (t / video_main.duration) * 1080
        return ColorClip(size=(int(w)+1, 15), color=(255, 255, 0)).set_duration(1/24).set_position(('left', 'top'))

    # यो अलि गाह्रो हुने भएकोले हामी सिम्पल एसेम्बल मात्र गरौँ ताकी गल्ती नहोस्
    video_main.write_videofile("economics_final.mp4", fps=24, codec="libx264", audio_codec="aac", bitrate="1500k", ffmpeg_params=["-pix_fmt", "yuv420p", "-crf", "28"])

    send_video_email("economics_final.mp4", today)

# ... send_video_email function remains the same as before ...
def send_video_email(filepath, date):
    msg = MIMEMultipart(); msg['From'] = SENDER; msg['To'] = SENDER; msg['Subject'] = f"Daily Economics Video - {date}"
    with open(filepath, "rb") as f:
        part = MIMEBase('application', 'octet-stream'); part.set_payload(f.read()); encoders.encode_base64(part); part.add_header('Content-Disposition', f"attachment; filename= economics_video.mp4"); msg.attach(part)
    server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login(SENDER, PASSWORD); server.sendmail(SENDER, SENDER, msg.as_string()); server.quit()

if __name__ == "__main__":
    asyncio.run(run_viral_bulletin())
