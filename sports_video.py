import os, requests, json, time, asyncio, textwrap
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Compatibility fix
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
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
    print(f"🔥 Viral Sports System Started for {today}...")

    # STEP 1: NEWS EXTRACTION (8 Sources)
    combined_news = []
    sources = ["https://ekantipur.com/sports", "https://ratopati.com/category/sport", "https://setopati.com/khel", "https://baarakhari.com/category/sports", "https://www.hamrokhelkud.com/", "https://kathmandupost.com/sports", "https://www.nayapatrikadaily.com/category/9", "https://annapurnapost.com/category/sports"]
    
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

    # STEP 2 & 4: HEADLINE & SCRIPT GENERATION (Viral Style)
    prompt = f"""
    तिमी एक विश्वविख्यात Viral TikTok Content Creator हौ। उपलब्ध खेलकुद समाचारबाट टप ५ समाचार छान।
    
    नियमहरू:
    १. शैली: एकदमै 'Engaging', 'Shocking' र 'Emotional' हुनुपर्छ। (Traditional news tone निषेध छ)।
    २. संरचना: हरेक समाचारको सुरुमा एउटा कडा 'HOOK' चाहिन्छ।
    ३. भाषा: सरल र बोलिचालीको ठेट नेपाली।
    ४. फोटो खोज्नका लागि Pexels मा चल्ने एकदमै 'Specific Player/Action' कीवर्ड देउ।
    
    मलाई यो 'json' फर्म्याटमा मात्र उत्तर देउ:
    {{
      "bulletin": [
        {{
          "hook": "के तपाईँलाई थाहा छ सन्दीपले आज के गरे?",
          "headline": "सन्दीप लामिछानेको नयाँ कीर्तिमान!",
          "info": "नेपालका जादुमयी स्पिनर सन्दीपले विश्व क्रिकेटलाई नै स्तब्ध बनाउने गरि फेरि इतिहास रचेका छन्।",
          "keyword": "Sandeep Lamichhane cricket"
        }}
      ]
    }}
    DATA: {news_context}
    """
    
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    m_res = requests.get(list_url).json()
    chosen_model = next((m['name'] for m in m_res['models'] if "gemini-1.5-flash" in m['name']), m_res['models'][0]['name'])

    res = requests.post(f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={GEMINI_KEY}", 
                        json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"response_mime_type": "application/json"}})
    video_data = json.loads(res.json()['candidates'][0]['content']['parts'][0]['text'])

    # STEP 3 & 5: IMAGE HANDLING & VIDEO CREATION
    os.system("wget -O font.ttf https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf")
    final_clips = []
    font_path = "font.ttf"

    def create_viral_frame(hook, headline, info, img_url, filename):
        r = requests.get(img_url, stream=True)
        img = Image.open(r.raw).convert('RGB')
        
        # Smart Resize to 1080x1920
        target_w, target_h = 1080, 1920
        w, h = img.size
        aspect = w / h
        if aspect > (target_w/target_h):
            new_h = target_h; new_w = int(aspect * new_h)
            img = img.resize((new_w, new_h), Image.LANCZOS).crop(((new_w-target_w)/2, 0, (new_w+target_w)/2, target_h))
        else:
            new_w = target_w; new_h = int(new_w / aspect)
            img = img.resize((new_w, new_h), Image.LANCZOS).crop((0, (new_h-target_h)/2, target_w, (new_h+target_h)/2))

        draw = ImageDraw.Draw(img)
        try:
            f_hook = ImageFont.truetype(font_path, 90)
            f_head = ImageFont.truetype(font_path, 70)
            f_info = ImageFont.truetype(font_path, 45)

            # Draw Hook (Top - Bright Yellow Box)
            draw.rectangle([50, 200, 1030, 450], fill=(255, 230, 0))
            draw.text((80, 250), textwrap.fill(hook, width=18), font=f_hook, fill=(0, 0, 0))

            # Draw Subtitles/Info (Bottom - High Contrast)
            draw.rectangle([0, 1400, 1080, 1800], fill=(0, 0, 0, 200))
            draw.text((60, 1450), textwrap.fill(headline, width=22), font=f_head, fill=(255, 255, 255))
            draw.text((60, 1600), textwrap.fill(info, width=40), font=f_info, fill=(200, 200, 200))
            
            # Watermark
            draw.text((350, 1850), "दैनिक खेलकुद समाचार", font=f_info, fill=(255, 255, 0))
        except: pass
        img.save(filename)

    # VOICEOVER & SYNC
    for i, item in enumerate(video_data['bulletin'][:5]):
        print(f"🎬 Creating Scene {i+1}...")
        
        # Audio Script: Hook -> Pause -> Headline -> Pause -> Info
        script = f"{item['hook']}. . . {item['headline']}. . . {item['info']}"
        v_file = f"v_{i}.mp3"
        await edge_tts.Communicate(script, "ne-NP-SagarNeural", rate="+10%", pitch="-2Hz").save(v_file)
        audio = AudioFileClip(v_file)

        # Image Fetch (Pexels with specific keywords)
        kw = item['keyword']
        r_img = requests.get(f"https://api.pexels.com/v1/search?query={kw}&per_page=1&orientation=portrait", headers={"Authorization": PEXELS_KEY}).json()
        img_url = r_img['photos'][0]['src']['large2x'] if r_img.get('photos') else "https://images.pexels.com/photos/399187/pexels-photo-399187.jpeg"
        
        img_file = f"f_{i}.jpg"
        create_viral_frame(item['hook'], item['headline'], item['info'], img_url, img_file)
        
        # Clip with Smooth Zoom
        clip = ImageClip(img_file).set_duration(audio.duration).set_audio(audio)
        clip = clip.resize(lambda t: 1 + 0.04 * t).set_position('center')
        final_clips.append(clip)

    # EXPORT
    print("🎥 Finalizing Viral Video...")
    video = concatenate_videoclips(final_clips, method="compose")
    output = "viral_sports_nepal.mp4"
    video.write_videofile(output, fps=24, codec="libx264", audio_codec="aac", bitrate="2000k", ffmpeg_params=["-pix_fmt", "yuv420p", "-crf", "24"])
    
    send_video_email(output, today)

def send_video_email(filepath, date):
    msg = MIMEMultipart(); msg['From'] = SENDER; msg['To'] = SENDER; msg['Subject'] = f"Viral Sports TikTok - {date}"
    with open(filepath, "rb") as f:
        part = MIMEBase('application', 'octet-stream'); part.set_payload(f.read()); encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {filepath}"); msg.attach(part)
    server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login(SENDER, PASSWORD); server.sendmail(SENDER, SENDER, msg.as_string()); server.quit()

if __name__ == "__main__":
    asyncio.run(run_viral_sports_system())
