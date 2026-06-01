import asyncio
import edge_tts
from docx import Document
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import os

# १. वर्ड फाइलबाट टेक्स्ट पढ्ने फङ्सन
def read_docx(file_path):
    if not os.path.exists(file_path):
        print(f"Error: {file_path} फाइल भेटिएन!")
        return []
    doc = Document(file_path)
    # खाली नभएका प्याराग्राफ मात्र लिने
    full_text = [para.text.strip() for para in doc.paragraphs if len(para.text.strip()) > 2]
    return full_text

# २. AI Voiceover (नेपाली) बनाउने फङ्सन
async def generate_audio(text, output_file):
    # नेपाली पुरुष आवाजको लागि 'ne-NP-SagarNeural' प्रयोग गरिएको छ
    communicate = edge_tts.Communicate(text, "ne-NP-SagarNeural") 
    await communicate.save(output_file)

async def start_processing():
    word_file = "script.docx" # तपाईंको वर्ड फाइलको नाम यो हुनुपर्छ
    paragraphs = read_docx(word_file)
    clips = []
    
    if not paragraphs:
        print("वर्ड फाइलमा कुनै टेक्स्ट भेटिएन।")
        return

    print(f"कुल {len(paragraphs)} सेक्सनहरू भेटिए। भिडियो बन्दैछ...")

    for i, para in enumerate(paragraphs):
        audio_file = f"temp_audio_{i}.mp3"
        image_file = f"images/{i+1}.png" # फोटोको नाम 1.png, 2.png हुनुपर्छ
        
        # फोटो छ कि छैन चेक गर्ने
        if not os.path.exists(image_file):
            print(f"Warning: {image_file} फाइल भेटिएन, यो भाग स्किप गरियो।")
            continue

        # अडियो बनाउने
        await generate_audio(para, audio_file)
        
        # अडियो र फोटो जोडेर भिडियो क्लिप बनाउने
        audio_clip = AudioFileClip(audio_file)
        img_clip = ImageClip(image_file).set_duration(audio_clip.duration)
        img_clip = img_clip.set_audio(audio_clip)
        
        clips.append(img_clip)
        print(f"Section {i+1} तयार भयो।")

    # सबै क्लिपहरूलाई एउटै भिडियो बनाउने
    if clips:
        final_video = concatenate_videoclips(clips, method="compose")
        final_video.write_videofile("final_video.mp4", fps=24, codec="libx264")
        print("बधाई छ! भिडियो तयार भयो: final_video.mp4")
    else:
        print("भिडियो बनाउन पर्याप्त सामग्री पुगेन।")

    # फोहोर सफा गर्ने (अस्थायी अडियो फाइलहरू हटाउने)
    for i in range(len(paragraphs)):
        if os.path.exists(f"temp_audio_{i}.mp3"):
            os.remove(f"temp_audio_{i}.mp3")

if __name__ == "__main__":
    asyncio.run(start_processing())
