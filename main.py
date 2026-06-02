import asyncio
import edge_tts
from docx import Document
import os

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
    # प्याराग्राफ फिल्टर गर्ने: धेरै छोटा लाइन वा शीर्षकहरूलाई हटाएर मुख्य टेक्स्ट मात्र लिने
    paras = [p.text.strip() for p in doc.paragraphs if len(p.text.strip()) > 20]
    return paras

def find_image(idx):
    exts = ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']
    # सिधै मुख्य फोल्डरमा खोज्ने
    for ext in exts:
        target = f"{idx}{ext}"
        if os.path.exists(target):
            return target
    return None

async def generate_audio(text, output_file):
    # en-US-AriaNeural एकदमै राम्रो आवाज हो
    # rate="+0%" राखेको छु ताकि यो नकुदोस् र सुस्तरी बोलेको सुनियोस्
    voice = "en-US-AriaNeural"
    communicate = edge_tts.Communicate(text, voice, rate="+0%") 
    await communicate.save(output_file)

async def start_processing():
    word_file = "script.docx"
    
    # Default इमेज सेट गर्ने
    default_img = None
    for ext in ['.png', '.jpg', '.jpeg']:
        if os.path.exists(f"default{ext}"):
            default_img = f"default{ext}"
            break

    paragraphs = read_docx(word_file)
    print(f"Total valid paragraphs to process: {len(paragraphs)}")
    
    clips = []
    last_image = default_img # सुरुमा default इमेज प्रयोग गर्ने

    for i, para in enumerate(paragraphs):
        print(f"--- Processing Section {i+1} ---")
        audio_file = f"temp_{i}.mp3"
        
        # नयाँ फोटो खोज्ने (जस्तै २.png, ३.png)
        current_image = find_image(i + 1)
        
        # यदि नयाँ फोटो भेटियो भने त्यसलाई प्रयोग गर्ने, नत्र पुरानै फोटो देखाइरहने
        if current_image:
            image_to_use = current_image
            last_image = current_image # नयाँ फोटोलाई 'last_image' बनाउने
            print(f"MATCH: Paragraph {i+1} using {image_to_use}")
        else:
            image_to_use = last_image
            print(f"HOLD: Paragraph {i+1} using previous image: {image_to_use}")

        if not image_to_use:
            print(f"SKIP: No image found at all for paragraph {i+1}")
            continue

        # अडियो बनाउने (सामान्य गतिमा)
        await generate_audio(para, audio_file)
        
        audio_clip = AudioFileClip(audio_file)
        img_clip = ImageClip(image_to_use).set_duration(audio_clip.duration)
        img_clip = img_clip.set_audio(audio_clip)
        
        clips.append(img_clip)

    if clips:
        print("Finalizing your professional video...")
        final_video = concatenate_videoclips(clips, method="compose")
        final_video.write_videofile("final_video.mp4", fps=24, codec="libx264", audio_codec="aac")
        print("Success! Download your video from Summary tab.")
    else:
        print("Error: No clips were generated.")

if __name__ == "__main__":
    asyncio.run(start_processing())
