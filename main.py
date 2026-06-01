import asyncio
import edge_tts
from docx import Document
import os

# MoviePy imports
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
    # This ensures we only count paragraphs that actually have text
    paras = [p.text.strip() for p in doc.paragraphs if len(p.text.strip()) > 10]
    return paras

def find_image(idx):
    # Since you uploaded directly to the root, we look for 2.png, 3.png etc. there
    exts = ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']
    for ext in exts:
        target = f"{idx}{ext}"
        if os.path.exists(target):
            print(f"FOUND: Paragraph {idx} matches {target}")
            return target
    return None

async def generate_audio(text, output_file):
    # Using 'en-US-AriaNeural' - One of the best natural English voices
    # rate="+15%" makes it sound energetic and exciting
    voice = "en-US-AriaNeural"
    communicate = edge_tts.Communicate(text, voice, rate="+15%") 
    await communicate.save(output_file)

async def start_processing():
    word_file = "script.docx"
    
    # Check for default background in the root
    default_img = None
    for ext in ['.png', '.jpg', '.jpeg']:
        if os.path.exists(f"default{ext}"):
            default_img = f"default{ext}"
            break

    paragraphs = read_docx(word_file)
    print(f"Total paragraphs to process: {len(paragraphs)}")
    
    clips = []
    for i, para in enumerate(paragraphs):
        print(f"Processing Section {i+1}...")
        audio_file = f"temp_{i}.mp3"
        
        # Look for image 1.png, 2.png etc. in the root
        image_to_use = find_image(i + 1)
        
        if not image_to_use:
            print(f"No specific image for paragraph {i+1}, using default: {default_img}")
            image_to_use = default_img
            
        if not image_to_use:
            print(f"Skipping paragraph {i+1} - no image or default found.")
            continue

        # Generate English Audio
        await generate_audio(para, audio_file)
        
        audio_clip = AudioFileClip(audio_file)
        img_clip = ImageClip(image_to_use).set_duration(audio_clip.duration)
        img_clip = img_clip.set_audio(audio_clip)
        
        clips.append(img_clip)

    if clips:
        print("Finalizing video...")
        final_video = concatenate_videoclips(clips, method="compose")
        final_video.write_videofile("final_video.mp4", fps=24, codec="libx264", audio_codec="aac")
        print("Success!")
    else:
        print("Error: No video clips created. Check your file names.")

if __name__ == "__main__":
    asyncio.run(start_processing())
