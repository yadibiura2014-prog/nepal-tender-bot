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
SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")

async def run_automated_bulletin():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 Economics Bulletin Started for {today}...")

    # १. न्युज संकलन (Focus on Business sections)
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
                for item in soup.find_all(['h1', 'h2', 'h3'])[:8]:
                    title = item.get_text().strip()
                    if len(title) > 25: combined_news.append(title)
        except: pass

    news_data = "\n".join(list(set(combined_news)))

    # २. एआई विश्लेषण (Retry Logic + Automatic Model Discovery)
    print("🔍 चल्ने मोडेल खोज्दै र स्क्रिप्ट तयार पार्दै...")
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    m_res = requests.get(list_url).json()
    models = [m['name'] for m in m_res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
    chosen_model = next((m for m in models if "gemini-1.5-flash" in m), models[0])

    prompt = f"""
    तिमी एक प्रतिष्ठित PhD Economic Analyst हौ। आजको १३ मुख्य 'आर्थिक समाचार' छान।
    कार्यहरू:
    १. प्राथमिकता: सबैभन्दा महत्वपूर्ण समाचार (ब्याजदर, बजेट, ठूला निर्णय) लाई सुरुमा राख।
    २. इन्ट्रो (Intro): "नमस्ते, आजका प्रमुख आर्थिक समाचारहरूमा स्वागत छ।"
    ३. हरेक समाचारमा अङ्क र तथ्य अनिवार्य हुनुपर्छ। राजनीति वा अन्य समाचार निषेध छ।
    ४. स्क्रिप्ट ढाँचा: "[नम्बर] . . . [हेडलाइन] . . . [१-२ वाक्यको थप तथ्य]"।
    ५. विराम चिन्ह (,) र (.) को सही प्रयोग गर।
    मलाई यो 'json' मा उत्तर देउ: {{'intro': '...', 'bulletin': [{{'num': '१', 'headline': '...', 'details': '...'}}], 'outro': '...'}}
    DATA: {news_data}
    """
    
    gen_url = f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={GEMINI_KEY}"
    
    data = None
    for attempt in range(5):
        try:
            res = requests.post(gen_url, json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"response_mime_type": "application/json"}})
            res_json = res.json()
            if 'candidates' in res_json:
                data = json.loads(res_json['candidates'][0]['content']['parts'][0]['text'])
                break
            else:
                print(f"⚠️ एआई बिजी छ, फेरि कोसिस गर्दै... ({attempt+1})")
                time.sleep(20)
        except: pass

    if not data:
        print("❌ एआईले उत्तर दिन सकेन। ईमेल पठाइँदै छैन।")
        return

    # ३. भिडियो निर्माण र फन्ट
    os.system("wget -O font.ttf https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf")
    font_path = "font.ttf"
    final_clips = []

    def make_economics_card(num, headline, details, filename):
        img = Image.new('RGB', (1080, 1920), color=(15, 15, 15))
        draw = ImageDraw.Draw(img)
        try:
            f_n = ImageFont.truetype(font_path, 100) # Number
            f_h = ImageFont.truetype(font_path, 80)  # Headline
            f_d = ImageFont.truetype(font_path, 45)  # Details
            f_b = ImageFont.truetype(font_path, 40)  # Brand
            
            draw.text((80, 700), f"{num}.", font=f_n, fill=(255, 255, 0))
            h_lines = textwrap.wrap(headline, width=22)
            y = 820
            for line in h_lines[:3]:
                draw.text((80, y), line, font=f_h, fill=(255, 255, 0))
                y += 110
            d_lines = textwrap.wrap(details, width=42)
            y += 40
            for line in d_lines[:4]:
                draw.text((80, y), line, font=f_d, fill=(230, 230, 230))
                y += 65
            draw.text((320, 1820), "दैनिक आर्थिक समाचार", font=f_b, fill=(70, 70, 70))
            draw.text((380, 1750), "DAILY ECONOMICS BULLETIN", font=f_d, fill=(100, 100, 100))
        except: pass
        img.save(filename)

    # ४. सिङ्क गरिएको अडियो-भिजुअल निर्माण
    # इन्ट्रो
    await edge_tts.Communicate(data['intro'], "ne-NP-SagarNeural", rate="+7%", pitch="-5Hz").save("intro.mp3")
    make_economics_card("0", "Economic News", "आजका प्रमुख आर्थिक समाचारहरू", "intro.jpg")
    final_clips.append(ImageClip("intro.jpg").set_duration(AudioFileClip("intro.mp3").duration).set_audio(AudioFileClip("intro.mp3")))

    for i, item in enumerate(data['bulletin']):
        text = f"{item['num']}. . . {item['headline']}. . . {item['details']}"
        v_file = f"v_{i}.mp3"
        await edge_tts.Communicate(text, "ne-NP-SagarNeural", rate="+9%", pitch="-5Hz").save(v_file)
        a_clip = AudioFileClip(v_file)
        img_file = f"f_{i}.jpg"
        make_economics_card(item['num'], item['headline'], item['details'], img_file)
        clip = ImageClip(img_file).set_duration(a_clip.duration).set_audio(a_clip).resize(lambda t: 1 + 0.02 * t)
        final_clips.append(clip)

    # ५. आउट्रो
    await edge_tts.Communicate(data['outro'], "ne-NP-SagarNeural", rate="+7%").save("outro.mp3")
    make_economics_card("✓", "धन्यवाद", "हामीलाई पछ्याउँदै गर्नुहोला", "outro.jpg")
    final_clips.append(ImageClip("outro.jpg").set_duration(AudioFileClip("outro.mp3").duration).set_audio(AudioFileClip("outro.mp3")))

    # ६. एसेम्बल र सेभ
    video = concatenate_videoclips(final_clips, method="compose")
    output_file = "economics_final.mp4"
    video.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac", bitrate="1500k", ffmpeg_params=["-pix_fmt", "yuv420p", "-crf", "28"])

    send_video_email(output_file, today)

def send_video_email(filepath, date):
    msg = MIMEMultipart()
    msg['From'] = SENDER
    msg['To'] = SENDER
    msg['Subject'] = f"Economics Daily Bulletin - {date}"
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
