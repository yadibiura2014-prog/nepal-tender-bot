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

async def run_viral_bulletin():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 Viral Economics Bulletin (6 News) Started for {today}...")

    # १. न्युज संकलन (Headline Only - For high stability)
    headlines_list = []
    sources = ["https://ekantipur.com/business", "https://kathmandupost.com/money", "https://setopati.com/kinmel", "https://ratopati.com/category/economy", "https://baarakhari.com/category/business", "https://www.sharesansar.com/category/latest-news", "https://www.nayapatrikadaily.com/category/11", "https://nagariknews.nagariknetwork.com/economy"]
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    for u in sources:
        try:
            r = requests.get(u, headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            for item in soup.find_all(['h1', 'h2', 'h3'])[:5]:
                txt = item.get_text().strip()
                if len(txt) > 25: headlines_list.append(txt)
        except: pass

    # डाटालाई एकदमै सानो बनाउने ताकी एआई क्र्यास नहोस्
    clean_news_input = "\n".join(list(set(headlines_list))[:15])

    # २. मोडेल अटो-डिटेक्ट
    print("🔍 चल्ने मोडेल खोज्दै...")
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    m_res = requests.get(list_url).json()
    models = [m['name'] for m in m_res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
    chosen_model = next((m for m in models if "gemini-1.5-flash" in m), models[0])

    # ३. एआई विश्लेषण (Fast Processing Prompt)
    prompt = f"""
    तिमी एक प्रतिष्ठित PhD Economic Analyst हौ। १५ वटा हेडलाइनबाट ६ वटा मात्र मुख्य समाचार छान। 
    नियम:
    १. 'COLD OPEN': भिडियोको सुरुमै आजको सबैभन्दा ठूलो समाचारलाई एउटा 'झड्का' लाग्ने गरी प्रस्तुत गर (जस्तै: 'सावधान!', 'इतिहासमै पहिलो पटक!')।
    २. मात्र ६ वटा समाचार। अङ्क र तथ्य अनिवार्य। भाषा ठेट नेपाली।
    मलाई यो 'json' मा उत्तर देउ: {{'hook_headline': '...', 'hook_details': '...', 'bulletin': [{{'num': '२', 'headline': '...', 'details': '...'}}], 'outro': '...'}}
    HEADLINES: {clean_news_input}
    """
    
    gen_url = f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={GEMINI_KEY}"
    
    data = None
    for attempt in range(5):
        try:
            res = requests.post(gen_url, json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"response_mime_type": "application/json"}}, timeout=30)
            res_json = res.json()
            if 'candidates' in res_json:
                data = json.loads(res_json['candidates'][0]['content']['parts'][0]['text'])
                break
            else:
                print(f"⚠️ एआई बिजी छ, फेरि कोसिस गर्दै... ({attempt+1})")
                time.sleep(25)
        except: time.sleep(25)

    if not data:
        print("❌ एआईले उत्तर दिएन।")
        return

    # ४. भिडियो कार्ड र फन्ट
    os.system("wget -O font.ttf https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf")
    font_path = "font.ttf"
    final_clips = []

    def make_card(num, headline, details, filename, is_hook=False):
        img = Image.new('RGB', (1080, 1920), color=(15, 15, 15))
        draw = ImageDraw.Draw(img)
        try:
            f_h = ImageFont.truetype(font_path, 95 if is_hook else 80)
            f_d = ImageFont.truetype(font_path, 45)
            y = 750 if is_hook else 820
            # Headline Wrap
            h_lines = textwrap.wrap(headline, width=20)
            for line in h_lines[:3]:
                draw.text((80, y), line, font=f_h, fill=(255, 255, 0)); y += 120
            # Details Wrap
            d_lines = textwrap.wrap(details, width=42)
            y += 40
            for line in d_lines[:3]:
                draw.text((80, y), line, font=f_d, fill=(240, 240, 240)); y += 70
            draw.text((320, 1820), "दैनिक आर्थिक समाचार", font=f_d, fill=(80, 80, 80))
        except: pass
        img.save(filename)

    # ५. अडियो-भिजुअल सिङ्क (Hook First)
    # Hook
    hook_text = f"{data['hook_headline']}. . . {data['hook_details']}"
    await edge_tts.Communicate(hook_text, "ne-NP-SagarNeural", rate="+10%", pitch="-5Hz").save("h.mp3")
    make_card("!", data['hook_headline'], data['hook_details'], "h.jpg", is_hook=True)
    final_clips.append(ImageClip("h.jpg").set_duration(AudioFileClip("h.mp3").duration).set_audio(AudioFileClip("h.mp3")))

    # Bulletin (News 2 to 6)
    for i, item in enumerate(data['bulletin']):
        text = f"{item['num']}. . . {item['headline']}. . . {item['details']}"
        v_file = f"v_{i}.mp3"
        await edge_tts.Communicate(text, "ne-NP-SagarNeural", rate="+10%", pitch="-5Hz").save(v_file)
        a_clip = AudioFileClip(v_file)
        img_file = f"f_{i}.jpg"
        make_card(item['num'], item['headline'], item['details'], img_file)
        final_clips.append(ImageClip(img_file).set_duration(a_clip.duration).set_audio(a_clip).resize(lambda t: 1 + 0.02 * t))

    # Outro
    await edge_tts.Communicate(data['outro'], "ne-NP-SagarNeural", rate="+7%", pitch="-5Hz").save("out.mp3")
    make_card("✓", "धन्यवाद", "हामीलाई पछ्याउँदै गर्नुहोला", "out.jpg")
    final_clips.append(ImageClip("out.jpg").set_duration(AudioFileClip("out.mp3").duration).set_audio(AudioFileClip("out.mp3")))

    # ६. एसेम्बल र सेभ
    video = concatenate_videoclips(final_clips, method="compose")
    output_file = "economics_final.mp4"
    video.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac", bitrate="1500k", ffmpeg_params=["-pix_fmt", "yuv420p", "-crf", "28"])

    send_video_email(output_file, today)

def send_video_email(filepath, date):
    msg = MIMEMultipart(); msg['From'] = SENDER; msg['To'] = SENDER; msg['Subject'] = f"Economics Daily Bulletin - {date}"
    with open(filepath, "rb") as f:
        part = MIMEBase('application', 'octet-stream'); part.set_payload(f.read()); encoders.encode_base64(part); part.add_header('Content-Disposition', f"attachment; filename= economics_video.mp4"); msg.attach(part)
    server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login(SENDER, PASSWORD); server.sendmail(SENDER, SENDER, msg.as_string()); server.quit()

if __name__ == "__main__":
    asyncio.run(run_viral_bulletin())
