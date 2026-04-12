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

# --- Secrets ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
PEXELS_KEY = os.getenv("PEXELS_KEY")
SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")

async def run_automated_bulletin():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 Economics Bulletin Started for {today}...")

    # १. ८ वटा पोर्टलबाट ताजा समाचार संकलन
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

    # २. मोडेल अटो-डिटेक्ट (Fix for 404/KeyError)
    print("🔍 उपलब्ध एआई मोडेल खोज्दै...")
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    m_res = requests.get(list_url).json()
    models = [m['name'] for m in m_res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
    chosen_model = next((m for m in models if "gemini-1.5-flash" in m), models[0])
    print(f"✅ मोडेल छानियो: {chosen_model}")

    prompt = f"""
    तिमी एक प्रतिष्ठित PhD Economic Analyst हौ। १३ वटा मुख्य समाचार छान। 
    नियम: १ हेडलाइन + १-२ वाक्यको थप तथ्य। अङ्क र तथ्याङ्क अनिवार्य हुनुपर्छ। 
    भिडियो ९० सेकेन्डको बनाउनुपर्ने भएकाले एकदमै छोटा र कडा वाक्य लेख।
    मलाई 'json' मा उत्तर देउ: {{'intro': '...', 'bulletin': [{{'headline': '...', 'details': '...'}}], 'outro': '...'}}
    DATA: {news_data}
    """
    
    gen_url = f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={GEMINI_KEY}"
    res = requests.post(gen_url, json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"response_mime_type": "application/json"}})
    
    data = json.loads(res.json()['candidates'][0]['content']['parts'][0]['text'])

    # ३. आवाज निर्माण (Sync Ready)
    final_clips = []
    # फन्ट डाउनलोड
    os.system("wget -O font.ttf https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf")
    font_path = "font.ttf"

    def make_bw_card(main_txt, sub_txt, filename):
        img = Image.new('RGB', (1080, 1920), color=(15, 15, 15))
        draw = ImageDraw.Draw(img)
        try:
            f_h = ImageFont.truetype(font_path, 80)
            f_p = ImageFont.truetype(font_path, 45)
            draw.text((80, 850), main_txt[:25], font=f_h, fill=(255, 255, 0)) # पहेलो
            draw.text((80, 960), main_txt[25:50], font=f_h, fill=(255, 255, 0))
            draw.text((80, 1150), sub_txt[:42], font=f_p, fill=(230, 230, 230))
            draw.text((80, 1220), sub_txt[42:85], font=f_p, fill=(230, 230, 230))
        except: pass
        img.save(filename)

    # इन्ट्रो क्लिप
    intro_txt = data['intro']
    await edge_tts.Communicate(intro_txt, "ne-NP-SagarNeural", rate="+8%", pitch="-5Hz").save("intro.mp3")
    make_bw_card("इकोनोमिक्स बुलेटिन", "आजका १३ मुख्य समाचारहरू", "intro.jpg")
    final_clips.append(ImageClip("intro.jpg").set_duration(AudioFileClip("intro.mp3").duration).set_audio(AudioFileClip("intro.mp3")))

    # समाचार क्लिपहरू (Perfect Sync)
    for i, item in enumerate(data['bulletin']):
        print(f"Processing scene {i+1}...")
        txt = f"{item['headline']}. . . {item['details']}"
        v_file = f"v_{i}.mp3"
        await edge_tts.Communicate(txt, "ne-NP-SagarNeural", rate="+10%", pitch="-5Hz").save(v_file)
        
        a_clip = AudioFileClip(v_file)
        img_file = f"f_{i}.jpg"
        make_bw_card(item['headline'], item['details'], img_file)
        
        clip = ImageClip(img_file).set_duration(a_clip.duration).set_audio(a_clip).resize(lambda t: 1 + 0.02 * t)
        final_clips.append(clip)

    # ४. भिडियो जोड्ने
    print("🎬 भिडियो एसेम्बल हुँदैछ...")
    video = concatenate_videoclips(final_clips, method="compose")
    video.write_videofile("economics_final.mp4", fps=24, codec="libx264", audio_codec="aac", ffmpeg_params=["-pix_fmt", "yuv420p"])

    # ५. ईमेल पठाउने
    send_video_email("economics_final.mp4", today)

def send_video_email(filepath, date):
    msg = MIMEMultipart()
    msg['From'] = SENDER
