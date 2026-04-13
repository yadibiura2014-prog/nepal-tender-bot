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

# --- Secrets ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")

async def run_automated_bulletin():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 Economics Bulletin Started for {today}...")

    # १. न्युज संकलन (All 8 Portals)
    combined_news = []
    sources = ["https://ekantipur.com/business", "https://kathmandupost.com/money", "https://setopati.com/kinmel", "https://ratopati.com/category/economy", "https://baarakhari.com/category/business", "https://www.sharesansar.com/category/latest-news", "https://www.nayapatrikadaily.com/category/11", "https://nagariknews.nagariknetwork.com/economy"]
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

    # २. एआई विश्लेषण (PhD Level & Pure Nepali)
    prompt = f"""
    तिमी एक प्रतिष्ठित PhD Economic Analyst हौ। आजको १३ मुख्य समाचार छान। 
    नियम: १ कडा हेडलाइन (अङ्क अनिवार्य) + १-२ वाक्यको थप तथ्य। 
    भाषा: शुद्ध र बौद्धिक नेपाली तर बुझ्न सजिलो। गल्ती नगर्नु।
    मलाई 'json' मा उत्तर देउ: {{'intro': '...', 'bulletin': [{{'headline': '...', 'details': '...'}}], 'outro': '...'}}
    DATA: {news_data}
    """
    
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    m_res = requests.get(list_url).json()
    usable = [m['name'] for m in m_res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
    chosen_model = next((m for m in usable if "gemini-1.5-flash" in m), usable[0])

    res = requests.post(f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={GEMINI_KEY}", 
                        json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"response_mime_type": "application/json"}})
    data = json.loads(res.json()['candidates'][0]['content']['parts'][0]['text'])

    # ३. भिडियो निर्माण र फन्ट सेटअप
    os.system("wget -O font.ttf https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf")
    font_path = "font.ttf"
    final_clips = []

    def make_professional_card(headline, details, filename):
        # १३ समाचारको लागि कालो-सेतो 'Elite' थिम
        img = Image.new('RGB', (1080, 1920), color=(12, 12, 12))
        draw = ImageDraw.Draw(img)
        try:
            # हेडलाइन र डिटेल्सको लागि फन्ट साइज
            font_h = ImageFont.truetype(font_path, 80)
            font_d = ImageFont.truetype(font_path, 45)
            
            # --- हेडलाइन र्‍यापिङ (Headline Wrapping) ---
            # शब्द नटुटाई २-३ लाइनमा हेडलाइन लेख्ने
            h_lines = textwrap.wrap(headline, width=20) # प्रति लाइन करिब २० अक्षर
            y_offset = 800
            for line in h_lines[:3]: # अधिकतम ३ लाइन हेडलाइन
                draw.text((80, y_offset), line, font=font_h, fill=(255, 255, 0)) # पहेलो
                y_offset += 110
            
            # --- डिटेल्स र्‍यापिङ (Details Wrapping) ---
            d_lines = textwrap.wrap(details, width=40)
            y_offset += 40 # ग्याप
            for line in d_lines[:4]: # अधिकतम ४ लाइन विवरण
                draw.text((80, y_offset), line, font=font_d, fill=(230, 230, 230)) # सेतो
                y_offset += 65
            
            # फुटर
            draw.text((380, 1750), "DAILY ECONOMICS BULLETIN", font=font_d, fill=(80, 80, 80))
        except Exception as e:
            print(f"Drawing Error: {e}")
        img.save(filename)

    # ४. इन्ट्रो र १३ समाचारको अडियो-भिजुअल सिङ्क
    print("🎙️ अडियो सिर्जना र सिङ्क हुँदैछ...")
    
    # इन्ट्रो
    await edge_tts.Communicate(data['intro'], "ne-NP-SagarNeural", rate="+7%", pitch="-5Hz").save("intro.mp3")
    i_audio = AudioFileClip("intro.mp3")
    make_professional_card("इकोनोमिक्स बुलेटिन", "आजका १३ मुख्य आर्थिक समाचार", "intro.jpg")
    final_clips.append(ImageClip("intro.jpg").set_duration(i_audio.duration).set_audio(i_audio))

    for i, item in enumerate(data['bulletin']):
        # आवाजलाई नेचुरल बनाउन हेडलाइन पछि डट-डट थपिएको छ
        text = f"{item['headline']}. . . {item['details']}"
        v_file = f"v_{i}.mp3"
        await edge_tts.Communicate(text, "ne-NP-SagarNeural", rate="+10%", pitch="-5Hz").save(v_file)
        
        a_clip = AudioFileClip(v_file)
        img_file = f"f_{i}.jpg"
        make_professional_card(item['headline'], item['details'], img_file)
        
        # सिङ्क गरिएको क्लिप
        clip = ImageClip(img_file).set_duration(a_clip.duration).set_audio(a_clip).resize(lambda t: 1 + 0.02 * t)
        final_clips.append(clip)

    # ५. भिडियो जोड्ने र ईमेल पठाउने
    print("🎬 भिडियो एसेम्बल हुँदैछ...")
    video = concatenate_videoclips(final_clips, method="compose")
    video.write_videofile("economics_pro_final.mp4", fps=24, codec="libx264", audio_codec="aac", ffmpeg_params=["-pix_fmt", "yuv420p"])

    send_video_email("economics_pro_final.mp4", today)

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
