import os, requests, json, time, asyncio, textwrap
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

# Compatibility fix for Pillow
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

async def run_stable_bulletin():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 Bulletproof Economics Process Started for {today}...")

    # १. न्युज संकलन (Headline Only - Ultra Light)
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

    # २. एआई विश्लेषण (Simpler API Call to avoid 400 error)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    
    prompt = f"""
    तिमी एक Economic Analyst हौ। आजको ६ वटा मुख्य आर्थिक समाचार छान।
    सुरुमा एउटा कडा 'झड्का' लाग्ने हेडलाइन (Hook) राख। त्यसपछि ६ वटा हेडलाइन (अङ्कसहित) र तथ्य देउ।
    सबै कुरा शुद्ध नेपालीमा लेख। अङ्ग्रेजी निषेध छ।
    मलाई यो 'json' ढाँचामा मात्र उत्तर देउ, अरु केही नलेख:
    {{
      "hook_h": "हेडलाइन", "hook_d": "विवरण",
      "bulletin": [ {{"n": "१", "h": "हेडलाइन", "d": "विवरण"}} ],
      "outro": "धन्यवाद।"
    }}
    HEADLINES: {clean_input}
    """

    data = None
    for attempt in range(5):
        try:
            response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
            if response.status_code == 200:
                # एआईको उत्तरबाट JSON मात्र निकाल्ने (Markdown सफा गर्ने)
                raw_res = response.json()['candidates'][0]['content']['parts'][0]['text']
                json_str = raw_res.replace('```json', '').replace('```', '').strip()
                data = json.loads(json_str)
                print(f"✅ एआई सफलता! (कोसिस: {attempt+1})")
                break
            else:
                print(f"⚠️ एआई व्यस्त (Error {response.status_code}), फेरि कोसिस गर्दै...")
                time.sleep(20)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(20)

    if not data:
        print("❌ एआईबाट डाटा आएन।")
        return

    # ३. फन्ट र भिडियो कार्ड
    os.system("wget -O font.ttf https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf")
    font_path = "font.ttf"
    final_clips = []

    def make_card(title, desc, num="", is_hook=False):
        img = Image.new('RGB', (1080, 1920), color=(15, 15, 15))
        draw = ImageDraw.Draw(img)
        try:
            f_h = ImageFont.truetype(font_path, 90 if is_hook else 75)
            f_d = ImageFont.truetype(font_path, 45)
            y = 750 if is_hook else 820
            h_lines = textwrap.wrap(title, width=22)
            for line in h_lines[:3]:
                draw.text((80, y), line, font=f_h, fill=(255, 255, 0)); y += 110
            d_lines = textwrap.wrap(desc, width=42)
            y += 40
            for line in d_lines[:3]:
                draw.text((80, y), line, font=f_d, fill=(230, 230, 230)); y += 70
            draw.text((320, 1820), "दैनिक आर्थिक समाचार", font=f_d, fill=(70, 70, 70))
        except: pass
        img.save("temp.jpg")
        return ImageClip("temp.jpg")

    # ४. अडियो-भिजुअल सिङ्क
    # Hook
    h_audio_file = "h.mp3"
    await edge_tts.Communicate(f"{data['hook_h']}. . . {data['hook_d']}", "ne-NP-SagarNeural", rate="+10%", pitch="-5Hz").save(h_audio_file)
    h_audio = AudioFileClip(h_audio_file)
    final_clips.append(make_card(data['hook_h'], data['hook_d'], is_hook=True).set_duration(h_audio.duration).set_audio(h_audio))

    # Bulletin
    for i, item in enumerate(data['bulletin'][:6]):
        v_txt = f"{item['n']}. . . {item['h']}. . . {item['d']}"
        v_file = f"v_{i}.mp3"
        await edge_tts.Communicate(v_txt, "ne-NP-SagarNeural", rate="+10%", pitch="-5Hz").save(v_file)
        a_clip = AudioFileClip(v_file)
        clip = make_card(item['h'], item['d'], num=item['n']).set_duration(a_clip.duration).set_audio(a_clip)
        final_clips.append(clip.resize(lambda t: 1 + 0.02 * t))

    # ५. एक्सपोर्ट
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
    asyncio.run(run_stable_bulletin())
