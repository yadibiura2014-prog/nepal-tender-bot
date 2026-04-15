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
    print(f"⚽ Sports Bulletin Started for {today}...")

    # १. न्युज संकलन (Major Sports Portals)
    combined_news = []
    sources = ["https://ekantipur.com/sports", "https://ratopati.com/category/sport", "https://setopati.com/khel", "https://baarakhari.com/category/sports", "https://www.hamrokhelkud.com/", "https://kathmandupost.com/sports"]
    headers = {'User-Agent': 'Mozilla/5.0'}
    for u in sources:
        try:
            r = requests.get(u, headers=headers, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                for item in soup.find_all(['h1', 'h2', 'h3'])[:6]:
                    title = item.get_text().strip()
                    if len(title) > 20: combined_news.append(title)
        except: pass

    news_data = "\n".join(list(set(combined_news)))

    # २. एआई विश्लेषण (Only 5 Headlines + Fast Facts)
    prompt = f"""
    तिमी एक प्रतिष्ठित स्पोर्ट्स एनालिस्ट हौ। आजका मुख्य ५ वटा 'खेलकुद समाचार' छान।
    नियम: १ हेडलाइन + १-२ वाक्यको थप तथ्य। कुल भिडियो १ मिनेट भित्र सकिनुपर्छ। 
    नेपालको खेललाई प्राथमिकता देउ। अङ्क र नतिजा अनिवार्य छ।
    मलाई 'json' मा उत्तर देउ: {{'intro': '...', 'bulletin': [{{'num': '१', 'headline': '...', 'details': '...', 'keyword': '...'}}], 'outro': '...'}}
    DATA: {news_data}
    """
    
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    m_res = requests.get(list_url).json()
    usable = [m['name'] for m in m_res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
    chosen_model = next((m for m in usable if "gemini-1.5-flash" in m), usable[0])

    res = requests.post(f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={GEMINI_KEY}", 
                        json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"response_mime_type": "application/json"}})
    data = json.loads(res.json()['candidates'][0]['content']['parts'][0]['text'])

    # ३. फन्ट र भिडियो कार्ड सेटअप
    os.system("wget -O font.ttf https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf")
    font_path = "font.ttf"
    final_clips = []

    def make_sports_card(num, headline, details, img_url, filename):
        img_raw = Image.open(requests.get(img_url, stream=True).raw).resize((1080, 1920))
        draw = ImageDraw.Draw(img_raw)
        try:
            f_n = ImageFont.truetype(font_path, 110); f_h = ImageFont.truetype(font_path, 80); f_d = ImageFont.truetype(font_path, 45); f_b = ImageFont.truetype(font_path, 40)
            draw.rectangle([0, 1300, 1080, 1750], fill=(0, 0, 0, 200))
            draw.text((60, 1320), f"{num}.", font=f_n, fill=(255, 255, 0))
            h_lines = textwrap.wrap(headline, width=22)
            y = 1440
            for line in h_lines[:2]:
                draw.text((60, y), line, font=f_h, fill=(255, 255, 255)); y += 100
            d_lines = textwrap.wrap(details, width=42)
            for line in d_lines[:2]:
                draw.text((60, y), line, font=f_d, fill=(210, 210, 210)); y += 60
            draw.text((320, 1820), "दैनिक खेलकुद समाचार", font=f_b, fill=(255, 255, 0))
        except: pass
        img_raw.save(filename)

    # ४. अडियो र सिन निर्माण (१ मिनेट टार्गेट)
    # इन्ट्रो
    intro_txt = "नमस्ते, दैनिक खेलकुद बुलेटिनमा स्वागत छ।"
    await edge_tts.Communicate(intro_txt, "ne-NP-SagarNeural", rate="+12%", pitch="-2Hz").save("in.mp3")
    r_in = requests.get(f"https://api.pexels.com/v1/search?query=football stadium&per_page=1&orientation=portrait", headers={"Authorization": PEXELS_KEY}).json()
    make_sports_card("0", "Khelkud Samachaar", "आजका ५ मुख्य समाचार", r_in['photos'][0]['src']['large2x'], "in.jpg")
    final_clips.append(ImageClip("in.jpg").set_duration(AudioFileClip("in.mp3").duration).set_audio(AudioFileClip("in.mp3")))

    for i, item in enumerate(data['bulletin']):
        text = f"{item['num']}. . . {item['headline']}. . . {item['details']}"
        v_file = f"v_{i}.mp3"
        await edge_tts.Communicate(text, "ne-NP-SagarNeural", rate="+15%", pitch="-2Hz").save(v_file)
        a_clip = AudioFileClip(v_file)
        
        kw = f"sports {item['keyword']}"
        r_img = requests.get(f"https://api.pexels.com/v1/search?query={kw}&per_page=1&orientation=portrait", headers={"Authorization": PEXELS_KEY}).json()
        img_url = r_img['photos'][0]['src']['large2x'] if 'photos' in r_img and len(r_img['photos']) > 0 else r_in['photos'][0]['src']['large2x']
        
        img_file = f"f_{i}.jpg"
        make_sports_card(item['num'], item['headline'], item['details'], img_url, img_file)
        clip = ImageClip(img_file).set_duration(a_clip.duration).set_audio(a_clip).resize(lambda t: 1 + 0.02 * t)
        final_clips.append(clip)

    # ५. आउट्रो र एसेम्बल
    await edge_tts.Communicate(data['outro'], "ne-NP-SagarNeural", rate="+10%").save("out.mp3")
    make_sports_card("✓", "धन्यवाद", "हामीलाई फलो गर्नुहोला", r_in['photos'][0]['src']['large2x'], "out.jpg")
    final_clips.append(ImageClip("out.jpg").set_duration(AudioFileClip("out.mp3").duration).set_audio(AudioFileClip("out.mp3")))

    video = concatenate_videoclips(final_clips, method="compose")
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
