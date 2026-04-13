import os, requests, json, time, asyncio, textwrap
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

# Pillow र MoviePy बीचको प्रविधिक समस्या समाधान गर्ने लाइन
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import edge_tts
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# --- GitHub Secrets बाट कुञ्जीहरू तान्ने ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")

async def run_automated_bulletin():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 Economics Bulletin Started for {today}...")

    # १. ८ वटा मुख्य पोर्टलबाट ताजा समाचार संकलन
    combined_news = []
    sources = [
        "https://ekantipur.com/business", "https://kathmandupost.com/money",
        "https://setopati.com/kinmel", "https://ratopati.com/category/economy",
        "https://baarakhari.com/category/business", "https://www.sharesansar.com/category/latest-news",
        "https://www.nayapatrikadaily.com/category/11", "https://nagariknews.nagariknetwork.com/economy"
    ]
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

    # २. एआई विश्लेषण (PhD Level + १३ समाचार)
    prompt = f"""
    तिमी एक प्रतिष्ठित PhD Economic Analyst हौ। आजको १३ मुख्य समाचार छान। 
    नियम: १ कडा हेडलाइन (अङ्क अनिवार्य) + १-२ वाक्यको थप तथ्य (Relevant facts)। 
    भाषा: शुद्ध नेपाली। भिडियो ९० सेकेन्डको बनाउनु पर्ने भएकाले वाक्यहरु छोटा र कडा बनाऊ।
    मलाई यो 'json' मा उत्तर देउ: {{'intro': '...', 'bulletin': [{{'headline': '...', 'details': '...'}}], 'outro': '...'}}
    DATA: {news_data}
    """
    
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    m_res = requests.get(list_url).json()
    usable = [m['name'] for m in m_res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
    chosen_model = next((m for m in usable if "gemini-1.5-flash" in m), usable[0])

    res = requests.post(f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={GEMINI_KEY}", 
                        json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"response_mime_type": "application/json"}})
    data = json.loads(res.json()['candidates'][0]['content']['parts'][0]['text'])

    # ३. भिडियो र फन्ट सेटअप
    os.system("wget -O font.ttf https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf")
    font_path = "font.ttf"
    final_clips = []

    def make_pro_card(headline, details, filename):
        img = Image.new('RGB', (1080, 1920), color=(12, 12, 12))
        draw = ImageDraw.Draw(img)
        try:
            f_h = ImageFont.truetype(font_path, 80)
            f_d = ImageFont.truetype(font_path, 45)
            # हेडलाइन र्‍यापिङ (Headline Wrap)
            h_lines = textwrap.wrap(headline, width=22)
            y = 800
            for line in h_lines[:3]:
                draw.text((80, y), line, font=f_h, fill=(255, 255, 0)) # पहेलो हेडलाइन
                y += 110
            # विवरण र्‍यापिङ (Details Wrap)
            d_lines = textwrap.wrap(details, width=42)
            y += 40
            for line in d_lines[:4]:
                draw.text((80, y), line, font=f_d, fill=(230, 230, 230)) # सेतो विवरण
                y += 65
            draw.text((380, 1750), "DAILY ECONOMICS BULLETIN", font=f_d, fill=(80, 80, 80))
        except: pass
        img.save(filename)

    # ४. सिङ्क गरिएको अडियो-भिजुअल निर्माण
    # इन्ट्रो
    await edge_tts.Communicate(data['intro'], "ne-NP-SagarNeural", rate="+7%", pitch="-5Hz").save("intro.mp3")
    make_pro_card("इकोनोमिक्स बुलेटिन", "आजका मुख्य १३ समाचारहरू", "intro.jpg")
    final_clips.append(ImageClip("intro.jpg").set_duration(AudioFileClip("intro.mp3").duration).set_audio(AudioFileClip("intro.mp3")))

    # १३ वटा समाचार
    for i, item in enumerate(data['bulletin']):
        text = f"{item['headline']}. . . {item['details']}" # . . . ले एआईलाई थोरै रोकिन सिकाउँछ
        v_file = f"v_{i}.mp3"
        await edge_tts.Communicate(text, "ne-NP-SagarNeural", rate="+10%", pitch="-5Hz").save(v_file)
        
        a_clip = AudioFileClip(v_file)
        img_file = f"f_{i}.jpg"
        make_pro_card(item['headline'], item['details'], img_file)
        
        clip = ImageClip(img_file).set_duration(a_clip.duration).set_audio(a_clip).resize(lambda t: 1 + 0.02 * t)
        final_clips.append(clip)

    # ५. अन्तिम भिडियो निर्माण र कम्प्रेसन (साइज घटाउने)
    print("🎬 भिडियो एसेम्बल र कम्प्रेसन हुँदैछ...")
    video = concatenate_videoclips(final_clips, method="compose")
    output_file = "economics_final.mp4"
    
    video.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac",
                        bitrate="1500k", # भिडियो साइज सानो बनाउन
                        ffmpeg_params=["-pix_fmt", "yuv420p", "-crf", "28"])

    # ६. ईमेल पठाउने
    try:
        send_video_email(output_file, today)
        print("✅ ईमेल सफलतापूर्वक पठाइयो।")
    except Exception as e:
        print(f"❌ ईमेल पठाउन सकिएन: {e}")

def send_video_email(filepath, date):
    msg = MIMEMultipart()
    msg['From'] = SENDER
    msg['To'] = SENDER
    msg['Subject'] = f"Daily Economics Video - {date}"
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
