import os, requests, json, time, asyncio, textwrap, logging, glob
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import edge_tts
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# --- Secrets from GitHub ---
GEMINI_KEY   = os.getenv("GEMINI_API_KEY")
SENDER       = os.getenv("EMAIL_SENDER")
PASSWORD     = os.getenv("EMAIL_PASSWORD")
UNSPLASH_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

FONT_PATH = "font.ttf"
FONT_URL  = "https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf"

# ── Font: download once ──────────────────────────────────────────────
def ensure_font():
    if not Path(FONT_PATH).exists():
        log.info("Font download गर्दै...")
        r = requests.get(FONT_URL, timeout=15)
        r.raise_for_status()
        Path(FONT_PATH).write_bytes(r.content)
        log.info("Font तयार")

# ── Gemini model picker ──────────────────────────────────────────────
def get_best_gemini_model() -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    models = requests.get(url, timeout=10).json().get('models', [])
    eligible = [m['name'] for m in models
                if 'generateContent' in m.get('supportedGenerationMethods', [])]
    return next((m for m in eligible if "gemini-1.5-flash" in m), eligible[0])

# ── Single shared background image ──────────────────────────────────
def fetch_shared_background(all_headlines: list, filename: str) -> bool:
    """
    सबै headlines हेरेर एउटा सबैभन्दा relevant background image download गर्छ।
    """
    try:
        model = get_best_gemini_model()
        url   = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={GEMINI_KEY}"

        headlines_text = "\n".join(all_headlines)
        prompt = f"""
        यी Nepal का आर्थिक समाचार headlines हेरेर Unsplash image search को लागि
        सबैभन्दा relevant 3-4 word English keyword दिनुस्।
        Rules:
        - Visual र concrete हुनुपर्छ (जस्तै: 'Nepal stock market trading', 'Nepali currency banknotes', 'Nepal bank finance')
        - एउटा मात्र keyword line दिनुस्, अरु केही होइन
        Headlines:
        {headlines_text}
        """
        res = requests.post(
            url,
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=15
        )
        keyword = res.json()['candidates'][0]['content']['parts'][0]['text'].strip().split('\n')[0][:60]
        log.info(f"Shared BG keyword: '{keyword}'")

        params = {
            "query": keyword,
            "per_page": 1,
            "orientation": "portrait",
            "client_id": UNSPLASH_KEY
        }
        res2 = requests.get("https://api.unsplash.com/search/photos", params=params, timeout=10)
        res2.raise_for_status()
        results = res2.json().get("results", [])

        if not results:
            log.warning("Unsplash मा image भेटिएन, fallback background प्रयोग हुनेछ")
            return False

        img_data = requests.get(results[0]["urls"]["regular"], timeout=15).content
        Path(filename).write_bytes(img_data)
        log.info(f"Shared background download भयो: {filename}")
        return True

    except Exception as e:
        log.warning(f"Background fetch fail: {e}")
        return False

# ── News scraping ────────────────────────────────────────────────────
def scrape_news() -> str:
    sources = [
        "https://ekantipur.com/business",
        "https://kathmandupost.com/money",
        "https://setopati.com/kinmel",
        "https://ratopati.com/category/economy",
        "https://baarakhari.com/category/business",
        "https://www.sharesansar.com/category/latest-news",
        "https://www.nayapatrikadaily.com/category/11",
        "https://nagariknews.nagariknetwork.com/economy",
    ]
    headlines = set()
    headers = {'User-Agent': 'Mozilla/5.0'}

    for url in sources:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'html.parser')
            for tag in soup.find_all(['h1', 'h2', 'h3'])[:8]:
                title = tag.get_text().strip()
                if len(title) > 25:
                    headlines.add(title)
        except Exception as e:
            log.warning(f"Scrape fail ({url}): {e}")

    log.info(f"{len(headlines)} unique headlines भेटियो")
    return "\n".join(headlines)

