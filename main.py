import asyncio
import edge_tts
from docx import Document
import os

# MoviePy imports सच्याइएको छ
try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
except ImportError:
    from moviepy.video.io.ImageClip import ImageClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip
    from moviepy.video.compositing.concatenate import concatenate_videoclips

def read_docx(file_path):
    if not os.path.exists(file_path):
        return []
    doc = Document(file_path)
    return [para.text.strip() for para in doc.paragraphs if len(para.text.strip()) > 2]

def find_image(base_path):
    extensions = ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']
    for ext in extensions:
        if os.path.exists(base_path + ext):
            return base_path + ext
    return None

async def generate_audio(text, output_file):
    communicate = edge_tts.Communicate(text, "ne-NP-SagarNeural") 
    await communicate.save(output_file)

async def start_processing():
    word_file = "script.docx"
    default_img = find_image("default")
    
    if not os.path.exists("images"):
        os.makedirs("images")

    paragraphs = read_docx(word_file)
    if not paragraphs:
        print("Script empty!")
        return

    clips = []
    for i, para in enumerate(paragraphs):
        audio_file = f"temp_{i}.mp3"
        specific_image = find_image(f"images/{i+1}")
        image_to_use = specific_image if specific_image else default_img
        
        if not image_to_use:
            continue

        await generate_audio(para, audio_file)
        audio_clip = AudioFileClip(audio_file)
        img_clip = ImageClip(image_to_use).set_duration(audio_clip.duration)
        img_clip = img_clip.set_audio(audio_clip)
        clips.append(img_clip)

    if clips:
        final_video = concatenate_videoclips(clips, method="compose")
        final_video.write_videofile("final_video.mp4", fps=24, codec="libx264", audio_codec="aac")
    
    # सफा गर्ने
    for i in range(len(paragraphs)):
        if os.path.exists(f"temp_{i}.mp3"): os.remove(f"temp_{i}.mp3")

if __name__ == "__main__":
    asyncio.run(start_processing())
