import os, requests, json, time, asyncio, textwrap, logging, glob
import numpy as np
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, VideoClip
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
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
SENDER     = os.getenv("EMAIL_SENDER")
PASSWORD   = os.getenv("EMAIL_PASSWORD")

# Background image — repo को root मा राखिएको
BG_IMAGE = "background.jpg"

# Noto Sans Devanagari fonts (Kokila-style, Linux compatible)
FONT_BOLD     = "noto_bold.ttf"
FONT_REG      = "noto_reg.ttf"
FONT_BOLD_URL = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Bold.ttf"
FONT_REG_URL  = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf"

W, H = 1080, 1920   # 9:16 portrait

# ── Font: download once ──────────────────────────────────────────────
def ensure_font():
    for path, url in [(FONT_BOLD, FONT_BOLD_URL), (FONT_REG, FONT_REG_URL)]:
        if not Path(path).exists():
            log.info(f"Font download गर्दै: {path}")
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            Path(path).write_bytes(r.content)
    log.info("Fonts तयार")

# ── Gemini model picker ──────────────────────────────────────────────
def get_best_gemini_model() -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    models = requests.get(url, timeout=10).json().get('models', [])
    eligible = [m['name'] for m in models
                if 'generateContent' in m.get('supportedGenerationMethods', [])]
    return next((m for m in eligible if "gemini-1.5-flash" in m), eligible[0])

# ── Prepare background base image ───────────────────────────────────
def prepare_bg_base() -> Image.Image:
    """
    background.jpg (repo root) लाई blur + darken गरेर ready बनाउँछ।
    File नभेटिए dark fallback।
    """
    if Path(BG_IMAGE).exists():
        try:
            bg = Image.open(BG_IMAGE).convert("RGB")

            # Crop to 9:16 portrait
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

            bg = bg.resize((W, H), Image.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(radius=9))
            bg = ImageEnhance.Brightness(bg).enhance(0.30)
            log.info("background.jpg load भयो")
            return bg
        except Exception as e:
            log.warning(f"BG load fail: {e}")

    log.warning("background.jpg भेटिएन — dark fallback प्रयोग हुनेछ")
    return Image.new('RGB', (W, H), color=(8, 8, 18))

# ── News scraping — आजको मात्र ──────────────────────────────────────
def scrape_news() -> str:
    """
    News scrape गर्छ र Gemini लाई आजको मात्र छान्न भन्छ।
    Website हरूले exact date tag नदिने भएकाले Gemini ले filter गर्छ।
    """
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

    # Nepal time (UTC+5:45)
    from datetime import timezone, timedelta
    nepal_tz  = timezone(timedelta(hours=5, minutes=45))
    today_str = datetime.now(nepal_tz).strftime("%Y-%m-%d")
    log.info(f"आजको मिति (नेपाल): {today_str}")

    for url in sources:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'html.parser')

            # Date hints खोज्छ — time, date, datetime tags
            date_tags = soup.find_all(['time', 'span', 'div'],
                                       attrs={'class': lambda c: c and any(
                                           x in ' '.join(c) for x in
                                           ['date', 'time', 'publish', 'ago', 'posted']
                                       )})

            for tag in soup.find_all(['h1', 'h2', 'h3'])[:12]:
                title = tag.get_text().strip()
                if len(title) > 25:
                    # Parent element मा date hint खोज्छ
                    parent = tag.parent
                    parent_text = parent.get_text() if parent else ""
                    # आजको date string वा "today"/"आज" keyword भएमा प्राथमिकता
                    is_today = any(x in parent_text.lower() for x in
                                   [today_str, 'today', 'आज', 'अहिले', 'just now', 'hour', 'घण्टा', 'मिनेट'])
                    if is_today:
                        headlines.add(f"[TODAY] {title}")
                    else:
                        headlines.add(title)
        except Exception as e:
            log.warning(f"Scrape fail ({url}): {e}")

    log.info(f"{len(headlines)} unique headlines भेटियो")
    return "\n".join(headlines)

