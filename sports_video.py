import os, requests, json, time, asyncio, textwrap, re
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

# डकडकगोबाट वास्तविक फोटो खोज्ने फङ्सन (No Key Needed)
def get_real_image(query):
    try:
        url = "https://duckduckgo.com/assets/logo_homepage.normal.v108.svg" # Just to check connection
        # समाचारको हेडलाइनबाट विशिष्ट फोटो खोज्ने
        search_url = f"https://duckduckgo.com/i.js?q={query}&o=json"
        headers = {'User-Agent': 'Mozilla/5.0'}
        # हामी यहाँ एउटा सिम्पल तरिकाले पिक्सल्स र एआईको किवर्ड मिलाएर फोटो लिन्छौँ
        # किनभने सिधै गुगल स्क्र्याप गर्दा गिटहबले ब्लक गर्न सक्छ। 
        # त्यसैले हामी एआईलाई 'सान्दर्भिक' किवर्ड निकाल्न भन्छौँ।
        return None
    except: return None

async def run_sports_bulletin():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"⚽ Real Sports Bulletin Process Started for {today}...")

    # १. न्युज संकलन
    combined_news = []
    sources = ["https://ekantipur.com/sports", "https://ratopati.com/category/sport", "https://setopati.com/khel", "https://www.hamrokhelkud.com/"]
    headers = {'User-Agent': 'Mozilla/5.0'}
    for u in sources:
        try:
            r = requests.get(u, headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            for item in soup.find_all(['h1', 'h2', 'h3'])[:8]:
                title = item.get_text().strip()
                if len(title) > 25: combined_news.append(title)
        except: pass

    news_data = "\n".join(list(set(combined_news)))

    # २. एआई विश्लेषण (Focus on Specific Keywords for Real Images)
    prompt = f"""
    तिमी एक प्रतिष्ठित स्पोर्ट्स एनालिस्ट हौ। आजका मुख्य ५ समाचार छान।
    नियम: १ हेडलाइन + १-२ वाक्यको थप तथ्य। कुल १ मिनेटको भिडियो। 
    फोटोको लागि: समाचारको मुख्य पात्र वा खेलको नाम जोडिएको 'Specific' किवर्ड देउ (जस्तै: "Nepal Cricket Team celebrating", "Nepali Footballer Anjan Bista").
    मलाई 'json' मा उत्तर देउ: {{'intro': '...', 'bulletin': [{{'num': '१', 'headline': '...', 'details': '...', 'keyword': '...'}}], 'outro': '...'}}
    DATA: {news_data}
    """
    
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    m_res = requests.get(list_url).json()
    usable = [m['name'] for m in m_res.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
    chosen_model = next((m for m in usable if "gemini-1.5-flash" in m), usable[0])

    res = requests.post(f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={GEMINI_KEY}", 
                        json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"response_mime_type": "application/json"}})
    data = json.loads(res.json()['candidates'][0]['content']['parts'][0]['text'])

    # ३. फन्ट र भिडियो कार्ड सेटअप
    os.system("wget -O font.ttf https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf")
    font_path = "font.ttf"
    final_clips = []

    def make_sports_card(num, headline, details, img_url, filename):
        # वास्तविक फोटो डाउनलोड गर्ने
        r = requests.get(img_url, stream=True)
        img_raw = Image.open(r.raw).convert('RGB').resize((1080, 1920))
        draw = ImageDraw.Draw(img_raw)
        try:
            f_n = ImageFont.truetype(font_path, 110); f_h = ImageFont.truetype(font_path, 80); f_d = ImageFont.truetype(font_path, 45); f_b = ImageFont.truetype(font_path, 40)
            draw.rectangle([0, 1300, 1080, 1750], fill=(0, 0, 0, 220)) # अझ गाढा पट्टी
            draw.text((60, 1320), f"{num}.", font=f_n, fill=(255, 255, 0))
            h_lines = textwrap.wrap(headline, width=22)
            y = 1440
            for line in h_lines[:2]:
                draw.text((60, y), line, font=f_h, fill=(255, 255, 255)); y += 100
            d_lines = textwrap.wrap(details, width=42)
            for line in d_lines[:2]:
                draw.text((60, y), line, font=f_d, fill=(210, 210, 210)); y += 60
            draw.text((320, 1820), "दैनिक खेलकुद समाचार", font=f_b, fill=(255, 255, 0))
        except: pass
        img_raw.save(filename)

    # ४. अडियो र सिन निर्माण (No Fade/Transitions)
    await edge_tts.Communicate(data['intro'], "ne-NP-SagarNeural", rate="+12%", pitch="-2Hz").save("in.mp3")
    # इन्ट्रोको लागि एउटा राम्रो फोटो
    intro_img_url = "https://images.pexels.com/photos/399187/pexels-photo-399187.jpeg?auto=compress&cs=tinysrgb&w=1080&h=1920&dpr=1"
    make_sports_card("0", "Khelkud Samachaar", "आजका ५ मुख्य समाचार", intro_img_url, "in.jpg")
    final_clips.append(ImageClip("in.jpg").set_duration(AudioFileClip("in.mp3").duration).set_audio(AudioFileClip("in.mp3")))

    for i, item in enumerate(data['bulletin']):
        text = f"{item['num']}. . . {item['headline']}. . . {item['details']}"
        v_file = f"v_{i}.mp3"
        await edge_tts.Communicate(text, "ne-NP-SagarNeural", rate="+15%", pitch="-2Hz").save(v_file)
        a_clip = AudioFileClip(v_file)
        
        # Pexels मा विशिष्ट कीवर्डबाट फोटो खोज्ने (नेपालको फोटो नभए साउथ एसियाली खोज्ने)
        kw = item['keyword']
        r_img = requests.get(f"https://api.pexels.com/v1/search?query={kw}&per_page=5&orientation=portrait", headers={"Authorization": os.getenv("PEXELS_KEY")}).json()
        
        # यदि पिक्सल्समा फोटो भेटिएन भने एउटा स्ट्यान्डर्ड स्पोर्ट्स ब्याकग्राउन्ड लिने
        img_url = r_img['photos'][0]['src']['large2x'] if 'photos' in r_img and len(r_img['photos']) > 0 else intro_img_url
        
        img_file = f"f_{i}.jpg"
        make_sports_card(item['num'], item['headline'], item['details'], img_url, img_file)
        
        # मुख्य सुधार: कुनै पनि resize वा fade इफेक्ट बिना सिधा क्लिप
        clip = ImageClip(img_file).set_duration(a_clip.duration).set_audio(a_clip)
        final_clips.append(clip)

    await edge_tts.Communicate(data['outro'], "ne-NP-SagarNeural", rate="+10%").save("out.mp3")
    make_sports_card("✓", "धन्यवाद", "हामीलाई पछ्याउँदै गर्नुहोला", intro_img_url, "out.jpg")
    final_clips.append(ImageClip("out.jpg").set_duration(AudioFileClip("out.mp3").duration).set_audio(AudioFileClip("out.mp3")))

    # ५. एसेम्बल (No Transitions)
    print("🎬 भिडियो जोडिँदैछ (Hard Cuts Only)...")
    # method="chain" ले गर्दा एउटा सिन सकिने बित्तिकै अर्को झ्याप्प आउँछ
    video = concatenate_videoclips(final_clips, method="chain")
    video.write_videofile("sports_final.mp4", fps=24, codec="libx264", audio_codec="aac", bitrate="1500k", ffmpeg_params=["-pix_fmt", "yuv420p", "-crf", "28"])
    send_video_email("sports_final.mp4", today)

def send_video_email(filepath, date):
    msg = MIMEMultipart(); msg['From'] = SENDER; msg['To'] = SENDER; msg['Subject'] = f"Daily Sports Video - {date}"
    with open(filepath, "rb") as f:
        part = MIMEBase('application', 'octet-stream'); part.set_payload(f.read()); encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= sports_news.mp4"); msg.attach(part)
    server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login(SENDER, PASSWORD); server.sendmail(SENDER, SENDER, msg.as_string()); server.quit()

if __name__ == "__main__":
    asyncio.run(run_sports_bulletin())
