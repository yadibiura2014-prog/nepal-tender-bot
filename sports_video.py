import os, requests, json, time, asyncio, textwrap, logging
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import edge_tts
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables check
REQUIRED_VARS = {
    'GEMINI_API_KEY': os.getenv("GEMINI_API_KEY"),
    'PEXELS_KEY': os.getenv("PEXELS_KEY"),
    'EMAIL_SENDER': os.getenv("EMAIL_SENDER"),
    'EMAIL_PASSWORD': os.getenv("EMAIL_PASSWORD")
}

for var, val in REQUIRED_VARS.items():
    if not val:
        raise ValueError(f"❌ {var} environment variable छैन!")

GEMINI_KEY = REQUIRED_VARS['GEMINI_API_KEY']
PEXELS_KEY = REQUIRED_VARS['PEXELS_KEY']
SENDER = REQUIRED_VARS['EMAIL_SENDER']
PASSWORD = REQUIRED_VARS['EMAIL_PASSWORD']

async def run_viral_system():
    today = datetime.now().strftime("%Y-%m-%d")
    logger.info(f"🚀 Viral Sports System Started for {today}...")
    
    temp_files = []  # Track files for cleanup

    try:
        # १. न्युज संकलन
        combined_news = []
        sources = [
            "https://ekantipur.com/sports", 
            "https://ratopati.com/category/sport",
            "https://setopati.com/khel", 
            "https://www.hamrokhelkud.com/"
        ]
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        for u in sources:
            try:
                logger.info(f"📰 Scraping: {u}")
                r = requests.get(u, headers=headers, timeout=15)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, 'html.parser')
                for item in soup.find_all(['h1', 'h2', 'h3', 'a'])[:15]:  # थप समाचार
                    title = item.get_text().strip()
                    if len(title) > 25 and len(title) < 200:  # धेरै लामो हटाउने
                        combined_news.append(title)
            except Exception as e:
                logger.warning(f"❌ {u} scrape failed: {e}")
                continue
        
        if not combined_news:
            raise Exception("कुनै न्युज भेटिएन!")
        
        news_context = "\n".join(list(set(combined_news))[:30])  # Unique + limited
        logger.info(f"✅ {len(combined_news)} समाचार संकलन भयो")

        # २. भाइरल हेडलाइन र स्क्रिप्ट
        prompt = f"""
तिमी एक प्रतिष्ठित TikTok Viral Creator हौ। टप ५ खेलकुद समाचार छान।
नियमहरू:
१. 'हुक' यस्तो होस् कि मान्छेले स्वाइप नगरुन् (Curiosity/Shock)।
२. शैली: कडा, इमोसनल र टिकटक फ्रेन्डली। 
३. हरेक न्युजमा: १ Hook (१०-१५ शब्द), १ Headline (छोटो, स्पष्ट) र १-२ वाक्य रोचक थप जानकारी।
४. 'keyword' एक वा दुई शब्दमा (photo search को लागि - english)।

JSON Format मात्र:
{{"bulletin": [{{"hook": "...", "headline": "...", "info": "...", "keyword": "..."}}]}}

समाचारहरू:
{news_context}
"""
        
        # Gemini API call with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
                m_res = requests.get(list_url, timeout=10)
                m_res.raise_for_status()
                models = m_res.json().get('models', [])
                chosen_model = next((m['name'] for m in models if "gemini-1.5-flash" in m['name']), models[0]['name'] if models else None)
                
                if not chosen_model:
                    raise Exception("No Gemini model available")
                
                logger.info(f"🤖 Using model: {chosen_model}")
                
                res = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={GEMINI_KEY}", 
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"response_mime_type": "application/json"}
                    },
                    timeout=30
                )
                res.raise_for_status()
                
                response_text = res.json()['candidates'][0]['content']['parts'][0]['text']
                video_data = json.loads(response_text)
                
                if 'bulletin' not in video_data or not video_data['bulletin']:
                    raise ValueError("Empty bulletin returned")
                
                logger.info(f"✅ {len(video_data['bulletin'])} समाचार generate भयो")
                break
                
            except Exception as e:
                logger.warning(f"Attempt {attempt+1} failed: {e}")
                if attempt == max_retries - 1:
                    raise Exception(f"Gemini API failed after {max_retries} attempts")
                time.sleep(2)

        # ३. फन्ट डाउनलोड (यदि छैन भने मात्र)
        font_path = "Hind-Bold.ttf"
        if not os.path.exists(font_path):
            logger.info("📥 Downloading font...")
            os.system(f"wget -q -O {font_path} https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf")
        
        if not os.path.exists(font_path):
            raise Exception("Font download failed!")

        # ४. फ्रेम र भिडियो निर्माण
        def create_frame(hook, headline, info, img_url, filename):
            try:
                r = requests.get(img_url, stream=True, timeout=10)
                r.raise_for_status()
                img = Image.open(r.raw).convert('RGB')
                
                # Proper 9:16 ratio for TikTok/Reels
                img = img.resize((1080, 1920), Image.LANCZOS)
                draw = ImageDraw.Draw(img)
                
                # Fonts with error handling
                try:
                    f_hook = ImageFont.truetype(font_path, 85)
                    f_head = ImageFont.truetype(font_path, 65)
                    f_info = ImageFont.truetype(font_path, 42)
                except:
                    logger.warning("⚠️ Font load failed, using default")
                    f_hook = f_head = f_info = ImageFont.load_default()
                
                # Hook box (top)
                draw.rectangle([40, 180, 1040, 500], fill=(255, 230, 0, 230))
                wrapped_hook = textwrap.fill(hook, width=18)
                draw.text((70, 220), wrapped_hook, font=f_hook, fill=(0, 0, 0))
                
                # Info box (bottom)
                draw.rectangle([0, 1400, 1080, 1920], fill=(0, 0, 0, 200))
                wrapped_head = textwrap.fill(headline, width=22)
                wrapped_info = textwrap.fill(info, width=35)
                
                draw.text((60, 1450), wrapped_head, font=f_head, fill=(255, 255, 255))
                draw.text((60, 1600), wrapped_info, font=f_info, fill=(220, 220, 220))
                draw.text((280, 1820), "📺 दैनिक खेलकुद समाचार", font=f_info, fill=(255, 255, 0))
                
                img.save(filename, quality=85, optimize=True)
                temp_files.append(filename)
                logger.info(f"✅ Frame created: {filename}")
            except Exception as e:
                logger.error(f"Frame creation failed: {e}")
                # Create fallback solid color frame
                img = Image.new('RGB', (1080, 1920), color=(40, 40, 40))
                draw = ImageDraw.Draw(img)
                draw.text((540, 960), "समाचार लोड गर्न सकिएन", fill=(255,255,255), anchor="mm")
                img.save(filename)
                temp_files.append(filename)

        final_clips = []
        
        for i, item in enumerate(video_data['bulletin'][:5]):
            try:
                logger.info(f"🎬 Processing news {i+1}/5...")
                
                # Audio generation
                script = f"{item['hook']}. . . {item['headline']}. . . {item['info']}"
                v_file = f"v_{i}.mp3"
                temp_files.append(v_file)
                
                await edge_tts.Communicate(
                    script, 
                    "ne-NP-SagarNeural", 
                    rate="+10%",  # थोरै सुस्त (clarity को लागि)
                    pitch="-1Hz"
                ).save(v_file)
                
                audio = AudioFileClip(v_file)
                
                # Pexels image fetch
                img_url = "https://images.pexels.com/photos/399187/pexels-photo-399187.jpeg"  # Default
                try:
                    keyword = item.get('keyword', 'sports').replace(' ', '%20')
                    pexels_res = requests.get(
                        f"https://api.pexels.com/v1/search?query={keyword}&per_page=1&orientation=portrait",
                        headers={"Authorization": PEXELS_KEY},
                        timeout=10
                    )
                    pexels_res.raise_for_status()
                    photos = pexels_res.json().get('photos', [])
                    if photos:
                        img_url = photos[0]['src']['large2x']
                except Exception as e:
                    logger.warning(f"Pexels API failed, using default: {e}")
                
                # Create frame
                img_file = f"f_{i}.jpg"
                temp_files.append(img_file)
                create_frame(item['hook'], item['headline'], item['info'], img_url, img_file)
                
                # Create video clip with zoom
                clip = (ImageClip(img_file)
                       .set_duration(audio.duration)
                       .set_audio(audio)
                       .resize(lambda t: 1 + 0.03 * t))  # Subtle zoom
                
                final_clips.append(clip)
                logger.info(f"✅ Clip {i+1} ready ({audio.duration:.1f}s)")
                
            except Exception as e:
                logger.error(f"❌ Clip {i+1} failed: {e}")
                continue
        
        if not final_clips:
            raise Exception("कुनै पनि क्लिप बनेन!")

        # ५. भिडियो निर्माण
        logger.info("🎥 Creating final video...")
        video = concatenate_videoclips(final_clips, method="compose")
        output = f"viral_sports_{today}.mp4"
        temp_files.append(output)
        
        video.write_videofile(
            output, 
            fps=24, 
            codec="libx264", 
            audio_codec="aac",
            bitrate="1500k",  # Better quality
            preset='medium',  # Balance speed/quality
            threads=4,
            logger=None  # Suppress moviepy logs
        )
        
        file_size_mb = os.path.getsize(output) / (1024 * 1024)
        logger.info(f"✅ Video created: {output} ({file_size_mb:.1f} MB)")
        
        # ६. Email पठाउने
        send_video_email(output, today)
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        raise
    
    finally:
        # Cleanup temporary files
        logger.info("🧹 Cleaning up...")
        for f in temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass

def send_video_email(filepath, date):
    try:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Video file not found: {filepath}")
        
        file_size = os.path.getsize(filepath) / (1024 * 1024)
        logger.info(f"📧 Sending email ({file_size:.1f} MB)...")
        
        msg = MIMEMultipart()
        msg['From'] = SENDER
        msg['To'] = SENDER
        msg['Subject'] = f"🎬 Viral Sports Video - {date}"
        
        with open(filepath, "rb") as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(filepath)}"')
            msg.attach(part)
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SENDER, PASSWORD)
            server.sendmail(SENDER, SENDER, msg.as_string())
        
        logger.info("✅ Email sent successfully!")
        
    except Exception as e:
        logger.error(f"❌ Email failed: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(run_viral_system())
        logger.info("🎉 Process completed successfully!")
    except KeyboardInterrupt:
        logger.info("⚠️ Process interrupted by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}", exc_info=True)
        exit(1)