# ── Gemini bulletin generation — आजको मात्र enforce ────────────────
def generate_bulletin(news_data: str, today_nepali: str) -> dict:
    model = get_best_gemini_model()
    url   = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={GEMINI_KEY}"

    prompt = f"""
    तिमी एक प्रतिष्ठित PhD Economic Analyst हौ।
    आजको मिति: {today_nepali}

    महत्वपूर्ण: केवल आज ({today_nepali}) प्रकाशित भएका समाचार मात्र छान्नुस्।
    [TODAY] tag भएका समाचारलाई प्राथमिकता दिनुस्।
    हिजो वा अघिका समाचार समावेश नगर्नुस्।

    कार्यहरू:
    १. प्राथमिकता: सबैभन्दा महत्वपूर्ण आर्थिक समाचार (ब्याजदर, बजेट, ठूला निर्णय) सुरुमा।
    २. इन्ट्रो: "नमस्ते, आजका प्रमुख आर्थिक समाचारहरूमा स्वागत छ।" — natural, warm tone मा।
    ३. हरेक समाचारमा अङ्क र तथ्य अनिवार्य। राजनीति वर्जित।
    ४. headline र details नेपालीमा मात्र — अंग्रेजी शब्द नराख्नुस्।
    ५. voice को लागि natural पढिने गरी — अल्पविराम (,) र पूर्णविराम (।) सही ठाउँमा।
    ६. bulletin array मा EXACTLY ६ वटा item मात्र।
    ७. outro मा धन्यवाद र हेर्दै गर्नुस् — Nepali मा natural tone मा।

    मलाई यो 'json' मा उत्तर देउ:
    {{"intro": "...", "bulletin": [{{"num": "१", "headline": "...", "details": "..."}}], "outro": "..."}}

    DATA:
    {news_data}
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

# ── Render single frame with slide offset ───────────────────────────
def render_frame(bg_base: Image.Image, num: str, headline: str,
                 details: str, slide_x: int, date_str: str = "") -> np.ndarray:
    img = bg_base.copy()

    # Dark overlay
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle([(0, 520), (W, H - 55)], fill=(0, 0, 0, 185))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    try:
        f_n    = ImageFont.truetype(FONT_BOLD, 118)
        f_h    = ImageFont.truetype(FONT_BOLD, 80)
        f_d    = ImageFont.truetype(FONT_REG,  46)
        f_b    = ImageFont.truetype(FONT_REG,  36)
        f_date = ImageFont.truetype(FONT_REG,  34)
    except Exception as e:
        raise RuntimeError(f"Font load भएन: {e}")

    x = 80 + slide_x   # animated x

    # Date — top right corner (fixed, no slide)
    if date_str:
        draw.text((W - 320, 60), date_str, font=f_date, fill=(200, 200, 200))

    # Number
    if num:
        draw.text((x, 565), f"{num}.", font=f_n, fill=(255, 215, 0))

    # Headline
    y = 730
    for line in textwrap.wrap(headline, width=20)[:3]:
        draw.text((x, y), line, font=f_h, fill=(255, 215, 0))
        y += 112

    # Gold divider (fixed)
    draw.rectangle([(80, y + 8), (1000, y + 12)], fill=(255, 215, 0))
    y += 46

    # Details
    for line in textwrap.wrap(details, width=40)[:4]:
        draw.text((x, y), line, font=f_d, fill=(242, 242, 242))
        y += 66

    # Branding — fixed bottom
    draw.text((270, 1848), "दैनिक आर्थिक समाचार", font=f_b, fill=(140, 140, 140))

    return np.array(img)

# ── Animated clip: slide in from right ──────────────────────────────
def make_animated_clip(bg_base: Image.Image, num: str, headline: str,
                       details: str, audio: AudioFileClip,
                       date_str: str = "") -> VideoClip:
    duration   = audio.duration
    slide_dur  = 0.5
    slide_dist = W

    def make_frame(t):
        if t < slide_dur:
            ease   = 1 - (1 - t / slide_dur) ** 3   # cubic ease-out
            offset = int(slide_dist * (1 - ease))
        else:
            offset = 0
        return render_frame(bg_base, num, headline, details, offset, date_str)

    return VideoClip(make_frame, duration=duration).set_audio(audio)

# ── Static clip (intro / outro) ──────────────────────────────────────
def make_static_clip(bg_base: Image.Image, headline: str,
                     details: str, audio: AudioFileClip,
                     date_str: str = "") -> VideoClip:
    frame = render_frame(bg_base, "", headline, details, 0, date_str)
    return ImageClip(frame).set_duration(audio.duration).set_audio(audio)

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
    from datetime import timezone, timedelta
    nepal_tz     = timezone(timedelta(hours=5, minutes=45))
    now_nepal    = datetime.now(nepal_tz)
    today_str    = now_nepal.strftime("%Y-%m-%d")
    # Card मा देखिने मिति — नेपाली format
    display_date = now_nepal.strftime("%Y/%m/%d")

    log.info(f"🚀 Economics Bulletin Started — {today_str} (Nepal Time)")

    ensure_font()
    bg_base   = prepare_bg_base()
    news_data = scrape_news()
    data      = generate_bulletin(news_data, today_str)

    clips, audio_refs = [], []

    # --- Intro ---
    await edge_tts.Communicate(
        data['intro'], "ne-NP-SagarNeural", rate="+3%", pitch="+0Hz"
    ).save("intro.mp3")
    a = AudioFileClip("intro.mp3")
    audio_refs.append(a)
    clips.append(make_static_clip(
        bg_base, "आर्थिक समाचार", "आजका प्रमुख समाचारहरू", a, display_date
    ))

    # --- ६ News items with slide-in ---
    for i, item in enumerate(data['bulletin']):
        mp3  = f"v_{i}.mp3"
        text = f"{item['num']}। {item['headline']}। {item['details']}"
        await edge_tts.Communicate(
            text, "ne-NP-SagarNeural", rate="+3%", pitch="+0Hz"
        ).save(mp3)
        a = AudioFileClip(mp3)
        audio_refs.append(a)
        clip = make_animated_clip(
            bg_base, item['num'], item['headline'], item['details'], a, display_date
        )
        clips.append(clip)
        log.info(f"Clip {i+1}/6 तयार")

    # --- Outro ---
    await edge_tts.Communicate(
        data['outro'], "ne-NP-SagarNeural", rate="+3%", pitch="+0Hz"
    ).save("outro.mp3")
    a = AudioFileClip("outro.mp3")
    audio_refs.append(a)
    clips.append(make_static_clip(
        bg_base, "धन्यवाद", "हामीलाई पछ्याउँदै गर्नुहोला", a, display_date
    ))

    # --- Render ---
    output = "economics_final.mp4"
    log.info("भिडियो render गर्दै...")
    concatenate_videoclips(clips, method="compose").write_videofile(
        output, fps=24, codec="libx264",
        audio_codec="aac", bitrate="1500k",
        ffmpeg_params=["-pix_fmt", "yuv420p", "-crf", "28"]
    )

    for a in audio_refs:
        try: a.close()
        except: pass

    send_email(output, today_str)
    cleanup("v_*.mp3", "intro.*", "outro.*", "noto_bold.ttf", "noto_reg.ttf")
    log.info("✅ सम्पन्न!")

if __name__ == "__main__":
    asyncio.run(run_automated_bulletin())