# ── Gemini bulletin generation ───────────────────────────────────────
def generate_bulletin(news_data: str) -> dict:
    model = get_best_gemini_model()
    url   = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={GEMINI_KEY}"

    prompt = f"""
    तिमी एक प्रतिष्ठित PhD Economic Analyst हौ। आजको ६ मुख्य 'आर्थिक समाचार' मात्र छान।
    कार्यहरू:
    १. प्राथमिकता: सबैभन्दा महत्वपूर्ण समाचार (ब्याजदर, बजेट, ठूला निर्णय) लाई सुरुमा राख।
    २. इन्ट्रो: "नमस्ते, आजका प्रमुख आर्थिक समाचारहरूमा स्वागत छ।" — यो natural, warm tone मा लेख।
    ३. हरेक समाचारमा अङ्क र तथ्य अनिवार्य छ। राजनीति वर्जित।
    ४. headline र details दुवै नेपालीमा मात्र लेख्नुस् — अंग्रेजी शब्द नराख्नुस्।
    ५. voice को लागि text natural पढिने गरी लेख — अल्पविराम (,) र पूर्णविराम (।) सही ठाउँमा राख।
    ६. bulletin array मा EXACTLY ६ वटा item मात्र हुनुपर्छ।
    ७. outro मा धन्यवाद र subscribe/follow गर्न भन्नुस् — Nepali मा natural tone मा।
    मलाई यो 'json' मा उत्तर देउ:
    {{"intro": "...", "bulletin": [{{"num": "१", "headline": "...", "details": "..."}}], "outro": "..."}}
    DATA: {news_data}
    """

    backoff = 20
    for attempt in range(5):
        try:
            res = requests.post(
                url,
                json={"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"response_mime_type": "application/json"}},
                timeout=30
            )
            res.raise_for_status()
            body = res.json()
            if 'candidates' in body:
                data = json.loads(body['candidates'][0]['content']['parts'][0]['text'])
                data['bulletin'] = data['bulletin'][:6]
                log.info(f"Bulletin तयार: {len(data['bulletin'])} items")
                return data
            log.warning(f"No candidates (attempt {attempt+1}), retry in {backoff}s")
        except Exception as e:
            log.warning(f"Gemini error (attempt {attempt+1}): {e}")
        time.sleep(backoff)
        backoff = min(backoff * 2, 120)

    raise RuntimeError("Gemini ले ५ पटक पनि उत्तर दिएन।")

# ── Card rendering ───────────────────────────────────────────────────
def make_card(num: str, headline: str, details: str,
              filename: str, bg_image_path: str = None):
    W, H = 1080, 1920

    # Background
    if bg_image_path and Path(bg_image_path).exists():
        try:
            bg = Image.open(bg_image_path).convert("RGB")
            bg_ratio     = bg.width / bg.height
            target_ratio = W / H
            if bg_ratio > target_ratio:
                new_w  = int(bg.height * target_ratio)
                offset = (bg.width - new_w) // 2
                bg = bg.crop((offset, 0, offset + new_w, bg.height))
            else:
                new_h  = int(bg.width / target_ratio)
                offset = (bg.height - new_h) // 2
                bg = bg.crop((0, offset, bg.width, offset + new_h))
            bg  = bg.resize((W, H), Image.LANCZOS)
            bg  = bg.filter(ImageFilter.GaussianBlur(radius=8))
            bg  = ImageEnhance.Brightness(bg).enhance(0.35)
            img = bg
        except Exception as e:
            log.warning(f"BG process fail: {e}")
            img = Image.new('RGB', (W, H), color=(15, 15, 15))
    else:
        img = Image.new('RGB', (W, H), color=(15, 15, 15))

    # Semi-transparent overlay
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle([(0, 580), (W, H - 80)], fill=(0, 0, 0, 170))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Fonts
    try:
        f_n = ImageFont.truetype(FONT_PATH, 110)
        f_h = ImageFont.truetype(FONT_PATH, 76)
        f_d = ImageFont.truetype(FONT_PATH, 44)
        f_b = ImageFont.truetype(FONT_PATH, 38)
    except Exception as e:
        raise RuntimeError(f"Font load भएन: {e}")

    # Number  (intro/outro card मा num खाली हुन्छ)
    if num:
        draw.text((80, 620), f"{num}.", font=f_n, fill=(255, 220, 0))

    y = 770
    for line in textwrap.wrap(headline, width=22)[:3]:
        draw.text((80, y), line, font=f_h, fill=(255, 220, 0))
        y += 108

    # Divider
    draw.rectangle([(80, y + 12), (1000, y + 15)], fill=(255, 220, 0))
    y += 48

    for line in textwrap.wrap(details, width=42)[:4]:
        draw.text((80, y), line, font=f_d, fill=(235, 235, 235))
        y += 63

    # Branding — Nepali only
    draw.text((300, 1820), "दैनिक आर्थिक समाचार", font=f_b, fill=(160, 160, 160))

    img.save(filename)

# ── Audio + clip ─────────────────────────────────────────────────────
async def make_clip(text: str, num: str, headline: str, details: str,
                    mp3: str, jpg: str, bg_img: str = None):
    # Natural voice: slightly slower rate, no pitch shift
    await edge_tts.Communicate(
        text, "ne-NP-SagarNeural", rate="+3%", pitch="+0Hz"
    ).save(mp3)
    make_card(num, headline, details, jpg, bg_image_path=bg_img)
    audio = AudioFileClip(mp3)
    clip  = (ImageClip(jpg)
             .set_duration(audio.duration)
             .set_audio(audio)
             .resize(lambda t: 1 + 0.015 * t))   # subtle zoom
    return clip, audio

# ── Email ────────────────────────────────────────────────────────────
def send_email(filepath: str, date: str):
    size_mb = Path(filepath).stat().st_size / 1_048_576
    if size_mb > 24:
        log.warning(f"⚠️  Video {size_mb:.1f} MB > 24 MB — Gmail reject हुन सक्छ!")

    msg = MIMEMultipart()
    msg['From'] = msg['To'] = SENDER
    msg['Subject'] = f"दैनिक आर्थिक समाचार - {date}"

    with open(filepath, "rb") as f:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="economics_video.mp4"')
        msg.attach(part)

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(SENDER, PASSWORD)
        server.sendmail(SENDER, SENDER, msg.as_string())
    log.info("📧 Email पठाइयो!")

# ── Cleanup ──────────────────────────────────────────────────────────
def cleanup(*patterns):
    for pat in patterns:
        for f in glob.glob(pat):
            try: Path(f).unlink()
            except Exception as e: log.warning(f"Cleanup fail: {f} — {e}")

# ── Main ─────────────────────────────────────────────────────────────
async def run_automated_bulletin():
    today = datetime.now().strftime("%Y-%m-%d")
    log.info(f"🚀 Economics Bulletin Started for {today}")

    ensure_font()
    news_data = scrape_news()
    data      = generate_bulletin(news_data)

    # ── एउटा shared background image सबैको लागि ──
    all_headlines = [item['headline'] for item in data['bulletin']]
    shared_bg     = "shared_bg.jpg"
    got_bg        = fetch_shared_background(all_headlines, shared_bg)
    bg_path       = shared_bg if got_bg else None

    clips, audio_refs = [], []

    # --- Intro (number छैन, shared bg) ---
    await edge_tts.Communicate(
        data['intro'], "ne-NP-SagarNeural", rate="+3%", pitch="+0Hz"
    ).save("intro.mp3")
    make_card("", "आर्थिक समाचार", "आजका प्रमुख समाचारहरू", "intro.jpg", bg_image_path=bg_path)
    a = AudioFileClip("intro.mp3")
    audio_refs.append(a)
    clips.append(ImageClip("intro.jpg").set_duration(a.duration).set_audio(a))

    # --- ६ Bulletin items (सबैमा एउटै shared bg) ---
    for i, item in enumerate(data['bulletin']):
        mp3 = f"v_{i}.mp3"
        jpg = f"f_{i}.jpg"
        text = f"{item['num']}। {item['headline']}। {item['details']}"
        clip, audio = await make_clip(
            text, item['num'], item['headline'], item['details'],
            mp3, jpg, bg_img=bg_path
        )
        clips.append(clip)
        audio_refs.append(audio)

    # --- Outro (shared bg) ---
    await edge_tts.Communicate(
        data['outro'], "ne-NP-SagarNeural", rate="+3%", pitch="+0Hz"
    ).save("outro.mp3")
    make_card("", "धन्यवाद", "हामीलाई पछ्याउँदै गर्नुहोला", "outro.jpg", bg_image_path=bg_path)
    a = AudioFileClip("outro.mp3")
    audio_refs.append(a)
    clips.append(ImageClip("outro.jpg").set_duration(a.duration).set_audio(a))

    # --- Render ---
    output = "economics_final.mp4"
    concatenate_videoclips(clips, method="compose").write_videofile(
        output, fps=24, codec="libx264",
        audio_codec="aac", bitrate="1500k",
        ffmpeg_params=["-pix_fmt", "yuv420p", "-crf", "28"]
    )

    for a in audio_refs:
        try: a.close()
        except: pass

    send_email(output, today)
    cleanup("v_*.mp3", "f_*.jpg", "intro.*", "outro.*", "shared_bg.jpg")
    log.info("✅ सम्पन्न!")

if __name__ == "__main__":
    asyncio.run(run_automated_bulletin())
