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
SENDER = os.getenv("EMAIL_SENDER")
PASSWORD = os.getenv("EMAIL_PASSWORD")

async def run_automated_bulletin():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 Economics Bulletin Started for {today} (6 News Edition)...")

    # १. ८ वटा पोर्टलबाट ताजा समाचार संकलन
    combined_news = []
    sources = ["https://ekantipur.com/business", "https://kathmandupost.com/money", "https://setopati.com/kinmel", "https://ratopati.com/category/economy", "https://baarakhari.com/category/business", "https://www.sharesansar.com/category/latest-news", "https://www.nayapatrikadaily.com/category/11", "https://nagariknews.nagariknetwork.com/economy"]
    headers = {'User-Agent': 'Mozilla/5.0'}
    for u in sources:
        try:
            r = requests.get(u, headers=headers, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                for item in soup.find_all(['h1', 'h2', 'h3'])[:8]:
                    title = item.get_text().strip()
                    p = item.find_next('p')
                    snippet = p.get_text().strip() if p else ""
                    if len(title) > 20: combined_news.append(f"Title: {title} | Snippet: {snippet}")
        except: pass

    news_data = "\n".join(list(set(combined_news)))

    # २. एआई विश्लेषण (Strictly 6 News + Priority Ranking)
    prompt = f"""
    तिमी एक प्रतिष्ठित PhD Economic Analyst हौ। आजको ६ वटा मुख्य 'आर्थिक समाचार' छान। 
    
    नियमहरू:
    १. प्राथमिकता: सबैभन्दा महत्वपूर्ण ६ वटा समाचार मात्र छान।
    २. इन्ट्रो: "नमस्ते, आजका प्रमुख आर्थिक समाचारहरूमा स्वागत छ।"
    ३. हरेक समाचारमा अङ्क र तथ्य अनिवार्य हुनुपर्छ। 
    ४. शैली: पहिले नम्बर भन, त्यसपछि १ हेडलाइन, त्यसपछि २ वाक्यको गहिरो तथ्यगत जानकारी।
    
    मलाई यो 'json' मा उत्तर देउ:
    {{
      "intro": "नमस्ते, आजका प्रमुख आर्थिक समाचारहरूमा स्वागत छ।",
      "bulletin": [ {{ "num": "१", "headline": "हेडलाइन", "details": "तथ्यगत जानकारी" }} ],
      "outro": "आजका लागि मुख्य आर्थिक खबर यति नै। भोलि फेरि भेटौँला, नमस्कार।"
    }}
    DATA: {news_data}
    """
    
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    m_res = requests.get(list_url).json()
    usable = [m['name'] for m in m_res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
    chosen_model = next((m for m in usable if "gemini-1.5-flash" in m), usable[0])

    res = requests.post(f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={GEMINI_KEY}", 
                        json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"response_mime_type": "application/json"}})
    data = json.loads(res.json()['candidates'][0]['content']['parts'][0]['text'])

    # ३. भिडियो निर्माण र फन्ट
    os.system("wget -O font.ttf https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf")
    font_path = "font.ttf"
    final_clips = []

    def make_economics_card(num, headline, details, filename, is_intro=False):
        img = Image.new('RGB', (1080, 1920), color=(15, 15, 15))
        draw = ImageDraw.Draw(img)
        try:
            f_n = ImageFont.truetype(font_path, 110); f_h = ImageFont.truetype(font_path, 80); f_d = ImageFont.truetype(font_path, 45); f_b = ImageFont.truetype(font_path, 40)
            
            if is_intro:
                draw.text((150, 900), headline, font=f_h, fill=(255, 255, 0))
                draw.text((250, 1050), "दैनिक आर्थिक बुलेटिन", font=f_d, fill=(200, 200, 200))
            else:
                # नम्बर लेख्ने
                draw.text((80, 700), f"{num}.", font=f_n, fill=(255, 255, 0))
                # हेडलाइन र्‍यापिङ
                h_lines = textwrap.wrap(headline, width=22)
                y = 820
                for line in h_lines[:3]:
                    draw.text((80, y), line, font=f_h, fill=(255, 255, 0)); y += 110
                # विवरण र्‍यापिङ
                d_lines = textwrap.wrap(details, width=42)
                y += 40
                for line in d_lines[:4]:
                    draw.text((80, y), line, font=f_d, fill=(230, 230, 230)); y += 65
                
            draw.text((320, 1820), "दैनिक आर्थिक समाचार", font=f_b, fill=(70, 70, 70))
        except: pass
        img.save(filename)

    # ४. अडियो-भिजुअल सिङ्क (NotebookLM Style)
    # १. इन्ट्रो (Removed leading "0")
    await edge_tts.Communicate(data['intro'], "ne-NP-SagarNeural", rate="+7%", pitch="-5Hz").save("intro.mp3")
    make_economics_card("", "आर्थिक समाचार", "", "intro.jpg", is_intro=True)
    final_clips.append(ImageClip("intro.jpg").set_duration(AudioFileClip("intro.mp3").duration).set_audio(AudioFileClip("intro.mp3")))

    # २. ६ समाचारहरू
    for i, item in enumerate(data['bulletin'][:6]):
        print(f"Syncing News {i+1}...")
        text = f"{item['num']}. . . {item['headline']}. . . {item['details']}"
        v_file = f"v_{i}.mp3"
        await edge_tts.Communicate(text, "ne-NP-SagarNeural", rate="+9%", pitch="-5Hz").save(v_file)
        
        a_clip = AudioFileClip(v_file)
        img_file = f"f_{i}.jpg"
        make_economics_card(item['num'], item['headline'], item['details'], img_file)
        
        clip = ImageClip(img_file).set_duration(a_clip.duration).set_audio(a_clip).resize(lambda t: 1 + 0.02 * t)
        final_clips.append(clip)

    # ३. आउट्रो
    await edge_tts.Communicate(data['outro'], "ne-NP-SagarNeural", rate="+7%", pitch="-5Hz").save("outro.mp3")
    make_economics_card("", "धन्यवाद", "", "outro.jpg", is_intro=True)
    final_clips.append(ImageClip("outro.jpg").set_duration(AudioFileClip("outro.mp3").duration).set_audio(AudioFileClip("outro.mp3")))

    # ५. एसेम्बल र सेभ
    video = concatenate_videoclips(final_clips, method="compose")
    output_file = "economics_final.mp4"
    video.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac", bitrate="1500k", ffmpeg_params=["-pix_fmt", "yuv420p", "-crf", "28"])

    send_video_email(output_file, today)

def send_video_email(filepath, date):
    msg = MIMEMultipart(); msg['From'] = SENDER; msg['To'] = SENDER; msg['Subject'] = f"Economics Daily Bulletin - {date}"
    with open(filepath, "rb") as f:
        part = MIMEBase('application', 'octet-stream'); part.set_payload(f.read()); encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= economics_video.mp4"); msg.attach(part)
    server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login(SENDER, PASSWORD); server.sendmail(SENDER, SENDER, msg.as_string()); server.quit()

if __name__ == "__main__":
    asyncio.run(run_automated_bulletin())
