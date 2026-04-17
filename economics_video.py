import os, requests, json, time, asyncio, textwrap
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

# Pillow Compatibility Fix
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

async def run_viral_bulletin():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 Stable Economics Bulletin Started for {today}...")

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
    
    # अनावश्यक डाटा हटाएर सानो बनाउने (AI Stability को लागि)
    clean_input = "\n".join(list(set(headlines))[:15])

    # २. एआई विश्लेषण (Using Stable v1 API)
    # हामी सिधै gemini-1.5-flash मोडेल प्रयोग गर्छौं जुन सबैभन्दा छिटो छ
    gen_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    
    prompt = f"""
    तिमी एक प्रतिष्ठित Economic Analyst हौ। १५ वटा हेडलाइनबाट ६ वटा मुख्य समाचार छान। 
    नियम:
    १. 'COLD OPEN': भिडियोको सुरुमै आजको सबैभन्दा ठूलो समाचारलाई एउटा 'झड्का' लाग्ने गरी प्रस्तुत गर (जस्तै: 'सावधान!', 'इतिहासमै पहिलो पटक!')।
    २. सबै कुरा शुद्ध नेपालीमा लेख। अङ्ग्रेजी शब्द निषेध छ।
    ३. ढाँचा: १ Hook, त्यसपछि ६ वटा हेडलाइन (अङ्कसहित) र हरेकको १-१ वाक्यको ठोस तथ्य।
    मलाई यो 'json' मा उत्तर देउ: {{'hook_h': '...', 'hook_d': '...', 'bulletin': [{{'n': '१', 'h': '...', 'd': '...'}}], 'outro': '...'}}
    HEADLINES: {clean_input}
    """
    
    data = None
    for attempt in range(5):
        try:
            res = requests.post(gen_url, json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"response_mime_type": "application/json"}}, timeout=30)
            res_json = res.json()
            if 'candidates' in res_json:
                data = json.loads(res_json['candidates'][0]['content']['parts'][0]['text'])
                print(f"✅ एआईले स्क्रिप्ट तयार पार्यो! (कोसिस: {attempt+1})")
                break
            else:
                print(f"⚠️ एआई बिजी छ ({res.status_code}), फेरि कोसिस गर्दै... {attempt+1}")
                time.sleep(20)
        except: time.sleep(20)

    if not data:
        print("❌ एआईबाट जवाफ आएन।")
        return

    # ३. फन्ट र भिडियो कार्ड
    os.system("wget -O font.ttf https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf")
    font_path = "font.ttf"
    final_clips = []

    def make_card(title, desc, num="", is_hook=False):
        img = Image.new('RGB', (1080, 1920), color=(15, 15, 15))
        draw = ImageDraw.Draw(img)
        try:
            f_h = ImageFont.truetype(font_path, 95 if is_hook else 80)
            f_d = ImageFont.truetype(font_path, 45)
            # Headline
            y = 750 if is_hook else 820
            h_lines = textwrap.wrap(title, width=20)
            for line in h_lines[:3]:
                draw.text((80, y), line, font=f_h, fill=(255, 255, 0)); y += 120
            # Description
            d_lines = textwrap.wrap(desc, width=42)
            y += 40
            for line in d_lines[:3]:
                draw.text((80, y), line, font=f_d, fill=(230, 230, 230)); y += 70
            # Branding (No '0')
            draw.text((320, 1820), "दैनिक आर्थिक समाचार", font=f_d, fill=(80, 80, 80))
        except: pass
        img.save("temp.jpg")
        return ImageClip("temp.jpg")

    # ४. अडियो-भिजुअल सिङ्क
    print("🎙️ आवाज र सिनहरू जोडिँदैछ...")
    # Hook Scene
    h_txt = f"{data['hook_h']}. . . {data['hook_d']}"
    await edge_tts.Communicate(h_txt, "ne-NP-SagarNeural", rate="+10%", pitch="-5Hz").save("h.mp3")
    h_audio = AudioFileClip("h.mp3")
    final_clips.append(make_card(data['hook_h'], data['hook_d'], is_hook=True).set_duration(h_audio.duration).set_audio(h_audio))

    # Bulletin Scenes (News 1-6)
    for i, item in enumerate(data['bulletin']):
        txt = f"{item['n']}. . . {item['h']}. . . {item['d']}"
        v_file = f"v_{i}.mp3"
        await edge_tts.Communicate(txt, "ne-NP-SagarNeural", rate="+10%", pitch="-5Hz").save(v_file)
        a_clip = AudioFileClip(v_file)
        clip = make_card(item['h'], item['d'], num=item['n']).set_duration(a_clip.duration).set_audio(a_clip)
        final_clips.append(clip.resize(lambda t: 1 + 0.02 * t))

    # Outro
    await edge_tts.Communicate(data['outro'], "ne-NP-SagarNeural", rate="+7%", pitch="-5Hz").save("o.mp3")
    o_audio = AudioFileClip("o.mp3")
    final_clips.append(make_card("धन्यवाद", data['outro']).set_duration(o_audio.duration).set_audio(o_audio))

    # ५. एसेम्बल
    video = concatenate_videoclips(final_clips, method="compose")
    output = "economics_final.mp4"
    video.write_videofile(output, fps=24, codec="libx264", audio_codec="aac", bitrate="1500k", ffmpeg_params=["-pix_fmt", "yuv420p", "-crf", "28"])

    send_video_email(output, today)

def send_video_email(filepath, date):
    msg = MIMEMultipart(); msg['From'] = SENDER; msg['To'] = SENDER; msg['Subject'] = f"Economics Daily - {date}"
    with open(filepath, "rb") as f:
        part = MIMEBase('application', 'octet-stream'); part.set_payload(f.read()); encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= economics_video.mp4"); msg.attach(part)
    server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login(SENDER, PASSWORD); server.sendmail(SENDER, SENDER, msg.as_string()); server.quit()

if __name__ == "__main__":
    asyncio.run(run_viral_bulletin())
