import os, requests, json, time, asyncio, textwrap
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

# Compatibility fix for Pillow/MoviePy
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import edge_tts
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# --- Secrets from GitHub ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
PEXELS_KEY = os.getenv("PEXELS_KEY")
SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")

async def run_sports_bulletin():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"⚽ Sports Bulletin Started for {today}...")

    # १. न्युज संकलन
    combined_news = []
    sources = ["https://ekantipur.com/sports", "https://ratopati.com/category/sport", "https://setopati.com/khel", "https://www.hamrokhelkud.com/", "https://baarakhari.com/category/sports"]
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for u in sources:
        try:
            r = requests.get(u, headers=headers, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                for item in soup.find_all(['h1', 'h2', 'h3'])[:6]:
                    title = item.get_text().strip()
                    if len(title) > 25: combined_news.append(title)
        except: pass

    news_data = "\n".join(list(set(combined_news)))

    # २. मोडेल र एआई विश्लेषण
    print("🔍 मोडेल खोज्दै...")
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    m_res = requests.get(list_url).json()
    models = [m['name'] for m in m_res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
    chosen_model = next((m for m in models if "gemini-1.5-flash" in m), models[0])

    prompt = f"""
    तिमी प्रतिष्ठित स्पोर्ट्स एनालिस्ट हौ। आजका मुख्य ५ समाचार छान।
    नियम: १ हेडलाइन + १-२ वाक्य तथ्य (अङ्क अनिवार्य)। भिडियो १ मिनेटको बनाउनु पर्ने भएकाले वाक्य छोटो बनाऊ।
    मलाई 'json' मा उत्तर देउ: {{'intro': '...', 'bulletin': [{{'num': '१', 'headline': '...', 'details': '...', 'keyword': '...'}}], 'outro': '...'}}
    DATA: {news_data}
    """
    
    gen_url = f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={GEMINI_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"response_mime_type": "application/json"}}

    # Retry Logic (Symmetry fix)
    data = None
    for attempt in range(5):
        try:
            res = requests.post(gen_url, json=payload)
            res_json = res.json()
            if 'candidates' in res_json:
                data = json.loads(res_json['candidates'][0]['content']['parts'][0]['text'])
                break
            else:
                print(f"⚠️ वेटिङ... ({attempt+1})")
                time.sleep(20)
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(20)

    if not data:
        print("❌ एआईले उत्तर दिएन।")
        return

    # ३. भिडियो निर्माण र फन्ट
    os.system("wget -O font.ttf https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf")
    font_path = "font.ttf"
    final_clips = []

    def make_sports_card(num, headline, details, img_url, filename):
        r = requests.get(img_url, stream=True)
        img_raw = Image.open(r.raw).convert('RGB').resize((1080, 1920))
        draw = ImageDraw.Draw(img_raw)
        try:
            f_n = ImageFont.truetype(font_path, 110); f_h = ImageFont.truetype(font_path, 80); f_d = ImageFont.truetype(font_path, 45)
            draw.rectangle([0, 1300, 1080, 1750], fill=(0, 0, 0, 210))
            draw.text((60, 1320), f"{num}.", font=f_n, fill=(255, 255, 0))
            h_lines = textwrap.wrap(headline, width=22)
            y = 1440
            for line in h_lines[:2]:
                draw.text((60, y), line, font=f_h, fill=(255, 255, 255)); y += 100
            d_lines = textwrap.wrap(details, width=42)
            for line in d_lines[:2]:
                draw.text((60, y), line, font=f_d, fill=(210, 210, 210)); y += 60
            draw.text((320, 1820), "दैनिक खेलकुद समाचार", font=f_d, fill=(255, 255, 0))
        except: pass
        img_raw.save(filename)

    # ४. अडियो-भिजुअल सिङ्क
    await edge_tts.Communicate(data['intro'], "ne-NP-SagarNeural", rate="+12%", pitch="-2Hz").save("in.mp3")
    i_audio = AudioFileClip("in.mp3")
    intro_img = "https://images.pexels.com/photos/399187/pexels-photo-399187.jpeg?auto=compress&cs=tinysrgb&w=1080&h=1920"
    make_sports_card("0", "Sports News", "आजका ५ मुख्य समाचार", intro_img, "in.jpg")
    final_clips.append(ImageClip("in.jpg").set_duration(i_audio.duration).set_audio(i_audio))

    for i, item in enumerate(data['bulletin']):
        text = f"{item['num']}. . . {item['headline']}. . . {item['details']}"
        v_file = f"v_{i}.mp3"
        await edge_tts.Communicate(text, "ne-NP-SagarNeural", rate="+15%", pitch="-2Hz").save(v_file)
        a_clip = AudioFileClip(v_file)
        
        kw = f"sports {item['keyword']}"
        r_img = requests.get(f"https://api.pexels.com/v1/search?query={kw}&per_page=1&orientation=portrait", headers={"Authorization": PEXELS_KEY}).json()
        img_url = r_img['photos'][0]['src']['large2x'] if 'photos' in r_img and len(r_img['photos']) > 0 else intro_img
        
        img_file = f"f_{i}.jpg"
        make_sports_card(item['num'], item['headline'], item['details'], img_url, img_file)
        final_clips.append(ImageClip(img_file).set_duration(a_clip.duration).set_audio(a_clip))

    await edge_tts.Communicate(data['outro'], "ne-NP-SagarNeural", rate="+10%").save("out.mp3")
    o_audio = AudioFileClip("out.mp3")
    make_sports_card("✓", "धन्यवाद", "हामीलाई पछ्याउँदै गर्नुहोला", intro_img, "out.jpg")
    final_clips.append(ImageClip("out.jpg").set_duration(o_audio.duration).set_audio(o_audio))

    # ५. एसेम्बल र ईमेल
    video = concatenate_videoclips(final_clips, method="chain")
    video.write_videofile("sports_final.mp4", fps=24, codec="libx264", audio_codec="aac", bitrate="1500k", ffmpeg_params=["-pix_fmt", "yuv420p", "-crf", "28"])
    send_video_email("sports_final.mp4", today)

def send_video_email(filepath, date):
    msg = MIMEMultipart(); msg['From'] = SENDER; msg['To'] = SENDER; msg['Subject'] = f"Daily Sports Video - {date}"
    with open(filepath, "rb") as f:
        part = MIMEBase('application', 'octet-stream'); part.set_payload(f.read()); encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= sports_news.mp4"); msg.attach(part)
    server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login(SENDER, PASSWORD); server.sendmail(SENDER, SENDER, msg.as_string()); server.quit()

if __name__ == "__main__":
    asyncio.run(run_sports_bulletin())
