import os, requests, json, time, asyncio
from bs4 import BeautifulSoup
from PIL import Image

# ERROR FIX: Monkey patch for MoviePy/Pillow compatibility
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import ImageDraw, ImageFont
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

async def run_automated_bulletin():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 Economics Bulletin Started for {today}...")

    # १. न्युज संकलन
    combined_news = []
    sources = ["https://ekantipur.com/business", "https://kathmandupost.com/money", "https://setopati.com/kinmel", "https://ratopati.com/category/economy", "https://baarakhari.com/category/business", "https://www.sharesansar.com/category/latest-news"]
    headers = {'User-Agent': 'Mozilla/5.0'}
    for u in sources:
        try:
            r = requests.get(u, headers=headers, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                for item in soup.find_all(['h1', 'h2', 'h3'])[:5]:
                    title = item.get_text().strip()
                    if len(title) > 25: combined_news.append(title)
        except: pass

    news_data = "\n".join(list(set(combined_news)))

    # २. एआई विश्लेषण
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    m_res = requests.get(list_url).json()
    models = [m['name'] for m in m_res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
    chosen_model = next((m for m in models if "gemini-1.5-flash" in m), models[0])

    prompt = f"तिमी PhD Economic Analyst हौ। १३ मुख्य समाचार छान। नियम: १ हेडलाइन + १-२ वाक्य तथ्य (अङ्क अनिवार्य)। ९० सेकेन्डको भिडियो बनाउनु छ। मलाई 'json' मा उत्तर देउ: {{'intro': '...', 'bulletin': [{{'headline': '...', 'details': '...'}}], 'outro': '...'}} DATA: {news_data}"
    
    gen_url = f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={GEMINI_KEY}"
    res = requests.post(gen_url, json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"response_mime_type": "application/json"}})
    data = json.loads(res.json()['candidates'][0]['content']['parts'][0]['text'])

    # ३. भिडियो निर्माण
    final_clips = []
    os.system("wget -O font.ttf https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf")
    
    # इन्ट्रो आवाज
    await edge_tts.Communicate(data['intro'], "ne-NP-SagarNeural", rate="+8%", pitch="-5Hz").save("intro.mp3")
    i_audio = AudioFileClip("intro.mp3")
    
    def make_card(txt, filename):
        img = Image.new('RGB', (1080, 1920), color=(15, 15, 15))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("font.ttf", 75)
            draw.text((80, 850), txt[:25], font=font, fill=(255, 255, 0))
            draw.text((80, 950), txt[25:50], font=font, fill=(255, 255, 0))
        except: pass
        img.save(filename)

    make_card("इकोनोमिक्स बुलेटिन", "intro.jpg")
    final_clips.append(ImageClip("intro.jpg").set_duration(i_audio.duration).set_audio(i_audio))

    for i, item in enumerate(data['bulletin']):
        txt = f"{item['headline']}. {item['details']}"
        v_file = f"v_{i}.mp3"
        await edge_tts.Communicate(txt, "ne-NP-SagarNeural", rate="+12%", pitch="-5Hz").save(v_file)
        a_clip = AudioFileClip(v_file)
        img_file = f"f_{i}.jpg"
        make_card(item['headline'], img_file)
        final_clips.append(ImageClip(img_file).set_duration(a_clip.duration).set_audio(a_clip).resize(lambda t: 1 + 0.02 * t))

    # ४. जोड्ने र सेभ गर्ने
    video = concatenate_videoclips(final_clips, method="compose")
    video.write_videofile("economics_final.mp4", fps=24, codec="libx264", audio_codec="aac", ffmpeg_params=["-pix_fmt", "yuv420p"])

    send_video_email("economics_final.mp4", today)

def send_video_email(filepath, date):
    msg = MIMEMultipart()
    msg['From'] = SENDER
    msg['To'] = SENDER
    msg['Subject'] = f"Daily Economics Video - {date}"
    with open(filepath, "rb") as f:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= economics_video.mp4")
        msg.attach(part)
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(SENDER, PASSWORD)
    server.sendmail(SENDER, SENDER, msg.as_string())
    server.quit()

if __name__ == "__main__":
    asyncio.run(run_automated_bulletin())
