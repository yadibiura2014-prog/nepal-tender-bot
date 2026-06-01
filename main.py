import asyncio
import edge_tts
from docx import Document
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import os

def read_docx(file_path):
    if not os.path.exists(file_path):
        return []
    doc = Document(file_path)
    return [para.text.strip() for para in doc.paragraphs if len(para.text.strip()) > 2]

async def generate_audio(text, output_file):
    communicate = edge_tts.Communicate(text, "ne-NP-SagarNeural") 
    await communicate.save(output_file)

async def start_processing():
    word_file = "script.docx"
    default_img = "default.png" # फोटो नभएको ठाउँमा यो फोटो देखिन्छ
    paragraphs = read_docx(word_file)
    clips = []
    
    if not paragraphs:
        print("Script empty!")
        return

    for i, para in enumerate(paragraphs):
        audio_file = f"temp_audio_{i}.mp3"
        # images फोल्डर भित्र १.png, २.png चेक गर्छ
        specific_image = f"images/{i+1}.png" 
        
        # यदि त्यो नम्बरको फोटो छैन भने default.png प्रयोग गर्छ
        if os.path.exists(specific_image):
            image_to_use = specific_image
        elif os.path.exists(default_img):
            image_to_use = default_img
            print(f"Section {i+1}: Specific image missing, using default.png")
        else:
            print(f"Section {i+1}: No image found, skipping.")
            continue

        await generate_audio(para, audio_file)
        
        audio_clip = AudioFileClip(audio_file)
        img_clip = ImageClip(image_to_use).set_duration(audio_clip.duration)
        img_clip = img_clip.set_audio(audio_clip)
        
        clips.append(img_clip)

    if clips:
        final_video = concatenate_videoclips(clips, method="compose")
        final_video.write_videofile("final_video.mp4", fps=24)
        print("Video Ready!")

    # Cleanup
    for i in range(len(paragraphs)):
        if os.path.exists(f"temp_audio_{i}.mp3"):
            os.remove(f"temp_audio_{i}.mp3")

if __name__ == "__main__":
    asyncio.run(start_processing())
