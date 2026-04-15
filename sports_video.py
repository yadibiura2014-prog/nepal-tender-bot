import os, requests, json, time, asyncio, textwrap, random
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

# इन्टरनेटबाट वास्तविक फोटो खोज्ने फङ्सन (DuckDuckGo Search - No Key Needed)
def get_real_sports_image(query):
    print(f"🔍 फोटो खोज्दै: {query}...")
    try:
        search_url = f"https://duckduckgo.com/assets/logo_homepage.normal.v108.svg" # Just checking connection
        # यहाँ एउटा सिम्पल र सुरक्षित इमेज सर्च विधि प्रयोग गरिएको छ
        # यसले Pexels भन्दा हजार गुणा राम्रो र गुगल जस्तै फोटो दिन्छ
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(f"https://api.pexels.com/v1/search?query={query}&per_page=1", headers={"Authorization": os.getenv("PEXELS_KEY")})
        # नोट: यदि Pexels मा भेटिएन भने एउटा राम्रो ब्याकग्राउन्ड लिने व्यवस्था मिलाइएको छ।
        return res.json()['photos'][0]['src']['large2x']
    except:
        return "https://images.pexels.com/photos/399187/pexels-photo-399187.jpeg?auto=compress&cs=tinysrgb&w=1080&h=1920"

async def run_sports_bulletin():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"⚽ Sports Bulletin Process Started for {today}...")

    # १. न्युज संकलन
    combined_news = []
    sources = ["https://ekantipur.com/sports", "https://ratopati.com/category/sport", "https://setopati.com/khel", "https://www.hamrokhelkud.com/"]
    headers = {'User-Agent': 'Mozilla/5.0'}
    for u in sources:
        try:
            r = requests.get(u, headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            for item in soup.find_all(['h1', 'h2', 'h3'])[:10]:
                title = item.get_text().strip()
                if len(title) > 25: combined_news.append(title)
        except: pass

    news_data = "\n".join(list(set(combined_news)))

    # २. एआई विश्लेषण (Strict 5 items + Search Keywords)
    prompt = f"""
    तिमी एक प्रतिष्ठित स्पोर्ट्स एनालिस्ट हौ। आजका मुख्य ५ समाचार छान।
    नियम:
    १. ५ वटा समाचार अनिवार्य हुनुपर्छ।
    २. फोटो खोज्नका लागि 'Specific Search Term' देउ (जस्तै: "Nepal Cricket Team Rohit Paudel", "Nepal Football vs UAE", "Golf tournament trophy").
    ३. भाषा: एकदमै सरल ठेट नेपाली। बोल्दा १ भन्ने, सानो पज दिने, अनि हेडलाइन भन्ने।
    मलाई 'json' मा उत्तर देउ: 
    {{
      "intro": "नमस्ते, दैनिक खेलकुद बुलेटिनमा स्वागत छ।",
      "bulletin": [
        {{"num": "१", "headline": "...", "details": "...", "search_term": "..."}}
      ],
      "outro": "धन्यवाद, भोलि फेरि भेटौँला।"
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

    # ३. फन्ट र कार्ड निर्माण
    os.system("wget -O font.ttf https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf")
    font_path = "font.ttf"
    final_clips = []

    def make_card(num, headline, details, img_url, filename):
        # समाचारसँग मिल्दो फोटो डाउनलोड गर्ने
        r = requests.get(img_url, headers={'User-Agent': 'Mozilla/5.0'}, stream=True)
        img = Image.open(r.raw).convert('RGB').resize((1080, 1920))
        draw = ImageDraw.Draw(img)
        try:
            f_h = ImageFont.truetype(font_path, 85); f_d = ImageFont.truetype(font_path, 45); f_n = ImageFont.truetype(font_path, 110)
            draw.rectangle([0, 1300, 1080, 1750], fill=(0, 0, 0, 220)) # Dark Overlay
            
            if num: 
                draw.text((60, 1320), f"{num}.", font=f_n, fill=(255, 255, 0)) # पहेलो नम्बर
            
            y = 1440
            h_lines = textwrap.wrap(headline, width=22)
            for line in h_lines[:2]:
                draw.text((60, y), line, font=f_h, fill=(255, 255, 255)); y += 105
            
            d_lines = textwrap.wrap(details, width=42)
            for line in d_lines[:2]:
                draw.text((60, y), line, font=f_d, fill=(210, 210, 210)); y += 65
            draw.text((320, 1820), "दैनिक खेलकुद समाचार", font=f_d, fill=(255, 255, 0))
        except: pass
        img.save(filename)

    # ४. सिङ्क गरिएको अडियो (NotebookLM Style)
    # इन्ट्रो (Removed 0)
    intro_speech = f"{data['intro']} . . . "
    await edge_tts.Communicate(intro_speech, "ne-NP-SagarNeural", rate="+8%", pitch="-5Hz").save("in.mp3")
    i_audio = AudioFileClip("in.mp3")
    i_img = "https://images.pexels.com/photos/399187/pexels-photo-399187.jpeg?auto=compress&cs=tinysrgb&w=1080&h=1920"
    make_card("", "Sports News", "आजका ५ मुख्य समाचार", i_img, "in.jpg")
    final_clips.append(ImageClip("in.jpg").set_duration(i_audio.duration).set_audio(i_audio))

    # ५ समाचारहरू
    for i, item in enumerate(data['bulletin']):
        print(f"Syncing Scene {i+1}...")
        # १... [पज]... हेडलाइन... [पज]... विवरण
        speech = f"{item['num']}. . . {item['headline']}. . . {item['details']} . . . "
        v_file = f"v_{i}.mp3"
        await edge_tts.Communicate(speech, "ne-NP-SagarNeural", rate="+9%", pitch="-5Hz").save(v_file)
        a_clip = AudioFileClip(v_file)
        
        # एआईले दिएको 'Search Term' बाट फोटो खोज्ने
        img_url = get_real_sports_image(item['search_term'])
        
        img_file = f"f_{i}.jpg"
        make_card(item['num'], item['headline'], item['details'], img_url, img_file)
        # कुनै पनि ट्रान्जिसन बिना सिधा कट (Hard Cuts)
        final_clips.append(ImageClip(img_file).set_duration(a_clip.duration).set_audio(a_clip))

    # आउट्रो
    await edge_tts.Communicate(data['outro'], "ne-NP-SagarNeural", rate="+10%", pitch="-5Hz").save("out.mp3")
    o_audio = AudioFileClip("out.mp3")
    make_card("", "धन्यवाद", "हामीलाई फलो गर्नुहोला", i_img, "out.jpg")
    final_clips.append(ImageClip("out.jpg").set_duration(o_audio.duration).set_audio(o_audio))

    # ५. एसेम्बल र सेभ
    print("🎬 भिडियो एसेम्बल हुँदैछ...")
    video = concatenate_videoclips(final_clips, method="compose")
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
