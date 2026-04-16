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

async def run_viral_sports_system():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 Viral Sports System Started for {today}...")

    # १. न्युज संकलन
    combined_news = []
    sources = ["https://ekantipur.com/sports", "https://ratopati.com/category/sport", "https://setopati.com/khel", "https://www.hamrokhelkud.com/", "https://kathmandupost.com/sports"]
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
    news_context = "\n".join(list(set(combined_news)))

    # २. एआई विश्लेषण
    prompt = f"तिमी एक Viral TikTok Creator हौ। ५ मुख्य खेलकुद समाचार छान। हरेकको लागि १ कडा HOOK, १ Headline र १-२ वाक्य रोचक तथ्य देउ। फोटोको लागि Specific Keyword देउ। मलाई 'json' मा उत्तर देउ: {{'bulletin': [{{'hook': '...', 'headline': '...', 'info': '...', 'keyword': '...'}}]}} DATA: {news_context}"
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    m_res = requests.get(list_url).json()
    chosen_model = next((m['name'] for m in m_res.get('models', []) if "gemini-1.5-flash" in m['name']), m_res['models'][0]['name'])
    res = requests.post(f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={GEMINI_KEY}", json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"response_mime_type": "application/json"}})
    video_data = json.loads(res.json()['candidates'][0]['content']['parts'][0]['text'])

    # ३. फन्ट र भिडियो कार्ड
    os.system("wget -O font.ttf https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf")
    final_clips = []
    font_path = "font.ttf"

    def create_viral_frame(hook, headline, info, img_url, filename):
        r = requests.get(img_url, stream=True)
        img = Image.open(r.raw).convert('RGB').resize((1080, 1920))
        draw = ImageDraw.Draw(img)
        try:
            f_hook = ImageFont.truetype(font_path, 90); f_head = ImageFont.truetype(font_path, 70); f_info = ImageFont.truetype(font_path, 45)
            # Yellow Hook Box
            draw.rectangle([50, 200, 1030, 450], fill=(255, 230, 0))
            draw.text((80, 250), textwrap.fill(hook, width=18), font=f_hook, fill=(0, 0, 0))
            # Bottom Info Box
            draw.rectangle([0, 1400, 1080, 1800], fill=(0, 0, 0, 200))
            draw.text((60, 1450), textwrap.fill(headline, width=22), font=f_head, fill=(255, 255, 255))
            draw.text((60, 1600), textwrap.fill(info, width=40), font=f_info, fill=(200, 200, 200))
            draw.text((350, 1850), "दैनिक खेलकुद समाचार", font=f_info, fill=(255, 255, 0))
        except: pass
        img.save(filename)

    # ४. अडियो र सिन सिङ्क
    for i, item in enumerate(video_data['bulletin'][:5]):
        script = f"{item['hook']}. . . {item['headline']}. . . {item['info']}"
        v_file = f"v_{i}.mp3"
        await edge_tts.Communicate(script, "ne-NP-SagarNeural", rate="+12%", pitch="-2Hz").save(v_file)
        audio = AudioFileClip(v_file)
        # Image Fetch
        r_img = requests.get(f"https://api.pexels.com/v1/search?query={item['keyword']}&per_page=1&orientation=portrait", headers={"Authorization": PEXELS_KEY}).json()
        img_url = r_img['photos'][0]['src']['large2x'] if r_img.get('photos') else "https://images.pexels.com/photos/399187/pexels-photo-399187.jpeg"
        img_file = f"f_{i}.jpg"
        create_viral_frame(item['hook'], item['headline'], item['info'], img_url, img_file)
        # Zoom Effect
        clip = ImageClip(img_file).set_duration(audio.duration).set_audio(audio).resize(lambda t: 1 + 0.03 * t)
        final_clips.append(clip)

    # ५. EXPORT (With Strong Compression to stay under 25MB)
    print("🎬 Finalizing Compressed Viral Video...")
    video = concatenate_videoclips(final_clips, method="compose")
    output = "viral_sports_nepal.mp4"
    
    # मुख्य सुधार: bitrate र crf मिलाइएको छ ताकि साइज सानो होस्
    video.write_videofile(output, fps=24, codec="libx264", audio_codec="aac", 
                        bitrate="1200k", 
                        ffmpeg_params=["-pix_fmt", "yuv420p", "-crf", "28"])
    
    send_video_email(output, today)

def send_video_email(filepath, date):
    msg = MIMEMultipart(); msg['From'] = SENDER; msg['To'] = SENDER; msg['Subject'] = f"Viral Sports TikTok - {date}"
    with open(filepath, "rb") as f:
        part = MIMEBase('application', 'octet-stream'); part.set_payload(f.read()); encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= sports_news.mp4"); msg.attach(part)
    server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login(SENDER, PASSWORD); server.sendmail(SENDER, SENDER, msg.as_string()); server.quit()

if __name__ == "__main__":
    asyncio.run(run_viral_sports_system())
