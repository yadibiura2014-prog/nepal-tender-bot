import os, requests, json, time, asyncio
from bs4 import BeautifulSoup
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
import edge_tts
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# --- Keys from Environment ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
PEXELS_KEY = os.getenv("PEXELS_KEY") # तपाईँले यसलाई GitHub Secret मा थप्नुपर्छ
SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")

async def run_automated_bulletin():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 Economics Bulletin Started for {today}...")

    # १. ८ वटा पोर्टलबाट ताजा समाचार संकलन (Strict Accuracy)
    combined_news = []
    sources = ["https://ekantipur.com/business", "https://kathmandupost.com/money", "https://setopati.com/kinmel", "https://ratopati.com/category/economy", "https://baarakhari.com/category/business", "https://www.sharesansar.com/category/latest-news"]
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    for u in sources:
        try:
            r = requests.get(u, headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            for item in soup.find_all(['h2', 'h3'])[:6]:
                title = item.get_text().strip()
                p = item.find_next('p')
                snippet = p.get_text().strip() if p else ""
                if len(title) > 25: combined_news.append(f"Title: {title} | Details: {snippet}")
        except: pass

    news_data = "\n".join(list(set(combined_news)))

    # २. एआई पीएचडी विश्लेषण (Strict Fact-only Mode)
    prompt = f"तिमी एक PhD Economic Analyst हौ। आजका मुख्य १३ समाचार छान। नियम: १ हेडलाइन + १-२ वाक्यको थप ठोस तथ्य। अङ्क र डाटा अनिवार्य चाहिन्छ। पत्रिकाहरुमा जे छ त्यही मात्र लेख, आफ्नो मनले केही नथप। मलाई 'json' मा उत्तर देउ: {{'intro': '...', 'bulletin': [{{'headline': '...', 'details': '...'}}], 'outro': '...'}} DATA: {news_data}"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"response_mime_type": "application/json"}})
    data = json.loads(res.json()['candidates'][0]['content']['parts'][0]['text'])

    # ३. आवाज निर्माण (Ultra-Normal Tune)
    full_script = f"{data['intro']} . . . "
    for item in data['bulletin']:
        full_script += f"{item['headline']}. . . {item['details']} . . . "
    full_script += data['outro']
    
    await edge_tts.Communicate(full_script, "ne-NP-SagarNeural", rate="+10%", pitch="-5Hz").save("voice.mp3")
    audio = AudioFileClip("voice.mp3")

    # ४. भिडियो निर्माण
    final_clips = []
    # फन्ट डाउनलोड (GitHub को लागि)
    os.system("wget -O font.ttf https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf")
    
    duration_per = audio.duration / (len(data['bulletin']) + 2)

    def make_card(txt, filename):
        img = Image.new('RGB', (1080, 1920), color=(15, 15, 15))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("font.ttf", 75)
            draw.text((80, 850), txt[:25], font=font, fill=(255, 255, 0))
            draw.text((80, 950), txt[25:50], font=font, fill=(255, 255, 0))
        except: pass
        img.save(filename)

    # क्लिपहरू थप्ने
    make_card("ECONOMICS BULLETIN", "intro.jpg")
    final_clips.append(ImageClip("intro.jpg").set_duration(duration_per))

    for i, item in enumerate(data['bulletin']):
        name = f"f_{i}.jpg"
        make_card(item['headline'], name)
        final_clips.append(ImageClip(name).set_duration(duration_per).resize(lambda t: 1 + 0.02 * t))

    final_clips.append(ImageClip("intro.jpg").set_duration(duration_per))
    
    video = concatenate_videoclips(final_clips, method="compose").set_audio(audio)
    video.write_videofile("economics_video.mp4", fps=24, codec="libx264", audio_codec="aac", ffmpeg_params=["-pix_fmt", "yuv420p"])

    # ५. ईमेलमा भिडियो पठाउने
    send_video_email("economics_video.mp4", today)

def send_video_email(filepath, date):
    msg = MIMEMultipart()
    msg['From'] = SENDER
    msg['To'] = SENDER
    msg['Subject'] = f"Your Daily Economics Video - {date}"

    with open(filepath, "rb") as f:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {filepath}")
        msg.attach(part)

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(SENDER, PASSWORD)
    server.sendmail(SENDER, SENDER, msg.as_string())
    server.quit()

if __name__ == "__main__":
    asyncio.run(run_automated_bulletin())
