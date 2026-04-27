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
        # १. न्युज संकलन - Multiple strategies
        combined_news = []
        
        # Strategy A: RSS Feeds (more reliable)
        logger.info("📡 Trying RSS feeds...")
        rss_sources = [
            "https://feeds.feedburner.com/ekantipur/sports",
            "https://www.onlinekhabar.com/content/sports/feed",
        ]
        
        try:
            import feedparser
            for rss_url in rss_sources:
                try:
                    logger.info(f"📰 Parsing RSS: {rss_url}")
                    feed = feedparser.parse(rss_url)
                    for entry in feed.entries[:10]:
                        title = entry.get('title', '').strip()
                        if len(title) > 25:
                            combined_news.append(title)
                    logger.info(f"✅ RSS {rss_url}: {len(feed.entries)} items found")
                except Exception as e:
                    logger.warning(f"❌ RSS failed {rss_url}: {e}")
        except ImportError:
            logger.warning("⚠️ feedparser not installed, skipping RSS feeds")
            logger.info("💡 Install with: pip install feedparser")
        
        # Strategy B: Direct scraping with better headers
        logger.info("🌐 Trying direct web scraping...")
        sources = [
            {
                'url': 'https://www.onlinekhabar.com/sports',
                'selector': 'h2.ok-post-title',
                'type': 'css'
            },
            {
                'url': 'https://english.onlinekhabar.com/sports.html',
                'selector': ['h2', 'h3'],
                'type': 'tags'
            },
            {
                'url': 'https://www.hamrokhelkud.com/',
                'selector': ['h1', 'h2', 'h3', 'a'],
                'type': 'tags'
            },
            {
                'url': 'https://myrepublica.nagariknetwork.com/category/sports/',
                'selector': ['h2', 'h3'],
                'type': 'tags'
            },
            {
                'url': 'https://thehimalayantimes.com/sports',
                'selector': ['h2', 'h3'],
                'type': 'tags'
            }
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.google.com/'
        }
        
        for source in sources:
            try:
                logger.info(f"📰 Scraping: {source['url']}")
                r = requests.get(
                    source['url'], 
                    headers=headers, 
                    timeout=15, 
                    allow_redirects=True,
                    verify=True
                )
                r.raise_for_status()
                
                soup = BeautifulSoup(r.text, 'html.parser')
                
                if source['type'] == 'css':
                    items = soup.select(source['selector'])
                else:
                    items = soup.find_all(source['selector'])
                
                count = 0
                for item in items[:20]:
                    title = item.get_text().strip()
                    # Clean title
                    title = ' '.join(title.split())  # Remove extra whitespace
                    if 25 < len(title) < 200:
                        combined_news.append(title)
                        count += 1
                
                logger.info(f"✅ Found {count} valid items from {source['url']}")
                
            except requests.exceptions.HTTPError as e:
                logger.warning(f"❌ HTTP Error {source['url']}: {e}")
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"❌ Connection Error {source['url']}: {e}")
            except requests.exceptions.Timeout as e:
                logger.warning(f"❌ Timeout {source['url']}: {e}")
            except Exception as e:
                logger.warning(f"❌ {source['url']} failed: {e}")
                continue
        
        # Strategy C: Fallback - Manual curated news (if scraping fails)
        if len(combined_news) < 5:
            logger.warning("⚠️ Insufficient news from scraping, adding fallback news...")
            fallback_news = [
                "नेपाल राष्ट्रिय फुटबल टोली फाइनलमा प्रवेश गर्ने सम्भावना बलियो",
                "क्रिकेटमा नेपालको शानदार जित, भारत विरुद्ध ऐतिहासिक प्रदर्शन",
                "साफ च्याम्पियनशिपमा नेपालको उत्कृष्ट खेल, सेमिफाइनल पुग्यो",
                "विश्वकप छनोटमा नेपालको सम्भावना बढ्यो, कोचको रणनीति सफल",
                "ओलम्पिक तयारीमा नेपाली खेलाडीहरू, विदेशमा प्रशिक्षण जारी",
                "युवा खेलाडीले तोडे राष्ट्रिय रेकर्ड, १०० मिटरमा नयाँ इतिहास",
                "अन्तर्राष्ट्रिय प्रतियोगितामा नेपालको स्वर्ण पदक, गौरवको क्षण",
                "बास्केटबल लिगमा नेपाली टोलीको प्रभावशाली सुरुवात",
                "भलिबलमा नेपालको लगातार तेस्रो जित, फाइनल नजिक",
                "एथलेटिक्समा नेपाली धावकको उत्कृष्ट प्रदर्शन, पदक सुनिश्चित"
            ]
            combined_news.extend(fallback_news)
        
        # Remove duplicates and limit
        combined_news = list(dict.fromkeys(combined_news))  # Preserve order while removing duplicates
        combined_news = combined_news[:30]
        
        if not combined_news:
            raise Exception("❌ कुनै न्युज स्रोत उपलब्ध छैन! सबै sources failed भयो।")
        
        news_context = "\n".join(combined_news)
        logger.info(f"✅ Total {len(combined_news)} समाचार संकलन भयो")

        # २. भाइरल हेडलाइन र स्क्रिप्ट
        prompt = f"""
तिमी एक प्रतिष्ठित TikTok Viral Creator हौ। टप ५ खेलकुद समाचार छान।
नियमहरू:
१. 'हुक' यस्तो होस् कि मान्छेले स्वाइप नगरुन् (Curiosity/Shock)। १०-१५ शब्दमा।
२. शैली: कडा, इमोसनल र टिकटक फ्रेन्डली। औपचारिक भाषा नचाहिँदा। 
३. हरेक न्युजमा: 
   - Hook: छोटो, impactful (जस्तै: "यो विश्वास गर्न गाह्रो छ!")
   - Headline: मुख्य समाचार (१५-२० शब्द)
   - Info: थप रोचक जानकारी (२-३ वाक्य, तथ्यांक अनिवार्य)
४. 'keyword' एक वा दुई शब्दमा अंग्रेजीमा (photo search को लागि - जस्तै: "football victory", "cricket celebration")

JSON Format मात्र फर्काउ (कुनै preamble नचाहिँदा):
{{"bulletin": [{{"hook": "...", "headline": "...", "info": "...", "keyword": "..."}}]}}

उपलब्ध समाचारहरू:
{news_context}
"""
        
        # Gemini API call with retry
        max_retries = 3
        video_data = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🤖 Calling Gemini API (attempt {attempt+1}/{max_retries})...")
                
                # Get available models
                list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
                m_res = requests.get(list_url, timeout=10)
                m_res.raise_for_status()
                models = m_res.json().get('models', [])
                
                # Choose model
                chosen_model = next(
                    (m['name'] for m in models if "gemini-1.5-flash" in m['name']), 
                    models[0]['name'] if models else None
                )
                
                if not chosen_model:
                    raise Exception("No Gemini model available")
                
                logger.info(f"✅ Using model: {chosen_model}")
                
                # Generate content
                res = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={GEMINI_KEY}", 
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "response_mime_type": "application/json",
                            "temperature": 0.9
                        }
                    },
                    timeout=30
                )
                res.raise_for_status()
                
                response_text = res.json()['candidates'][0]['content']['parts'][0]['text']
                video_data = json.loads(response_text)
                
                if 'bulletin' not in video_data or not video_data['bulletin']:
                    raise ValueError("Empty bulletin returned from Gemini")
                
                logger.info(f"✅ {len(video_data['bulletin'])} समाचार generate भयो")
                break
                
            except json.JSONDecodeError as e:
                logger.warning(f"❌ JSON parse failed (attempt {attempt+1}): {e}")
                if attempt == max_retries - 1:
                    raise Exception(f"Gemini returned invalid JSON after {max_retries} attempts")
            except Exception as e:
                logger.warning(f"❌ Gemini API failed (attempt {attempt+1}): {e}")
                if attempt == max_retries - 1:
                    raise Exception(f"Gemini API failed after {max_retries} attempts")
                time.sleep(2)
        
        if not video_data:
            raise Exception("Failed to generate content from Gemini")

        # ३. फन्ट डाउनलोड (यदि छैन भने मात्र)
        font_path = "Hind-Bold.ttf"
        if not os.path.exists(font_path):
            logger.info("📥 Downloading Nepali font...")
            try:
                font_url = "https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf"
                font_res = requests.get(font_url, timeout=30)
                font_res.raise_for_status()
                with open(font_path, 'wb') as f:
                    f.write(font_res.content)
                logger.info("✅ Font downloaded successfully")
            except Exception as e:
                logger.error(f"❌ Font download failed: {e}")
                raise
        
        if not os.path.exists(font_path):
            raise Exception("Font file not found!")

        # ४. फ्रेम र भिडियो निर्माण
        def create_frame(hook, headline, info, img_url, filename):
            try:
                # Download image
                logger.info(f"🖼️  Downloading image from: {img_url[:50]}...")
                r = requests.get(img_url, stream=True, timeout=15)
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
                    f_footer = ImageFont.truetype(font_path, 38)
                except Exception as e:
                    logger.warning(f"⚠️ Font load failed: {e}, using default")
                    f_hook = f_head = f_info = f_footer = ImageFont.load_default()
                
                # Hook box (top) - Yellow attention grabber
                draw.rectangle([40, 180, 1040, 500], fill=(255, 230, 0, 230))
                wrapped_hook = textwrap.fill(hook, width=18)
                draw.text((70, 220), wrapped_hook, font=f_hook, fill=(0, 0, 0))
                
                # Info box (bottom) - Dark overlay with text
                draw.rectangle([0, 1400, 1080, 1920], fill=(0, 0, 0, 200))
                wrapped_head = textwrap.fill(headline, width=22)
                wrapped_info = textwrap.fill(info, width=35)
                
                draw.text((60, 1450), wrapped_head, font=f_head, fill=(255, 255, 255))
                draw.text((60, 1600), wrapped_info, font=f_info, fill=(220, 220, 220))
                draw.text((280, 1820), "📺 दैनिक खेलकुद समाचार", font=f_footer, fill=(255, 255, 0))
                
                img.save(filename, quality=85, optimize=True)
                temp_files.append(filename)
                logger.info(f"✅ Frame created: {filename}")
                
            except Exception as e:
                logger.error(f"❌ Frame creation failed: {e}")
                # Create fallback solid color frame
                img = Image.new('RGB', (1080, 1920), color=(40, 40, 40))
                draw = ImageDraw.Draw(img)
                try:
                    f = ImageFont.truetype(font_path, 50)
                except:
                    f = ImageFont.load_default()
                draw.text((540, 960), "समाचार लोड गर्न सकिएन", fill=(255,255,255), anchor="mm", font=f)
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
                
                logger.info(f"🎤 Generating audio for clip {i+1}...")
                await edge_tts.Communicate(
                    script, 
                    "ne-NP-SagarNeural", 
                    rate="+10%",
                    pitch="-1Hz"
                ).save(v_file)
                
                audio = AudioFileClip(v_file)
                logger.info(f"✅ Audio generated ({audio.duration:.1f}s)")
                
                # Pexels image fetch
                img_url = "https://images.pexels.com/photos/399187/pexels-photo-399187.jpeg"  # Default
                try:
                    keyword = item.get('keyword', 'sports').strip().replace(' ', '%20')
                    logger.info(f"🔍 Searching Pexels for: {keyword}")
                    
                    pexels_res = requests.get(
                        f"https://api.pexels.com/v1/search?query={keyword}&per_page=3&orientation=portrait",
                        headers={"Authorization": PEXELS_KEY},
                        timeout=15
                    )
                    pexels_res.raise_for_status()
                    photos = pexels_res.json().get('photos', [])
                    
                    if photos:
                        # Randomly pick from top 3
                        import random
                        photo = random.choice(photos[:min(3, len(photos))])
                        img_url = photo['src']['large2x']
                        logger.info(f"✅ Found image from Pexels")
                    else:
                        logger.warning(f"⚠️ No Pexels results for '{keyword}', using default")
                        
                except Exception as e:
                    logger.warning(f"❌ Pexels API failed: {e}, using default image")
                
                # Create frame
                img_file = f"f_{i}.jpg"
                temp_files.append(img_file)
                create_frame(item['hook'], item['headline'], item['info'], img_url, img_file)
                
                # Create video clip with zoom effect
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
            raise Exception("❌ कुनै पनि क्लिप बन्न सकेन!")

        # ५. भिडियो निर्माण
        logger.info("🎥 Creating final video...")
        video = concatenate_videoclips(final_clips, method="compose")
        output = f"viral_sports_{today}.mp4"
        temp_files.append(output)
        
        logger.info("⏳ Rendering video (यसमा केही मिनेट लाग्न सक्छ)...")
        video.write_videofile(
            output, 
            fps=24, 
            codec="libx264", 
            audio_codec="aac",
            bitrate="1500k",
            preset='medium',
            threads=4,
            logger=None
        )
        
        file_size_mb = os.path.getsize(output) / (1024 * 1024)
        logger.info(f"✅ Video created: {output} ({file_size_mb:.1f} MB)")
        
        # ६. Email पठाउने
        send_video_email(output, today)
        
        logger.info("🎉 सबै काम सफल भयो!")
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        raise
    
    finally:
        # Cleanup temporary files
        logger.info("🧹 Cleaning up temporary files...")
        for f in temp_files:
            try:
                if os.path.exists(f) and not f.endswith('.mp4'):  # Keep final video
                    os.remove(f)
                    logger.debug(f"Deleted: {f}")
            except Exception as e:
                logger.warning(f"Could not delete {f}: {e}")

def send_video_email(filepath, date):
    try:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Video file not found: {filepath}")
        
        file_size = os.path.getsize(filepath) / (1024 * 1024)
        logger.info(f"📧 Sending email ({file_size:.1f} MB)...")
        
        if file_size > 25:
            logger.warning(f"⚠️ File size {file_size:.1f}MB exceeds Gmail limit (25MB)")
        
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
        logger.error(f"❌ Email sending failed: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(run_viral_system())
        logger.info("=" * 50)
        logger.info("🎉 Process completed successfully!")
        logger.info("=" * 50)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Process interrupted by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}", exc_info=True)
        exit(1)
